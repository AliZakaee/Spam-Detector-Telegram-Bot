def get_username(message):
    """Return a Markdown-safe identity for a user or sender chat."""
    user = getattr(message, "from_user", None)
    if user is not None:
        if user.username:
            return f"@{user.username} (`{user.id}`)"
        return f"کاربر بدون نام کاربری با آیدی عددی `{user.id}`"

    sender_chat = getattr(message, "sender_chat", None)
    if sender_chat is not None:
        if sender_chat.username:
            return f"@{sender_chat.username} (`{sender_chat.id}`)"
        return f"چت فرستنده با آیدی عددی `{sender_chat.id}`"

    return "فرستنده ناشناس"
