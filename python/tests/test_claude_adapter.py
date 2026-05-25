"""Unit tests for the Claude adapter — exercise the message-build path
without making real network calls."""
from unittest.mock import MagicMock

from redtonomous.models.claude import ClaudeAdapter


def _mock_response():
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "hello"
    usage = MagicMock(input_tokens=10, output_tokens=5)
    return MagicMock(content=[text_block], usage=usage)


def test_prompt_cache_on_by_default(monkeypatch):
    monkeypatch.delenv("REDTONOMOUS_CLAUDE_PROMPT_CACHE", raising=False)
    a = ClaudeAdapter(api_key="test")
    assert a.prompt_cache is True

    captured: dict = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return _mock_response()

    a.client.messages.create = fake_create
    a.chat(messages=[{"role": "user", "content": "hi"}], tools=[], system="be helpful")

    # System prompt was wrapped into a cache_control block.
    assert isinstance(captured["system"], list)
    assert captured["system"][0]["cache_control"] == {"type": "ephemeral"}
    # User message was promoted from str to list with cache_control.
    last_user = captured["messages"][-1]
    assert isinstance(last_user["content"], list)
    assert last_user["content"][-1]["cache_control"] == {"type": "ephemeral"}


def test_prompt_cache_off(monkeypatch):
    monkeypatch.setenv("REDTONOMOUS_CLAUDE_PROMPT_CACHE", "0")
    a = ClaudeAdapter(api_key="test")
    assert a.prompt_cache is False

    captured: dict = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return _mock_response()

    a.client.messages.create = fake_create
    a.chat(messages=[{"role": "user", "content": "hi"}], tools=[], system="be helpful")

    # System prompt stays a plain string.
    assert captured["system"] == "be helpful"
    # User message stays a plain string.
    assert captured["messages"][-1]["content"] == "hi"
