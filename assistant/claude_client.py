import threading
from anthropic import Anthropic
from config import SYSTEM_PROMPT, CLAUDE_MODEL, MAX_TOKENS, MAX_HISTORY

_client = None
_client_lock = threading.Lock()
_conversations: dict[str, list] = {}
_conv_lock = threading.Lock()

# Plain system prompt without cache_control — avoids SDK auto-injecting cache_control
# into messages which creates empty text blocks and causes 400 errors.
_SYSTEM = SYSTEM_PROMPT


def _get_client() -> Anthropic:
    global _client
    with _client_lock:
        if _client is None:
            import os
            _client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        return _client


def chat(conversation_id: str, message: str) -> str:
    with _conv_lock:
        if conversation_id not in _conversations:
            _conversations[conversation_id] = []
        _conversations[conversation_id].append({"role": "user", "content": message})
        history = list(_conversations[conversation_id][-MAX_HISTORY:])

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
