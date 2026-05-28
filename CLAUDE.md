# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

A Telegram group-moderation bot that flags spam with a TF-IDF + linear-SVM classifier. It runs as two decoupled stages: an offline training script that produces the model, and a long-running polling bot that consumes it. User-facing strings are in Persian; admin permission errors are in English.

## Commands

```bash
pip install -r requirements.txt   # install deps (Python 3.8+)
python train/train.py             # train -> writes model.pkl + vectorizer.pkl
python core/bot.py                # run the bot (long-running, infinity_polling)
```

There is no test suite, linter, or build step configured.

**Run both scripts from the repository root.** All file I/O uses bare CWD-relative paths (not script-relative), even though the scripts live in `train/` and `core/`. `train/train.py` writes `model.pkl`/`vectorizer.pkl` to the CWD, and `core/bot.py` loads them from the CWD at import time. If the working directories differ, the bot won't find the model. `data.csv`, `spam_messages.csv`, and `bot.log` resolve the same way.

## Architecture

Two stages connected by two pickle files (`model.pkl`, `vectorizer.pkl`), which are generated, untracked, and absent until you train.

- **`train/train.py`** — run-once offline. Reads `data.csv` (requires named `message` and `label` columns), fits a `TfidfVectorizer` (word 1–2 grams, `max_features=5000`, `min_df=2`, `max_df=0.9`) and an `SVC(kernel='linear', probability=True)`, prints test-set accuracy, and dumps both objects.
- **`core/bot.py`** — the running process. Loads both pickles, then on every message vectorizes the text and calls `model.predict` / `model.predict_proba`. A message is flagged when the prediction is `spam` **and** confidence > 0.4 (`core/bot.py:108`); it then warns the user inline and posts to the admins group with action buttons.

### The train ↔ bot contract

These two files must agree, or the bot breaks at runtime:
- The SVM **must** be trained with `probability=True` — the bot calls `predict_proba`.
- The positive class **must** be the literal string `"spam"` — the bot does `model.classes_.index("spam")` (`core/bot.py:82,105`). The negative label is conventionally `normal`.

### Spam handling flow

- `@bot.message_handler(func=lambda: True)` classifies every text message; non-text messages are ignored.
- Admin gating is repeated in every command and the callback handler: it re-fetches `get_chat_administrators` and checks `from_user.id` (or anonymous-admin `sender_chat`). See `admin_check` (`core/bot.py:131`).
- Admin commands (reply-based, admin-only): `/detect` (label a replied message via buttons), `/check` (show spam probability), `/send_data` (send the collected CSV).
- Callback actions are encoded in `callback_data` as `action:chat_id:msg_id` — do not change this format without updating `callback_handler`.
- `user_original_message` and `warning_messages` are in-memory dicts; pending state is lost on restart.

### Data-collection loop (note the mismatch)

`/detect` appends rows to `spam_messages.csv` as `[label, message]` with **no header** (`core/bot.py:167-169`). But `train/train.py` reads its input **by column name**, requiring a header row. So collected data is not directly trainable — you must add a `message,label` header (and align the columns) before reusing it as `data.csv`. The README's "just reuse spam_messages.csv as data.csv" glosses over this.

## Required configuration before running

- `AUTH_TOKEN` env var — bot token; the bot raises `ValueError` on startup if unset (`core/bot.py:9-11`).
- Hardcoded placeholders in `core/bot.py` that must be replaced with real values:
  - `LOGS_CHANNEL_ID` / `ADMINS_GROUP_ID` (`:26-27`) — currently `-123456789012`; keep the leading `-`.
  - Admin "review message" deep-link `https://t.me/SomeCoolGroup/...` (`:125`).
  - Advertisement link `https://t.me/ITheEqualizer` (`:113,119`).
- The bot must be a group admin with delete-message permission.

## Note on the README

The README describes a flat layout (`bot.py`, `train.py` at the repo root). The actual paths are `core/bot.py` and `train/train.py`. Trust the paths above.
