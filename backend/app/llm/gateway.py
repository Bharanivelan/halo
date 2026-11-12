"""LLM gateway (AGENT_ARCHITECTURE §12).

All model calls go through here so that every call is: budget-checked, cost-logged
(llm_calls), tagged with prompt id + version, and provider-agnostic.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from app.core.config import get_settings
from app.core.db import tenant_session
from app.models import LlmCall
from app.workflow.budget import BudgetGuard
from app.workflow.errors import AIQuotaExhausted, PermanentError, TransientError

_settings = get_settings()
_rpm_throttle = None
_quota_until = 0.0  # epoch seconds; while in the future, the daily AI allowance is spent (D-44)
QUOTA_MESSAGE = "The AI's daily allowance is used up, so this step continued without AI."


def ai_available() -> bool:
    """AI is configured and its daily allowance isn't spent. Steps use their no-AI path otherwise."""
    return _settings.llm_configured and time.time() >= _quota_until


def _daily_quota_cooldown(err: Exception) -> float | None:
    """Seconds until a per-day quota resets, if this rate-limit error is a per-day quota (else None)."""
    import re
    msg = str(err)
    if "PerDay" not in msg:
        return None
    m = re.search(r"retryDelay'?\"?:\s*'?\"?(\d+)s", msg)
    return min(float(m.group(1)) if m else 3600.0, 6 * 3600.0)


def _pace() -> None:
    """Space requests out to stay under LLM_MAX_RPM (shared by all worker threads in this process)."""
    global _rpm_throttle
    if _settings.llm_max_rpm <= 0:
        return
    if _rpm_throttle is None:
        from app.providers.http import Throttle
        _rpm_throttle = Throttle(60.0 / _settings.llm_max_rpm)
    _rpm_throttle.wait("llm")


class LLMNotConfigured(Exception):
    pass


@dataclass
class CallContext:
    workspace_id: UUID
    step: str
    job_id: UUID | None = None
    task_id: UUID | None = None
    budget: BudgetGuard | None = None
    on_cost: Any = None  # callable(float) to add to task cost


@dataclass
class LLMResult:
    message: Any            # provider message object (for tool loops)
    content: str | None
    tool_calls: list[dict]  # [{id, name, arguments(dict)}]
    input_tokens: int
    output_tokens: int
    cost_usd: float


class LLMProvider(Protocol):
    name: str

    def chat(self, *, model: str, messages: list[dict], max_output_tokens: int, json_mode: bool,
             tools: list[dict] | None, tool_choice: Any) -> tuple[Any, str | None, list[dict], int, int]: ...


class OpenAICompatibleProvider:
    """Chat-completions provider for OpenAI and Gemini (via Google's OpenAI-compatible endpoint, D-32).

    Both vendors speak the same request shape (messages, tools, JSON mode), so the research loop,
    budget guard and cost logging are identical whichever one is configured.
    """

    def __init__(self, name: str) -> None:
        from openai import OpenAI

        self.name = name
        base_url = _settings.gemini_base_url if name == "gemini" else None
        self.client = OpenAI(api_key=_settings.llm_api_key, base_url=base_url,
                             timeout=_settings.llm_timeout_s, max_retries=1)

    def _kwargs(self, model, messages, max_output_tokens, json_mode, tools, tool_choice) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"model": model, "messages": messages}
        if self.name == "gemini":
            kwargs["max_tokens"] = max_output_tokens
            # Keep "thinking" small: cheaper and faster; our prompts are extraction-style.
            # Sent via extra_body so it works with the pinned openai SDK (no reasoning_effort kwarg there).
            if model.startswith(("gemini-2.5", "gemini-3")):
                kwargs["extra_body"] = {"reasoning_effort": "low"}
        else:
            kwargs["max_completion_tokens"] = max_output_tokens
            if model.startswith(("gpt-5", "o3", "o4")):
                kwargs["extra_body"] = {"reasoning_effort": "low"}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        if tools:
            kwargs["tools"] = tools
            if tool_choice:
                kwargs["tool_choice"] = tool_choice
        return kwargs

    def chat(self, *, model, messages, max_output_tokens, json_mode, tools, tool_choice):
        import openai

        global _quota_until
        if not ai_available():
            raise AIQuotaExhausted(QUOTA_MESSAGE)
        kwargs = self._kwargs(model, messages, max_output_tokens, json_mode, tools, tool_choice)
        _pace()
        try:
            try:
                resp = self.client.chat.completions.create(**kwargs)
            except openai.BadRequestError:
                # Some Gemini models reject forcing a named function; "required" forces a tool call
                # and the research loop only offers "finish" meaningfully at that point.
                if self.name == "gemini" and isinstance(tool_choice, dict):
                    kwargs["tool_choice"] = "required"
                    resp = self.client.chat.completions.create(**kwargs)
                else:
                    raise
        except openai.RateLimitError as e:
            cool = _daily_quota_cooldown(e)
            if cool is not None:
                _quota_until = time.time() + cool
                raise AIQuotaExhausted(QUOTA_MESSAGE) from e
            raise TransientError("AI provider temporarily unavailable (RateLimitError)", retry_after_s=60) from e
        except (openai.APITimeoutError, openai.APIConnectionError, openai.InternalServerError) as e:
            wait = 60 if isinstance(e, openai.RateLimitError) else 20
            raise TransientError(f"AI provider temporarily unavailable ({type(e).__name__})", retry_after_s=wait) from e
        except (openai.AuthenticationError, openai.PermissionDeniedError) as e:
            raise PermanentError(f"AI provider rejected the API key. Check {_settings.llm_key_name}.") from e
        except openai.NotFoundError as e:
            raise PermanentError(f"AI model '{model}' not found for {self.name}. Check LLM_MODEL_FAST / LLM_MODEL_STANDARD.") from e
        except openai.BadRequestError as e:
            raise PermanentError(f"AI request rejected: {str(e)[:200]}") from e
        if not resp.choices:
            raise TransientError("AI provider returned no answer (possibly filtered); will retry", retry_after_s=10)
        msg = resp.choices[0].message
        calls = []
        for i, tc in enumerate(msg.tool_calls or []):
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {"_raw": tc.function.arguments}
            call = {"id": tc.id or f"call_{i}", "name": tc.function.name, "arguments": args}
            # Gemini attaches a "thought signature" that must be echoed back on the next turn.
            extra = (tc.model_extra or {}).get("extra_content")
            if extra:
                call["extra_content"] = extra
            calls.append(call)
        usage = resp.usage
        tin = usage.prompt_tokens if usage else 0
        tout = usage.completion_tokens if usage else 0
        # Gemini bills thinking tokens as output; they show up in total_tokens, not always in completion_tokens.
        if usage and usage.total_tokens and usage.total_tokens > tin + tout:
            tout = usage.total_tokens - tin
        return msg, msg.content, calls, tin, tout


