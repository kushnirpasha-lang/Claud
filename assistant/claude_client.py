import threading
from anthropic import Anthropic
from config import SYSTEM_PROMPT, CLAUDE_MODEL, MAX_TOKENS, MAX_HISTORY

_client = None
_client_lock = threading.Lock()
_conversations: dict[str, list] = {}
_conv_lock = threading.Lock()

# System prompt with cache_control — charged full price once, then 10% on cache hits
_CACHED_SYSTEM = [
    {
        "type": "text",
        "text": SYSTEM_PROMPT,
        "cache_control": {"type": "ephemeral"},
    }
]


def _get_client() -> Anthropic:
    global _client
    with _client_lock:
        if _client is None:
            import os
            _client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        return _client


def _sanitize_messages(messages: list) -> list:
    """Remove empty text blocks that cause cache_control API errors."""
    result = []
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, list):
            cleaned = [
                blk for blk in content
                if not (blk.get("type") == "text" and not (blk.get("text") or "").strip())
            ]
            if cleaned:
                result.append({**msg, "content": cleaned})
        elif isinstance(content, str) and content.strip():
            result.append(msg)
        else:
            result.append(msg)
    return result


def chat(conversation_id: str, message: str) -> str:
    if not (message or "").strip():
        raise ValueError("message must not be empty")
    with _conv_lock:
        if conversation_id not in _conversations:
            _conversations[conversation_id] = []
        _conversations[conversation_id].append({"role": "user", "content": message})
        history = list(_conversations[conversation_id][-MAX_HISTORY:])

    response = _get_client().messages.create(
        model=CLAUDE_MODEL,
        max_tokens=MAX_TOKENS,
        system=_CACHED_SYSTEM,
        messages=_sanitize_messages(history),
    )

    reply = response.content[0].text

    with _conv_lock:
        _conversations[conversation_id].append({"role": "assistant", "content": reply})

    return reply


def clear(conversation_id: str) -> None:
    with _conv_lock:
        _conversations.pop(conversation_id, None)


_INSTAGRAM_PROMPT = """Ты — контент-менеджер бренда HairLove (@hair_love_company).
Твоя задача: написать подпись к фото для Instagram.

ГОЛОС БРЕНДА HairLove:
- Тон: живой, тёплый, экспертный — как совет от подруги-профессионала
- Язык: русский
- Без пафоса и рекламных штампов
- Говорим о конкретном результате, не об "уникальности"
- Допускается лёгкая эмоциональность, но без кринжа

СТРУКТУРА ПОСТА (гибкая):
1. Зацепка — первая строка должна остановить скролл
2. Суть — что это, как работает, зачем нужно (свойство → действие → результат)
3. Призыв — мягкий, не агрессивный
4. Хэштеги — 5-10 штук в конце

ЗАПРЕЩЕНО (правила гуманизатора):
- Слова: уникальный, неповторимый, инновационный, непревзойдённый, роскошный, идеальный выбор, премиальное качество, выводит уход на новый уровень, подарит незабываемые ощущения
- Конструкции: "является ключевым", "служит", "выступает в роли", "стоит отметить", "важно подчеркнуть"
- Шаблоны: "создан для тех, кто ценит", "заботится о вас каждый день", "раскрывает красоту"
- Отрицательные параллелизмы: "это не просто X, это Y"
- Раздувание значимости: "ознаменовал новую эру", "играет ключевую роль"
- Все предложения одной длины — меняй ритм
- Списки с жирными заголовками и эмодзи в каждой строке

ОБЯЗАТЕЛЬНО:
- Конкретика: называй ингредиенты, эффекты, ощущения — то что видно на фото
- Живой ритм: чередуй короткие и длинные предложения
- Пиши так, чтобы текст нормально читался вслух

Напиши ТОЛЬКО текст поста. Без пояснений, без "вот пост:", без лишних слов."""


def generate_instagram_caption(image_bytes: bytes, mime_type: str, hint: str = "") -> str:
    import base64
    client = _get_client()

    user_content = []
    if image_bytes:
        user_content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": mime_type,
                "data": base64.standard_b64encode(image_bytes).decode("utf-8"),
            },
        })

    text = "Напиши подпись для этого фото."
    if hint:
        text += f" Пожелание: {hint}"
    user_content.append({"type": "text", "text": text})

    if not user_content:
        raise ValueError("No content to send (image_bytes is empty)")

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=_INSTAGRAM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    return response.content[0].text.strip()
