def dismiss_warning_message(bot, warning_messages, chat_id, message_id):
    """Delete a resolved warning and release its in-memory state."""
    key = (chat_id, message_id)
    warning_message = warning_messages.get(key)
    if warning_message is None:
        return False

    bot.delete_message(warning_message.chat.id, warning_message.message_id)
    warning_messages.pop(key, None)
    return True
