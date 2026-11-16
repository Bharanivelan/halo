"""AI providers (D-49): Amazon Bedrock translation and fallbacks, OpenAI-compatible servers, JSON replies.

No network: the Bedrock client is replaced by a stub.
"""
import json

import pytest
from botocore.exceptions import ClientError

from app.core.config import Settings
from app.llm import gateway
from app.workflow.errors import PermanentError, TransientError

FETCH = {"type": "function", "function": {"name": "fetch_page", "description": "Fetch a page",
                                          "parameters": {"type": "object", "properties": {"url": {"type": "string"}}}}}
FINISH = {"type": "function", "function": {"name": "finish", "description": "Done", "parameters": {"type": "object"}}}


def test_openai_style_conversation_becomes_converse():
    messages = [
        {"role": "system", "content": "You are a researcher."},
        {"role": "user", "content": "Research acme.example"},
        {"role": "assistant", "content": None, "tool_calls": [
            {"id": "t1", "type": "function", "function": {"name": "fetch_page", "arguments": json.dumps({"url": "https://acme.example"})}},
            {"id": "t2", "type": "function", "function": {"name": "fetch_page", "arguments": "{\"url\": \"https://acme.example/about\"}"},
             "extra_content": {"google": {"thought_signature": "x"}}}]},
        {"role": "tool", "tool_call_id": "t1", "content": "Home page text"},
        {"role": "tool", "tool_call_id": "t2", "content": ""},
        {"role": "user", "content": "Call finish now with your claims."},
    ]
    system, conv, cfg = gateway.to_converse(messages, [FETCH, FINISH], {"type": "function", "function": {"name": "finish"}})
    assert system == [{"text": "You are a researcher."}]
    assert [m["role"] for m in conv] == ["user", "assistant", "user"]  # strictly alternating
    assert conv[1]["content"][0]["toolUse"] == {"toolUseId": "t1", "name": "fetch_page", "input": {"url": "https://acme.example"}}
    results = [b for b in conv[2]["content"] if "toolResult" in b]
    assert [r["toolResult"]["toolUseId"] for r in results] == ["t1", "t2"]
    assert results[1]["toolResult"]["content"] == [{"text": "(empty)"}]  # no empty text blocks
    assert conv[2]["content"][-1] == {"text": "Call finish now with your claims."}
    assert cfg["toolChoice"] == {"tool": {"name": "finish"}}
    assert cfg["tools"][0]["toolSpec"]["inputSchema"]["json"]["properties"]["url"] == {"type": "string"}
    assert gateway.to_converse(messages, [FETCH], "auto")[2]["toolChoice"] == {"auto": {}}


def test_converse_reply_becomes_text_tool_calls_and_tokens():
    resp = {"output": {"message": {"role": "assistant", "content": [
        {"text": "Looking."}, {"toolUse": {"toolUseId": "u1", "name": "finish", "input": {"claims": []}}}]}},
        "usage": {"inputTokens": 120, "outputTokens": 30}}
    assert gateway.from_converse(resp) == ("Looking.", [{"id": "u1", "name": "finish", "arguments": {"claims": []}}], 120, 30)


class StubBedrock:
    """Records requests; raises the queued errors first, then answers."""

    def __init__(self, errors=(), answer=None):
        self.errors, self.requests = list(errors), []
        self.answer = answer or {"output": {"message": {"content": [{"text": "{\"ok\": true}"}]}},
                                 "usage": {"inputTokens": 10, "outputTokens": 5}}

    def converse(self, **req):
        self.requests.append(json.loads(json.dumps(req)))
        if self.errors:
            code, message = self.errors.pop(0)
            raise ClientError({"Error": {"Code": code, "Message": message}}, "Converse")
        return self.answer


@pytest.fixture
def bedrock(monkeypatch):
    monkeypatch.setattr(gateway, "_pace", lambda: None)
    monkeypatch.setattr(gateway, "ai_available", lambda: True)

    def make(stub):
        p = object.__new__(gateway.BedrockProvider)
        p.client = stub
        return p
    return make


