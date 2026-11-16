"""LLM gateway (AGENT_ARCHITECTURE §12).

All model calls go through here so that every call is: budget-checked, cost-logged
(llm_calls), tagged with prompt id + version, and provider-agnostic.
"""
from __future__ import annotations

import json
import re
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
    """Chat-completions provider for OpenAI, Gemini (Google's OpenAI-compatible endpoint, D-32) and any other
    OpenAI-compatible server (D-49: OpenRouter, Groq, Together, Azure OpenAI, Ollama, LM Studio, vLLM...).

    They all speak the same request shape (messages, tools, JSON mode), so the research loop,
    budget guard and cost logging are identical whichever one is configured.
    """

    def __init__(self, name: str) -> None:
        from openai import OpenAI

        self.name = name
        base_url = {"gemini": _settings.gemini_base_url,
                    "openai_compatible": _settings.openai_compatible_base_url}.get(name)
        # Local servers (Ollama, LM Studio) need no key, but the SDK insists on a value.
        api_key = _settings.llm_api_key or ("not-needed" if name == "openai_compatible" else None)
        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=_settings.llm_timeout_s, max_retries=1)

    def _kwargs(self, model, messages, max_output_tokens, json_mode, tools, tool_choice) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"model": model, "messages": messages}
        if self.name == "gemini":
            kwargs["max_tokens"] = max_output_tokens
            # Keep "thinking" small: cheaper and faster; our prompts are extraction-style.
            # Sent via extra_body so it works with the pinned openai SDK (no reasoning_effort kwarg there).
            if model.startswith(("gemini-2.5", "gemini-3")):
                kwargs["extra_body"] = {"reasoning_effort": "low"}
        elif self.name == "openai_compatible":
            kwargs["max_tokens"] = max_output_tokens  # the parameter every compatible server understands
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
                # Other compatible servers may also lack JSON mode; the prompts already ask for JSON
                # and call_json() extracts and repairs it.
                if self.name in ("gemini", "openai_compatible") and isinstance(tool_choice, dict):
                    kwargs["tool_choice"] = "required"
                elif self.name == "openai_compatible" and "response_format" in kwargs:
                    kwargs.pop("response_format")
                else:
                    raise
                resp = self.client.chat.completions.create(**kwargs)
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


# ───────── Amazon Bedrock (D-49) ─────────
_BEDROCK_TRANSIENT = {"ThrottlingException", "ServiceUnavailableException", "InternalServerException",
                      "ModelNotReadyException", "ModelTimeoutException", "ServiceQuotaExceededException"}
_BEDROCK_AUTH = {"AccessDeniedException", "UnrecognizedClientException", "ExpiredTokenException",
                 "InvalidSignatureException", "UnauthorizedException"}


def to_converse(messages: list[dict], tools: list[dict] | None, tool_choice: Any
                ) -> tuple[list[dict], list[dict], dict | None]:
    """Translate the OpenAI-style messages and tools Halo uses into Bedrock Converse's shape.

    Converse wants system text separately, strictly alternating user/assistant turns, tool results as user
    turns, and no empty text blocks. Returns (system, messages, toolConfig).
    """
    system = [{"text": m["content"]} for m in messages if m["role"] == "system" and m.get("content")]
    out: list[dict] = []

    def add(role: str, blocks: list[dict]) -> None:
        if not blocks:
            return
        if out and out[-1]["role"] == role:
            out[-1]["content"].extend(blocks)
        else:
            out.append({"role": role, "content": blocks})

    for m in messages:
        role = m["role"]
        if role == "system":
            continue
        if role == "tool":
            add("user", [{"toolResult": {"toolUseId": m["tool_call_id"], "content": [{"text": m.get("content") or "(empty)"}]}}])
            continue
        blocks: list[dict] = [{"text": m["content"]}] if isinstance(m.get("content"), str) and m["content"].strip() else []
        for tc in m.get("tool_calls") or []:
            fn = tc.get("function") or {}
            args = fn.get("arguments") or "{}"
            try:
                args = json.loads(args) if isinstance(args, str) else args
            except json.JSONDecodeError:
                args = {"_raw": args}
            blocks.append({"toolUse": {"toolUseId": tc["id"], "name": fn.get("name"), "input": args}})
        add("assistant" if role == "assistant" else "user", blocks)
    if out and out[0]["role"] != "user":  # Converse must start with a user turn
        out.insert(0, {"role": "user", "content": [{"text": "Continue."}]})

    tool_config = None
    if tools:
        specs = [{"toolSpec": {"name": t["function"]["name"], "description": t["function"].get("description") or t["function"]["name"],
                               "inputSchema": {"json": t["function"].get("parameters") or {"type": "object", "properties": {}}}}}
                 for t in tools]
        tool_config = {"tools": specs}
        if isinstance(tool_choice, dict):
            tool_config["toolChoice"] = {"tool": {"name": tool_choice["function"]["name"]}}
        elif tool_choice == "required":
            tool_config["toolChoice"] = {"any": {}}
        elif tool_choice == "auto":
            tool_config["toolChoice"] = {"auto": {}}
    return system, out, tool_config