_provider: LLMProvider | None = None


def provider() -> LLMProvider:
    global _provider
    if not _settings.llm_configured:
        raise LLMNotConfigured(f"{_settings.llm_key_name} is not set")
    if _provider is None:
        if _settings.llm_provider not in ("gemini", "openai"):
            raise LLMNotConfigured(f"Unknown LLM_PROVIDER '{_settings.llm_provider}' (use gemini or openai)")
        _provider = OpenAICompatibleProvider(_settings.llm_provider)
    return _provider


def model_for(tier: str) -> str:
    return _settings.llm_model(tier)


def price(model: str, tin: int, tout: int) -> float:
    pin, pout = _settings.llm_pricing.get(model, (1.0, 4.0))  # unknown model → conservative estimate
    return (tin * pin + tout * pout) / 1_000_000


def _approx_tokens(messages: list[dict]) -> int:
    return sum(len(json.dumps(m.get("content") or "", ensure_ascii=False)) for m in messages) // 3 + 200


def call(*, ctx: CallContext, prompt_id: str, version: str, messages: list[dict], tier: str = "fast",
         json_mode: bool = False, tools: list[dict] | None = None, tool_choice: Any = None,
         max_output_tokens: int = 6000) -> LLMResult:
    prov = provider()
    model = model_for(tier)
    est = price(model, _approx_tokens(messages), max_output_tokens // 2)
    if ctx.budget:
        ctx.budget.reserve(est)
    started = time.monotonic()
    status, err, tin, tout, cost = "ok", None, 0, 0, 0.0
    try:
        msg, content, calls, tin, tout = prov.chat(model=model, messages=messages, max_output_tokens=max_output_tokens,
                                                   json_mode=json_mode, tools=tools, tool_choice=tool_choice)
        cost = price(model, tin, tout)
        return LLMResult(message=msg, content=content, tool_calls=calls, input_tokens=tin, output_tokens=tout, cost_usd=cost)
    except Exception as e:
        status, err = "error", str(e)[:500]
        raise
    finally:
        if ctx.budget:
            ctx.budget.commit(est, cost)
        if ctx.on_cost and cost:
            ctx.on_cost(cost)
        try:
            with tenant_session(ctx.workspace_id) as db:
                db.add(LlmCall(workspace_id=ctx.workspace_id, job_id=ctx.job_id, task_id=ctx.task_id, step=ctx.step,
                               provider=prov.name, model=model, prompt_id=prompt_id, prompt_version=version,
                               input_tokens=tin, output_tokens=tout, cost_usd=cost,
                               latency_ms=int((time.monotonic() - started) * 1000), status=status, error=err))
        except Exception:  # noqa: BLE001
            pass


def call_json(*, ctx: CallContext, prompt_id: str, version: str, system: str, user: str, tier: str = "fast",
              max_output_tokens: int = 6000) -> dict:
    """Single structured call with one repair attempt if the JSON is invalid."""
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    res = call(ctx=ctx, prompt_id=prompt_id, version=version, messages=messages, tier=tier, json_mode=True,
               max_output_tokens=max_output_tokens)
    try:
        return json.loads(res.content or "")
    except json.JSONDecodeError:
        messages += [{"role": "assistant", "content": res.content or ""},
                     {"role": "user", "content": "That was not valid JSON. Reply again with only the JSON object."}]
        res = call(ctx=ctx, prompt_id=prompt_id, version=version + "-repair", messages=messages, tier=tier,
                   json_mode=True, max_output_tokens=max_output_tokens)
        try:
            return json.loads(res.content or "")
        except json.JSONDecodeError as e:
            raise PermanentError("AI returned invalid JSON twice") from e
