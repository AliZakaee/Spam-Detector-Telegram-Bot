# Spam Detector Telegram Bot

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-green)](https://core.telegram.org/bots)

## Overview / توصیف پروژه

### English
**Spam Detector Telegram Bot** flags spam in Telegram groups. You can run it in two ways:

1. **TypeSafe (no training)** — set `TYPESAFE_API_KEY` and start the bot. [TypeSafe](https://docs.typesafe.ai/introduction) Jev returns structured spam judgments (choice, hazard probabilities, severity) that the bot thresholds in code.
2. **Your own SVM** — label messages with `/detect`, export them with `/send_data`, train with `python train/train.py`. Useful for community-specific Persian slang.

If both are configured, `CLASSIFIER_BACKEND=auto` uses **hybrid** mode: either judge can flag a message for admin review, and a TypeSafe outage falls back to the local model.

Flagged messages still go to admins (warning the user, review buttons, delete or confirm). The bot does not auto-delete without an admin click.

#### Key Features
- **Zero-training TypeSafe path**: run immediately with an API key; no `data.csv` or pickle files.
- **Optional local SVM**: TF-IDF + linear SVM trained on your CSV for group-specific language.
- **Hybrid mode**: TypeSafe semantic judgments plus the local model; SVM-only still works offline.
- **Confidence-gated flagging**: TypeSafe Choice/Score answers are ignored when confidence is below `TYPESAFE_CONFIDENCE_FLOOR`; independent Noul hazards can still flag.
- **Admin tools**: `/check` (probability + reasons), `/detect` (label for SVM training), `/send_data`, `/status` (which backend is live).
- **Logging**: errors in `bot.log`; delete/flag actions forwarded to a logs channel.
- **Persian support**: user-facing copy is Persian. Jev is strongest in English; a local SVM still helps on Persian slang.

#### Project Structure
- `core/bot.py`: Telegram handlers, commands, and callbacks.
- `core/classifier.py`: SVM, TypeSafe, and hybrid backends.
- `core/typesafe_moderation.py`: TypeSafe questions, state, and routing policy (the file to edit when spam rules change).
- `train/train.py`: Train the SVM from `data.csv` (`message`, `label`), save `model.pkl` and `vectorizer.pkl`.
- `preprocessing.py`: Shared Persian text normalization for the trainer and the SVM path.
- `requirements.txt`: Python packages, including `typesafe-sdk`.
- `.env.example`: Configuration template.
- `data.csv`: SVM training set (not included; user-provided).
- `spam_messages.csv`: Labels collected by `/detect` (same schema as `data.csv`).
- `model.pkl` & `vectorizer.pkl`: SVM artifacts after training.
- `bot.log`: Generated log file.
- `README.md`: This file.

Configuration is read from `.env`. Persian text is normalized the same way at SVM train and inference time. TypeSafe is given both the original message and the normalized form, plus an English group policy.

#### Prerequisites / الزامات
- Python 3.10 or higher (`typesafe-sdk` requirement).
- Telegram Bot Token (from @BotFather).
- **Either** a TypeSafe API key from [the TypeSafe dashboard](https://console.typesafe.ai) **or** a `data.csv` training set (or both).
- A `.env` file (copy from `.env.example`) with `AUTH_TOKEN`, `LOGS_CHANNEL_ID`, and `ADMINS_GROUP_ID`.
- Bot must be an admin in target groups with delete-message permissions.

### فارسی
**ربات تشخیص اسپم تلگرام** پیام‌های اسپم را در گروه‌های تلگرام علامت می‌گذارد. دو روش برای اجرا هست:

1. **TypeSafe (بدون آموزش)** — فقط `TYPESAFE_API_KEY` را بگذارید و ربات را اجرا کنید. مدل Jev قضاوت ساخت‌یافته برمی‌گرداند و ربات در کد تصمیم می‌گیرد.
2. **SVM خودتان** — با `/detect` برچسب بزنید، با `/send_data` خروجی بگیرید، با `python train/train.py` آموزش دهید. برای اصطلاحات خاص گروه مفید است.

اگر هر دو پیکربندی شده باشند، حالت **hybrid** هر دو را با هم استفاده می‌کند.

پیام‌های مشکوک همچنان برای ادمین می‌روند؛ ربات بدون کلیک ادمین پیام را حذف نمی‌کند.

#### ویژگی‌های کلیدی
- **مسیر بدون آموزش TypeSafe**: با کلید API فوراً اجرا می‌شود.
- **SVM محلی اختیاری**: TF-IDF + SVM خطی روی CSV شما.
- **حالت ترکیبی**: قضاوت TypeSafe به‌علاوه مدل محلی.
- **علامت‌گذاری مبتنی بر اطمینان**: Choice/Score با اطمینان پایین به‌تنهایی عمل نمی‌کنند.
- **ابزارهای ادمین**: `/check`، `/detect`، `/send_data`، `/status`.
- **ثبت لاگ**: `bot.log` و کانال لاگ.
- **پشتیبانی فارسی**: متن‌های کاربر فارسی است. دقت Jev روی انگلیسی بهتر است؛ SVM محلی برای اصطلاحات فارسی کمک می‌کند.

#### ساختار پروژه
- `core/bot.py`: هندلرهای تلگرام.
- `core/classifier.py`: بک‌اندهای SVM، TypeSafe و hybrid.
- `core/typesafe_moderation.py`: سوال‌ها و سیاست مسیریابی TypeSafe.
- `train/train.py`: آموزش SVM از `data.csv`.
- `preprocessing.py`: نرمال‌سازی متن فارسی برای SVM.
- `requirements.txt`: وابستگی‌ها شامل `typesafe-sdk`.
- `.env.example`: قالب پیکربندی.
- `spam_messages.csv`: برچسب‌های `/detect`.
- `model.pkl` و `vectorizer.pkl`: خروجی آموزش SVM.
- `README.md`: این فایل.

#### الزامات
- پایتون 3.10 یا بالاتر.
- توکن ربات تلگرام (از @BotFather).
- **یا** کلید TypeSafe **یا** فایل `data.csv` (یا هر دو).
- فایل `.env` با `AUTH_TOKEN`، `LOGS_CHANNEL_ID` و `ADMINS_GROUP_ID`.
- ربات باید ادمین گروه با مجوز حذف پیام باشد.

## Installation / نصب

### English
1. **Clone the Repository**:
   ```
   git clone https://github.com/your-repo/Spam-detector-telegram-bot.git
   cd Spam-detector-telegram-bot
   ```

2. **Install Dependencies**:
   ```
   pip install -r requirements.txt
   ```

3. **Configure**: Copy `.env.example` to `.env` and fill in your values:
   ```
   cp .env.example .env
   # required: AUTH_TOKEN, LOGS_CHANNEL_ID, ADMINS_GROUP_ID
   # to run without training: TYPESAFE_API_KEY
   # optional: CLASSIFIER_BACKEND, SPAM_THRESHOLD, TYPESAFE_CONFIDENCE_FLOOR, AD_LINK, GROUP_USERNAME
   ```

4. **Choose a classifier**:
   - **No training:** set `TYPESAFE_API_KEY`. Leave `CLASSIFIER_BACKEND=auto` (or `typesafe`).
   - **Local SVM:** put `data.csv` in the repo root (`message`, `label` columns; labels `spam` / `normal`) and run:
     ```
     python train/train.py
     ```
     Prints accuracy plus precision/recall/F1; retrain with more data if accuracy is below 90%.
   - **Both:** set the API key *and* train. `auto` then selects hybrid.

5. **Run the Bot** (from the repo root):
   ```
   python core/bot.py
   ```

Add the bot to your group as an admin with delete permissions.

### فارسی
1. **کلون کردن مخزن**:
   ```
   git clone https://github.com/your-repo/Spam-detector-telegram-bot.git
   cd Spam-detector-telegram-bot
   ```

2. **نصب وابستگی‌ها**:
   ```
   pip install -r requirements.txt
   ```

3. **پیکربندی**: `.env.example` را به `.env` کپی کنید و مقادیر را پر کنید (حداقل `AUTH_TOKEN`، `LOGS_CHANNEL_ID`، `ADMINS_GROUP_ID`). برای اجرا بدون آموزش `TYPESAFE_API_KEY` را هم بگذارید.

4. **انتخاب طبقه‌بند**:
   - بدون آموزش: `TYPESAFE_API_KEY`
   - SVM محلی: `data.csv` و `python train/train.py`
   - هر دو: hybrid

5. **اجرای ربات** (از ریشهٔ مخزن):
   ```
   python core/bot.py
   ```

ربات را به گروه به‌عنوان ادمین با مجوز حذف اضافه کنید.

## Usage / استفاده

### English
- **Add to Group**: Invite the bot, make it an admin with delete rights.
- **Commands** (admin-only):
  - `/detect`: Reply to a message, choose spam/normal; saves to CSV for optional SVM retraining.
  - `/send_data`: Sends `spam_messages.csv`.
  - `/check`: Reply to a message; shows spam probability, backend, and TypeSafe reasons when available.
  - `/status`: Shows the live classifier backend and thresholds.
- **Automatic Detection**: Scans all text messages. If the active backend decides `should_flag`, the user is warned and the admins group gets review buttons (delete or 👍). Admin alerts include TypeSafe hazard labels when that backend fired.
- **Retraining the SVM**: `spam_messages.csv` uses a `message,label` header, same as `data.csv`. Rename/append it and rerun `python train/train.py`. This does **not** retrain TypeSafe; edit `core/typesafe_moderation.py` to change Jev’s questions and cutoffs.
- **Backends**: `CLASSIFIER_BACKEND=auto|typesafe|svm|hybrid`. TypeSafe calls fail open (do not freeze the group); hybrid then uses the SVM.

Monitor `bot.log` for errors. Get a TypeSafe key at [console.typesafe.ai](https://console.typesafe.ai).

### فارسی
- **اضافه کردن به گروه**: ربات را دعوت کنید و ادمین با حق حذف کنید.
- **دستورات** (فقط ادمین):
  - `/detect`: برچسب اسپم/عادی برای آموزش SVM.
  - `/send_data`: ارسال CSV.
  - `/check`: احتمال اسپم و دلایل TypeSafe.
  - `/status`: بک‌اند فعال و آستانه‌ها.
- **تشخیص خودکار**: اگر طبقه‌بند `should_flag` بدهد، هشدار به کاربر و اطلاع به ادمین‌ها.
- **بازآموزش SVM**: `spam_messages.csv` همان قالب `data.csv` را دارد. TypeSafe با CSV بازآموزش نمی‌شود؛ سوال‌ها در `core/typesafe_moderation.py` هستند.

## Contributing / مشارکت

### English
Contributions welcome! Fork, branch, commit, push, PR. Report issues on GitHub.

### فارسی
مشارکت خوش آمدید! فورک، شاخه، کامیت، پوش، PR. مشکلات را در GitHub گزارش دهید.

## License / مجوز
MIT License - see [LICENSE](LICENSE) for details.
