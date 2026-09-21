"""Persian/English copy for classification results shown in Telegram."""

SOURCE_LABELS = {
    "typesafe": "TypeSafe (Jev)",
    "svm": "مدل محلی SVM",
    "hybrid": "ترکیبی TypeSafe + SVM",
}


def format_check_reply(result):
    """Admin /check body. Keeps the original probability sentence, then adds TypeSafe detail."""
    source = SOURCE_LABELS.get(result.source, result.source)
    lines = []
    if result.error:
        lines.append(f"هشدار: طبقه‌بند با خطا مواجه شد (`{result.error}`).")

    if result.label == "spam":
        lines.append(
            f"پیام مورد نظر با احتمال *{result.spam_confidence * 100:.2f}%* اسپم شناسایی شده است."
        )
    else:
        lines.append("پیام مورد نظر اسپم شناسایی نشد.")
        if result.spam_confidence:
            lines.append(f"احتمال اسپم: *{result.spam_confidence * 100:.2f}%*")

    lines.append(f"منبع: {source}")
    if result.reasons:
        lines.append("دلایل: " + "، ".join(result.reasons))
    if result.choice_confidence is not None:
        lines.append(f"اطمینان انتخاب: *{result.choice_confidence * 100:.2f}%*")
    if result.severity is not None:
        lines.append(f"شدت: *{result.severity:.2f}* از ۳")
    if result.label == "spam":
        if result.should_flag:
            lines.append("این پیام در آستانهٔ علامت‌گذاری خودکار است.")
        else:
            lines.append("این پیام به آستانهٔ علامت‌گذاری خودکار نرسیده است.")
    return "\n".join(lines)


def format_admin_alert(result, username):
    source = SOURCE_LABELS.get(result.source, result.source)
    lines = [
        (
            f"یک پیام احتمالی اسپم با احتمال {result.spam_confidence * 100:.2f}% "
            f"از {username} شناسایی شده است و نیازمند تایید شماست."
        ),
        f"منبع: {source}",
    ]
    if result.reasons:
        lines.append("دلایل: " + "، ".join(result.reasons))
    return "\n".join(lines)


def format_status(classifier, spam_threshold, confidence_floor, normalization_backend):
    return "\n".join(
        [
            f"Classifier backend: `{classifier.name}`",
            classifier.describe(),
            f"Spam threshold: `{spam_threshold}`",
            f"TypeSafe confidence floor: `{confidence_floor}`",
            f"Normalization: `{normalization_backend}`",
        ]
    )