def from_converse(resp: dict) -> tuple[str | None, list[dict], int, int]:
    """Text, tool calls ([{id, name, arguments}]) and token counts from a Converse response."""
    blocks = ((resp.get("output") or {}).get("message") or {}).get("content") or []
    text = "".join(b["text"] for b in blocks if "text" in b) or None
    calls = [{"id": b["toolUse"]["toolUseId"], "name": b["toolUse"]["name"], "arguments": b["toolUse"].get("input") or {}}
             for b in blocks if "toolUse" in b]
    usage = resp.get("usage") or {}
    return text, calls, int(usage.get("inputTokens") or 0), int(usage.get("outputTokens") or 0)


class BedrockProvider:
    """Amazon Bedrock through the Converse API: one request shape for every chat model Bedrock hosts
    (Anthropic Claude, Amazon Nova, Meta Llama, Mistral, Cohere, DeepSeek, ...), including tool use.

    Models differ in what they accept, so a rejected request is retried once per known difference:
    forcing a specific tool, a system prompt, or a large output limit.
    """

    name = "bedrock"

    def __init__(self) -> None:
        import os

        import boto3
        from botocore.config import Config

        if _settings.aws_bearer_token_bedrock and not os.environ.get("AWS_BEARER_TOKEN_BEDROCK"):
            os.environ["AWS_BEARER_TOKEN_BEDROCK"] = _settings.aws_bearer_token_bedrock  # read by botocore
        session = boto3.Session(profile_name=_settings.aws_profile, region_name=_settings.aws_region,
                                aws_access_key_id=_settings.aws_access_key_id,
                                aws_secret_access_key=_settings.aws_secret_access_key,
                                aws_session_token=_settings.aws_session_token)
        self.client = session.client("bedrock-runtime", config=Config(
            read_timeout=_settings.llm_timeout_s, connect_timeout=15, retries={"max_attempts": 2, "mode": "standard"}))

    def chat(self, *, model, messages, max_output_tokens, json_mode, tools, tool_choice):
        from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

        if not ai_available():
            raise AIQuotaExhausted(QUOTA_MESSAGE)
        if json_mode:  # Converse has no JSON switch; ask for it (call_json extracts and repairs)
            messages = [*messages[:-1], {**messages[-1], "content": f"{messages[-1].get('content') or ''}\n\n"
                                                                     "Reply with only the JSON object, no other text."}]
        system, conv, tool_config = to_converse(messages, tools, tool_choice)
        req: dict[str, Any] = {"modelId": model, "messages": conv, "inferenceConfig": {"maxTokens": max_output_tokens}}
        if system:
            req["system"] = system
        if tool_config:
            req["toolConfig"] = tool_config
        tried: set[str] = set()
        while True:
            _pace()
            try:
                resp = self.client.converse(**req)
                break
            except NoCredentialsError as e:
                raise PermanentError(f"No AWS credentials found for Bedrock. Set {_settings.llm_key_name}.") from e
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code", "")
                msg = str(e)
                if code == "ValidationException":
                    low = msg.lower()
                    tc = (req.get("toolConfig") or {}).get("toolChoice") or {}
                    if "tool" in tc and "toolchoice" not in tried and ("toolchoice" in low or "tool_choice" in low or "tool choice" in low):
                        tried.add("toolchoice")  # model can't force a named tool: "any" still forces a tool call
                        req["toolConfig"]["toolChoice"] = {"any": {}}
                        continue
                    if "any" in tc and "toolchoice-any" not in tried and ("toolchoice" in low or "tool_choice" in low or "tool choice" in low):
                        tried.add("toolchoice-any")
                        req["toolConfig"].pop("toolChoice", None)
                        continue
                    if "system" in req and "system" not in tried and "system" in low:
                        tried.add("system")  # model takes no system prompt: put it in front of the first user turn
                        sys_text = "\n\n".join(s["text"] for s in req.pop("system"))
                        req["messages"][0]["content"].insert(0, {"text": sys_text})
                        continue
                    if req["inferenceConfig"]["maxTokens"] > 2048 and re.search(r"max(imum)?[ _]?tokens", low):
                        req["inferenceConfig"]["maxTokens"] //= 2  # model has a smaller output limit
                        continue
                    if "on-demand throughput" in low or "inference profile" in low:
                        raise PermanentError(f"Bedrock model '{model}' must be called through an inference profile in this "
                                             f"region. Use the profile ID (e.g. 'us.{model}') in LLM_MODEL_FAST / LLM_MODEL_STANDARD.") from e
                    raise PermanentError(f"AI request rejected by Bedrock: {msg[:200]}") from e
                if code in _BEDROCK_TRANSIENT:
                    wait = 60 if code in ("ThrottlingException", "ServiceQuotaExceededException") else 20
                    raise TransientError(f"AI provider temporarily unavailable ({code})", retry_after_s=wait) from e
                if code in _BEDROCK_AUTH:
                    raise PermanentError(f"Bedrock refused the request ({code}). Check the AWS credentials, the region "
                                         f"({_settings.aws_region}) and that access to model '{model}' is enabled.") from e
                if code == "ResourceNotFoundException":
                    raise PermanentError(f"Bedrock model '{model}' not found in {_settings.aws_region}. "
                                         "Check LLM_MODEL_FAST / LLM_MODEL_STANDARD and AWS_REGION.") from e
                raise PermanentError(f"Bedrock error ({code}): {msg[:200]}") from e
            except BotoCoreError as e:  # network, endpoint, timeouts
                raise TransientError(f"AI provider temporarily unavailable ({type(e).__name__})", retry_after_s=20) from e
        text, calls, tin, tout = from_converse(resp)
        if text is None and not calls:
            raise TransientError("AI provider returned no answer (possibly filtered); will retry", retry_after_s=10)
        return resp, text, calls, tin, tout


