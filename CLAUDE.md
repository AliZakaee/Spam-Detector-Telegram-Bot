# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

A Telegram group-moderation bot that flags spam. Classification has two backends that can run alone or together:

- **TypeSafe (Jev)** — a System One model that returns structured Choice / Noul / Score answers. No local training and no pickle files. Set `TYPESAFE_API_KEY`.
- **TF-IDF + linear SVM** — optional, community-specific. Offline `train/train.py` writes `model.pkl` + `vectorizer.pkl`; the bot loads them.

The running process is a long-polling bot (`core/bot.py`). User-facing strings are in Persian; admin permission errors are in English.

## Commands

```bash
pip install -r requirements.txt   # install deps (Python 3.10+; TypeSafe SDK requires this)
python train/train.py             # optional: train local SVM -> model.pkl + vectorizer.pkl
python core/bot.py                # run the bot (long-running, infinity_polling)
python -m unittest discover -v    # unit tests (run from the repository root)
```

**Run scripts from the repository root.** Training I/O uses repo-root paths (`data.csv`, `model.pkl`, `vectorizer.pkl`). The bot resolves `spam_messages.csv`, pickle files, and `bot.log` from the repo root (`BASE_DIR`), not CWD.

## Architecture

`CLASSIFIER_BACKEND` (default `auto`) selects how every text message is judged:

| Backend | When | Behavior |
| --- | --- | --- |
| `typesafe` | `TYPESAFE_API_KEY` set | One TypeSafe request per message. No pickles required. |
| `svm` | `model.pkl` + `vectorizer.pkl` present | Local `predict_proba`. Requires training. |
| `hybrid` | both available | TypeSafe + SVM; **either** side can flag (this bot queues for admin review). TypeSafe errors fall back to SVM. |
| `auto` | default | `hybrid` if both, else `typesafe`, else `svm`. Exits if neither is configured. |

TypeSafe questions and numeric cutoffs live in `core/typesafe_moderation.py` (one file on purpose). Each message is one request with:

- **Choice `verdict`**: `spam` vs `normal`, plus `confidence`
- **Noul hazards** (independent): unsolicited ad, scam/phishing, mass promo/invite, suspicious link/impersonation
- **Score `severity`**: 0 harmless … 3 harmful deception

`core/typesafe_moderation.py:route_typesafe_answers` composes those answers in code (confidence-gated Choice/Score; any Noul above `SPAM_THRESHOLD` can flag). TypeSafe API failures **fail open** (treat as not-spam) so a group is not frozen; hybrid then uses the SVM.

The SVM train ↔ bot contract is unchanged when that backend is used:

- The SVM **must** be trained with `probability=True`
- The positive class **must** be the literal string `"spam"` (negative: `normal`)

### Spam handling flow

- `@bot.message_handler(func=lambda: True)` classifies every text message; non-text messages are ignored.
- A message is flagged when `ClassificationResult.should_flag` is true (SVM: label `spam` and probability > `SPAM_THRESHOLD`; TypeSafe: routed policy above). The bot warns the user inline and posts to the admins group with action buttons. Admin alerts include the backend and TypeSafe hazard reasons when present.
- Admin gating is repeated in every command and the callback handler: it re-fetches `get_chat_administrators` and checks `from_user.id` (or anonymous-admin `sender_chat`). See `is_admin` (`core/bot.py`).
- Admin commands: `/detect` (label a replied message via buttons into `spam_messages.csv` for optional SVM retraining), `/check` (show spam probability and TypeSafe detail), `/send_data` (send the collected CSV), `/status` (which classifier is running).
- Callback actions are encoded in `callback_data` as `action:chat_id:msg_id` — do not change this format without updating `callback_handler`.
- `user_original_message` and `warning_messages` are in-memory dicts; pending state is lost on restart.

### Data-collection loop

`/detect` appends rows to `spam_messages.csv` as `message,label` with a header, matching `train/train.py`. Collected data trains the **local SVM only**. TypeSafe/Jev is not fine-tuned on customer CSV; it is steered through the questions and `community_policy` in `core/typesafe_moderation.py`.

## Required configuration before running

- `AUTH_TOKEN`, `LOGS_CHANNEL_ID`, `ADMINS_GROUP_ID` — required; the bot raises if unset (`core/bot.py`).
- **Either** `TYPESAFE_API_KEY` **or** trained `model.pkl`/`vectorizer.pkl` (or both).
- Optional: `CLASSIFIER_BACKEND`, `SPAM_THRESHOLD` (default `0.4`), `TYPESAFE_CONFIDENCE_FLOOR` (default `0.5`), `AD_LINK`, `GROUP_USERNAME`.
- The bot must be a group admin with delete-message permission.

Jev’s strongest language is English; Persian is accepted but less accurate. For a Persian community, TypeSafe still lets you run with no dataset, and hybrid plus a local SVM trained on `/detect` labels is the better long-term setup.

## Note on the README

The README describes `core/bot.py` and `train/train.py`. Trust those paths.
