import threading
from anthropic import Anthropic
from config import SYSTEM_PROMPT, CLAUDE_MODEL, MAX_TOKENS, MAX_HISTORY

_client = None
_client_lock = threading.Lock()
_conversations: dict[str, list] = {}
_conv_lock = threading.Lock()

_SYSTEM = SYSTEM_PROMPT


def _get_client() -> Anthropic:
    global _client
    with _client_lock:
        if _client is None:
            import os
            _client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        return _client


def _sanitize_messages(messages: list) -> list:
    cleaned = []
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, list):
            blocks = []
            for block in content:
                if not isinstance(block, dict):
                    continue
                b = {k: v for k, v in block.items() if k != "cache_control"}
                if b.get("type") == "text" and not b.get("text", "").strip():
                    continue
                blocks.append(b)
            if not blocks:
                continue
            cleaned.append({"role": msg["role"], "content": blocks})
        elif isinstance(content, str):
            if content.strip():
                cleaned.append({"role": msg["role"], "content": content})
        else:
            cleaned.append(msg)
    while cleaned and cleaned[0]["role"] != "user":
        cleaned.pop(0)
    return cleaned


def chat(conversation_id: str, message: str) -> str:
    with _conv_lock:
        if conversation_id not in _conversations:
            _conversations[conversation_id] = []
        _conversations[conversation_id].append({"role": "user", "content": message})
        raw_history = list(_conversations[conversation_id][-MAX_HISTORY:])

    history = _sanitize_messages(raw_history)

    response = _get_client().messages.create(
        model=CLAUDE_MODEL,
        max_tokens=MAX_TOKENS,
        system=_SYSTEM,
        messages=history,
    )

    reply = response.content[0].text

    with _conv_lock:
        _conversations[conversation_id].append({"role": "assistant", "content": reply})

    return reply


def clear(conversation_id: str) -> None:
    with _conv_lock:
        _conversations.pop(conversation_id, None)
