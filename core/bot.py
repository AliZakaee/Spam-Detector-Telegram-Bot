import csv
import logging
import os
import sys

import joblib
import telebot
from dotenv import load_dotenv
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, ReactionTypeEmoji

# Make the repo root importable so the shared normalizer is found regardless of CWD.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from preprocessing import ACTIVE_BACKEND, normalize_text

load_dotenv(os.path.join(BASE_DIR, ".env"))

# --- Configuration (all from environment / .env, nothing hardcoded) ---
AUTH_TOKEN = os.environ.get("AUTH_TOKEN")
LOGS_CHANNEL_ID = os.environ.get("LOGS_CHANNEL_ID")
ADMINS_GROUP_ID = os.environ.get("ADMINS_GROUP_ID")
AD_LINK = os.environ.get("AD_LINK", "https://t.me/ITheEqualizer")
GROUP_USERNAME = os.environ.get("GROUP_USERNAME", "")  # used to build the admin "review message" deep-link
try:
    SPAM_THRESHOLD = float(os.environ.get("SPAM_THRESHOLD", "0.4"))
except ValueError:
    SPAM_THRESHOLD = 0.4

_missing = [name for name in ("AUTH_TOKEN", "LOGS_CHANNEL_ID", "ADMINS_GROUP_ID") if not os.environ.get(name)]
if _missing:
    raise ValueError(f"Missing required environment variable(s): {', '.join(_missing)}. See .env.example.")

DATA_FILE = os.path.join(BASE_DIR, "spam_messages.csv")
MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")
VECTORIZER_PATH = os.path.join(BASE_DIR, "vectorizer.pkl")
LOG_PATH = os.path.join(BASE_DIR, "bot.log")

bot = telebot.TeleBot(AUTH_TOKEN)

# Keep console quiet (CRITICAL) but log everything to bot.log for later inspection.
logger = telebot.logger
logger.setLevel(logging.CRITICAL)
file_handler = logging.FileHandler(LOG_PATH)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(file_handler)

try:
    model = joblib.load(MODEL_PATH)
    vectorizer = joblib.load(VECTORIZER_PATH)
except (FileNotFoundError, OSError) as exc:
    raise SystemExit(f"Could not load model/vectorizer ({exc}). Run 'python train/train.py' first.")

# The bot reads the 'spam' class probability directly; cache its index once.
try:
    SPAM_INDEX = list(model.classes_).index("spam")
except ValueError:
    raise SystemExit("Loaded model has no 'spam' class. Retrain with a dataset that contains 'spam' labels.")

print(f"Bot starting — normalization backend: {ACTIVE_BACKEND}, spam threshold: {SPAM_THRESHOLD}")


def is_admin(chat_id, user_id, sender_chat=None):
    """True if user_id is an admin of chat_id (or the message was sent by the chat itself)."""
    admins = bot.get_chat_administrators(chat_id)
    if any(admin.user.id == user_id for admin in admins):
        return True
    return bool(sender_chat and sender_chat.id == chat_id)


def admin_only(func):
    """Decorator: gate a command handler so only admins can run it."""
    def wrapper(message):
        if is_admin(message.chat.id, message.from_user.id, message.sender_chat):
            return func(message)
        bot.reply_to(message, "You need to be an admin to use this command!")
    wrapper.__name__ = func.__name__
    return wrapper


def classify(text):
    """Return (label, spam_confidence) from a single predict_proba pass over normalized text."""
    X_new = vectorizer.transform([normalize_text(text)])
    proba = model.predict_proba(X_new)[0]
    spam_confidence = proba[SPAM_INDEX]
    label = model.classes_[proba.argmax()]
    return label, spam_confidence


def get_username(message):
    if message.from_user.username:
        return '@' + message.from_user.username + ' ' + f'(`{message.from_user.id}`)'
    return f'کاربر بدون نام کاربری با آیدی عددی `{message.from_user.id}`'


# /detect labels a replied-to message as spam/normal and stores its text for the callback to save.
user_original_message = {}
@bot.message_handler(commands=["detect"])
@admin_only
def spam_message(message):
    if not message.reply_to_message:
        bot.reply_to(message, "You need to reply to a message to mark it!")
        return
    reply = message.reply_to_message
    if not reply.text:
        bot.reply_to(message, "The replied message has no text to label.")
        return

    user_original_message[(message.chat.id, reply.message_id)] = reply.text
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton('Spam', callback_data=f'spam:{message.chat.id}:{reply.message_id}'),  # callback format: action:chat_id:msg_id
        InlineKeyboardButton('Normal', callback_data=f'normal:{message.chat.id}:{reply.message_id}'),
    )
    bot.reply_to(message, "Choose the type which fits this message. This action cannot be undone.", reply_markup=markup)


@bot.message_handler(commands=['send_data'])
@admin_only
def send_data(message):
    if not os.path.exists(DATA_FILE) or os.path.getsize(DATA_FILE) == 0:
        bot.reply_to(message, "No spam messages found.")
        return
    with open(DATA_FILE, 'r', encoding='utf-8') as file:
        line_count = sum(1 for _ in file)
    total_amount = max(line_count - 1, 0)  # exclude the header row
    with open(DATA_FILE, 'rb') as f:
        bot.send_document(message.chat.id, f, caption=f"Spam message data with a total of *{total_amount}* entries.", parse_mode='Markdown')