_provider: LLMProvider | None = None
PROVIDERS = ("gemini", "openai", "bedrock", "openai_compatible")


def provider() -> LLMProvider:
    global _provider
    if _settings.llm_provider not in PROVIDERS:
        raise LLMNotConfigured(f"Unknown LLM_PROVIDER '{_settings.llm_provider}' (use one of: {', '.join(PROVIDERS)})")
    if not _settings.llm_configured:
        raise LLMNotConfigured(f"{_settings.llm_key_name} is not set")
    if _provider is None:
        _provider = BedrockProvider() if _settings.llm_provider == "bedrock" else OpenAICompatibleProvider(_settings.llm_provider)
    return _provider


def model_for(tier: str) -> str:
    return _settings.llm_model(tier)


_REGION_PREFIXES = ("us.", "eu.", "apac.", "global.", "us-gov.", "jp.", "au.", "ca.")


def price(model: str, tin: int, tout: int) -> float:
    key = model
    if key not in _settings.llm_pricing and key.startswith(_REGION_PREFIXES):
        key = key.split(".", 1)[1]  # Bedrock cross-region inference profile → base model id
    pin, pout = _settings.llm_pricing.get(key, (1.0, 4.0))  # unknown model → conservative estimate
    return (tin * pin + tout * pout) / 1_000_000


def parse_json_reply(text: str | None) -> dict:
    """JSON object from a model reply. Tolerates code fences and a sentence around the object."""
    s = (text or "").strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", s, re.S)
    if fenced:
        return json.loads(fenced.group(1))
    start, end = s.find("{"), s.rfind("}")
    if start != -1 and end > start:
        return json.loads(s[start:end + 1])
    raise json.JSONDecodeError("no JSON object in reply", s, 0)


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
        return parse_json_reply(res.content)
    except json.JSONDecodeError:
        messages += [{"role": "assistant", "content": res.content or ""},
                     {"role": "user", "content": "That was not valid JSON. Reply again with only the JSON object."}]
        res = call(ctx=ctx, prompt_id=prompt_id, version=version + "-repair", messages=messages, tier=tier,
                   json_mode=True, max_output_tokens=max_output_tokens)
        try:
            return parse_json_reply(res.content)
        except json.JSONDecodeError as e:
            raise PermanentError("AI returned invalid JSON twice") from e