def _chat(p, **kw):
    args = {"model": "amazon.nova-lite-v1:0", "messages": [{"role": "system", "content": "Rules."}, {"role": "user", "content": "Hi"}],
            "max_output_tokens": 6000, "json_mode": False, "tools": None, "tool_choice": None}
    return p.chat(**{**args, **kw})


def test_bedrock_retries_with_what_the_model_supports(bedrock):
    stub = StubBedrock(errors=[("ValidationException", "This model doesn't support the toolChoice.tool field."),
                               ("ValidationException", "This model doesn't support system messages."),
                               ("ValidationException", "The maximum tokens you requested exceeds the model limit")])
    _, text, calls, tin, tout = _chat(bedrock(stub), tools=[FETCH, FINISH],
                                      tool_choice={"type": "function", "function": {"name": "finish"}})
    first, last = stub.requests[0], stub.requests[-1]
    assert first["toolConfig"]["toolChoice"] == {"tool": {"name": "finish"}} and "system" in first
    assert last["toolConfig"]["toolChoice"] == {"any": {}}  # still forces a tool call
    assert "system" not in last and last["messages"][0]["content"][0] == {"text": "Rules."}
    assert last["inferenceConfig"]["maxTokens"] == 3000
    assert (text, tin, tout) == ("{\"ok\": true}", 10, 5)


def test_bedrock_json_mode_asks_for_json(bedrock):
    stub = StubBedrock()
    _chat(bedrock(stub), json_mode=True)
    assert stub.requests[0]["messages"][-1]["content"][0]["text"].endswith("Reply with only the JSON object, no other text.")


@pytest.mark.parametrize("code,kind,words", [
    ("ThrottlingException", TransientError, "temporarily unavailable"),
    ("AccessDeniedException", PermanentError, "access to model"),
    ("ResourceNotFoundException", PermanentError, "not found"),
])
def test_bedrock_errors_are_readable(bedrock, code, kind, words):
    with pytest.raises(kind, match=words):
        _chat(bedrock(StubBedrock(errors=[(code, "nope")])))


def test_bedrock_explains_inference_profiles(bedrock):
    msg = "Invocation of model ID anthropic.x with on-demand throughput isn't supported. Retry with an inference profile."
    with pytest.raises(PermanentError, match="inference profile"):
        _chat(bedrock(StubBedrock(errors=[("ValidationException", msg)])))


def test_json_replies_with_fences_or_chatter_are_accepted():
    assert gateway.parse_json_reply('```json\n{"a": 1}\n```') == {"a": 1}
    assert gateway.parse_json_reply('Here you go: {"a": {"b": 2}} Hope it helps.') == {"a": {"b": 2}}
    with pytest.raises(json.JSONDecodeError):
        gateway.parse_json_reply("no json here")


def test_cross_region_bedrock_ids_are_priced_like_the_base_model():
    assert gateway.price("us.amazon.nova-pro-v1:0", 1_000_000, 0) == gateway.price("amazon.nova-pro-v1:0", 1_000_000, 0) == 0.80


def test_provider_settings():
    s = Settings(_env_file=None, llm_provider="openai_compatible", openai_compatible_base_url="http://localhost:11434/v1",
                 llm_model_fast="llama3.1")
    assert s.llm_configured and s.llm_model("standard") == "llama3.1"  # one model serves both tiers
    assert not Settings(_env_file=None, llm_provider="openai_compatible", openai_compatible_base_url="http://x").llm_configured
    b = Settings(_env_file=None, llm_provider="bedrock", aws_access_key_id="AKIAEXAMPLE", aws_secret_access_key="x")
    assert b.llm_configured and b.llm_model("fast") == "amazon.nova-lite-v1:0"
    assert "AWS" in b.llm_key_name
    assert Settings(_env_file=None, llm_provider="gemini").llm_configured is False
    blank = Settings(_env_file=None, aws_profile="", aws_access_key_id=" ", aws_region="", llm_model_fast="")
    assert (blank.aws_profile, blank.aws_access_key_id, blank.aws_region, blank.llm_model_fast) == (None, None, "us-east-1", None)