@bot.message_handler(commands=['check'])
@admin_only
def check_message(message):
    if not message.reply_to_message or not message.reply_to_message.text:
        bot.reply_to(message, "You need to reply to a text message to check it!")
        return
    label, spam_confidence = classify(message.reply_to_message.text)
    if label == 'spam':
        bot.reply_to(message, f"پیام مورد نظر با احتمال *{spam_confidence*100:.2f}%* اسپم شناسایی شده است.", parse_mode='Markdown')
    else:
        bot.reply_to(message, "پیام مورد نظر اسپم شناسایی نشد.")


# Every text message is classified; flagged ones warn the user and notify the admins group.
warning_messages = {}
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text
    if not text:
        return

    label, spam_confidence = classify(text)
    if label == 'spam' and spam_confidence > SPAM_THRESHOLD:
        username = get_username(message)
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton('⛔️ پیام اسپم ⛔️', callback_data=f'spamdetected:{message.chat.id}:{message.message_id}'),
            InlineKeyboardButton('❇️ تبلیغات ❇️', url=AD_LINK),
        )

        warning_messages[(message.chat.id, message.message_id)] = bot.reply_to(message, f"""
پیام شما با احتمال **{spam_confidence*100:.2f}%** اسپم و تبلیغات شناسایی شده است و در انتظار تایید توسط ادمین است.

در صورت تمایل به سفارش تبلیغات [اینجا]({AD_LINK}) کلیک کنید و یا از دکمه زیر همین پیام استفاده کنید.

در صورت بررسی و عدم وجود مشکل علامت 👍 در زیر پیام شما قرار خواهد گرفت و در غیر این صورت پیام شما حذف خواهد شد.
""", parse_mode='Markdown', reply_markup=markup)

        admin_markup = InlineKeyboardMarkup()
        admin_buttons = []
        if GROUP_USERNAME:
            admin_buttons.append(InlineKeyboardButton('بررسی پیام', url=f'https://t.me/{GROUP_USERNAME}/{message.message_id}'))
        admin_buttons.append(InlineKeyboardButton('اسپم نیست', callback_data=f'checked:{message.chat.id}:{message.message_id}'))
        admin_markup.add(*admin_buttons)
        bot.send_message(ADMINS_GROUP_ID, f"یک پیام احتمالی اسپم با احتمال {spam_confidence*100:.2f}% از {username} شناسایی شده است و نیازمند تایید شماست.", parse_mode='Markdown', reply_markup=admin_markup)


@bot.callback_query_handler(func=lambda call: is_admin(call.message.chat.id, call.from_user.id, getattr(call, 'sender_chat', None)))
def callback_handler(call):
    try:
        action, chat_id, msg_id = call.data.split(":", 2)
        chat_id = int(chat_id)
        msg_id = int(msg_id)
    except (ValueError, AttributeError):
        logger.error("Malformed callback_data: %r", call.data)
        bot.answer_callback_query(call.id, "درخواست نامعتبر است.")
        return

    if action == 'spamdetected':
        try:
            bot.send_message(LOGS_CHANNEL_ID, f"""پیام اسپم از کاربر شناسایی و حذف شد
 ادمین: {call.from_user.first_name}(`{call.from_user.id}`)

#spam""", parse_mode='Markdown')
            bot.forward_message(LOGS_CHANNEL_ID, chat_id, msg_id)
            bot.delete_message(chat_id, msg_id)
            warning_message = warning_messages.pop((chat_id, msg_id), None)
            if warning_message:
                bot.delete_message(warning_message.chat.id, warning_message.message_id)
            bot.answer_callback_query(call.id, "پیام اسپم حذف شد.", show_alert=True)
        except Exception as exc:
            logger.error("Failed to delete spam message %s/%s: %s", chat_id, msg_id, exc)
            bot.answer_callback_query(call.id, "خطا در حذف پیام.", show_alert=True)

    elif action in ('spam', 'normal'):
        original_message = user_original_message.pop((chat_id, msg_id), None)
        if not original_message:
            bot.answer_callback_query(call.id, "Message not found.")
            return

        # Write directly in train.py's expected schema: 'message,label' with a header.
        write_header = not os.path.exists(DATA_FILE) or os.path.getsize(DATA_FILE) == 0
        with open(DATA_FILE, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            if write_header:
                writer.writerow(["message", "label"])
            writer.writerow([original_message, action])

        bot.edit_message_text(
            f"*{action.capitalize()}* message has been added!",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown',
        )
        bot.send_message(LOGS_CHANNEL_ID, f"""*{action.capitalize()}* message has been added!
ادمین: {call.from_user.first_name}(`{call.from_user.id}`)

#flag""", parse_mode='Markdown')
        bot.forward_message(LOGS_CHANNEL_ID, chat_id, msg_id)
        bot.answer_callback_query(call.id)

    elif action == 'checked':
        try:
            bot.set_message_reaction(chat_id, msg_id, reaction=[ReactionTypeEmoji(emoji="👍")])
            bot.answer_callback_query(call.id, "پیام تایید شد.", show_alert=True)
        except Exception as exc:
            logger.error("Failed to confirm message %s/%s: %s", chat_id, msg_id, exc)
            bot.answer_callback_query(call.id, "خطا در تایید پیام.", show_alert=True)

    else:
        bot.answer_callback_query(call.id, "عملیات ناشناخته.")


if __name__ == "__main__":
    bot.infinity_polling()
