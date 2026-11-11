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
