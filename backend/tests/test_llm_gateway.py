"""Gateway provider behaviour that doesn't need a network call (D-32)."""
from types import SimpleNamespace

from app.core.config import Settings
from app.llm import gateway


def _provider(name: str) -> gateway.OpenAICompatibleProvider:
    p = gateway.OpenAICompatibleProvider.__new__(gateway.OpenAICompatibleProvider)
    p.name = name
    return p


def test_model_defaults_follow_provider():
    assert Settings(llm_provider="gemini", llm_model_fast="").llm_model("fast") == "gemini-2.5-flash"
    assert Settings(llm_provider="openai", llm_model_standard=None).llm_model("standard") == "gpt-5-mini"
    assert Settings(llm_provider="gemini", llm_model_standard="gemini-2.5-pro").llm_model("standard") == "gemini-2.5-pro"


def test_key_follows_provider():
    s = Settings(llm_provider="gemini", gemini_api_key="g", openai_api_key=None)
    assert s.llm_configured and s.llm_api_key == "g" and s.llm_key_name == "GEMINI_API_KEY"
    assert not Settings(llm_provider="openai", gemini_api_key="g", openai_api_key=None).llm_configured


def test_gemini_request_shape():
    kw = _provider("gemini")._kwargs("gemini-2.5-flash", [], 4000, True, None, None)
    assert kw["max_tokens"] == 4000 and "max_completion_tokens" not in kw
    assert kw["extra_body"] == {"reasoning_effort": "low"} and kw["response_format"] == {"type": "json_object"}
    kw = _provider("openai")._kwargs("gpt-5-mini", [], 4000, False, None, None)
    assert kw["max_completion_tokens"] == 4000 and "max_tokens" not in kw


def test_gemini_thinking_tokens_counted_and_signature_kept():
    tc = SimpleNamespace(id="", function=SimpleNamespace(name="finish", arguments='{"claims": []}'),
                         model_extra={"extra_content": {"google": {"thought_signature": "abc"}}})
    msg = SimpleNamespace(content=None, tool_calls=[tc])
    resp = SimpleNamespace(choices=[SimpleNamespace(message=msg)],
                           usage=SimpleNamespace(prompt_tokens=100, completion_tokens=20, total_tokens=320))
    p = _provider("gemini")
    p.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **k: resp)))
    _, _, calls, tin, tout = p.chat(model="gemini-2.5-flash", messages=[], max_output_tokens=100,
                                    json_mode=False, tools=None, tool_choice=None)
    assert (tin, tout) == (100, 220)
    assert calls == [{"id": "call_0", "name": "finish", "arguments": {"claims": []},
                      "extra_content": {"google": {"thought_signature": "abc"}}}]


def test_rate_limit_becomes_transient_with_a_minute_wait():
    import httpx
    import openai
    import pytest
    from app.workflow.errors import TransientError

    req = httpx.Request("POST", "https://example.invalid")
    err = openai.RateLimitError("429", response=httpx.Response(429, request=req), body=None)

    def boom(**kw):
        raise err

    p = _provider("gemini")
    p.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=boom)))
    with pytest.raises(TransientError) as e:
        p.chat(model="gemini-2.5-flash", messages=[], max_output_tokens=10, json_mode=False, tools=None, tool_choice=None)
    assert e.value.retry_after_s == 60


def test_pacing_spaces_calls_to_the_rpm_limit(monkeypatch):
    waits = []
    monkeypatch.setattr(gateway._settings, "llm_max_rpm", 10)
    monkeypatch.setattr(gateway, "_rpm_throttle", None)
    monkeypatch.setattr("app.providers.http.time.sleep", lambda s: waits.append(s))
    gateway._pace()
    gateway._pace()
    assert gateway._rpm_throttle.interval == 6.0 and waits and 5.0 < waits[0] <= 6.0
    monkeypatch.setattr(gateway._settings, "llm_max_rpm", 0)
    monkeypatch.setattr(gateway, "_rpm_throttle", None)
    gateway._pace()
    assert gateway._rpm_throttle is None


def test_daily_quota_trips_breaker_and_stops_further_calls(monkeypatch):
    import httpx
    import openai
    import pytest
    from app.workflow.errors import AIQuotaExhausted

    req = httpx.Request("POST", "https://example.invalid")
    body = ("{'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier', 'quotaValue': '20'}, "
            "{'@type': 'RetryInfo', 'retryDelay': '55219s'}")
    err = openai.RateLimitError(body, response=httpx.Response(429, request=req), body=None)
    calls = []

    def boom(**kw):
        calls.append(1)
        raise err

    monkeypatch.setattr(gateway, "_quota_until", 0.0)
    monkeypatch.setattr(gateway._settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(gateway._settings, "llm_provider", "gemini")
    p = _provider("gemini")
    p.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=boom)))
    kw = dict(model="gemini-2.5-flash", messages=[], max_output_tokens=10, json_mode=False, tools=None, tool_choice=None)
    with pytest.raises(AIQuotaExhausted):
        p.chat(**kw)
    assert not gateway.ai_available()
    assert 6 * 3600 - 5 <= gateway._quota_until - __import__("time").time() <= 6 * 3600  # capped at 6 h
    with pytest.raises(AIQuotaExhausted):  # no second request to the provider
        p.chat(**kw)
    assert len(calls) == 1
