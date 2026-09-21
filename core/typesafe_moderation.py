"""TypeSafe (Jev) questions and routing for Telegram spam moderation.

Questions and numeric cutoffs live here on purpose: they are the policy the
model sees and the thresholds code applies. Edit this file when the group's
definition of spam changes; do not scatter copies across the bot.
"""

from typesafe_sdk import Choice, Noul, NoulCriteria, Score

from preprocessing import normalize_text


# Score level at which a message is "clear unsolicited spam" (see SEVERITY criteria).
SEVERITY_REVIEW = 2.0
MAX_SEVERITY = 3.0

HAZARD_KEYS = (
    "unsolicited_ad",
    "scam_or_phishing",
    "mass_promo_or_invite",
    "suspicious_link_or_impersonation",
)

HAZARD_LABELS_FA = {
    "unsolicited_ad": "تبلیغات ناخواسته",
    "scam_or_phishing": "کلاهبرداری یا فیشینگ",
    "mass_promo_or_invite": "پیام انبوه یا دعوت به کانال",
    "suspicious_link_or_impersonation": "لینک مشکوک یا جعل هویت",
}

COMMUNITY_POLICY = (
    "This is a Telegram group chat, often in Persian (Farsi). "
    "Spam includes unsolicited advertising, scams, phishing, crypto or investment schemes, "
    "VPN or account selling, lottery or prize bait, requests to message privately for ads, "
    "and mass invitations to other channels or bots. "
    "Ordinary conversation, questions, jokes, greetings, and on-topic discussion without "
    "selling or recruiting are not spam."
)

LOCAL_SPAM_CUES = [
    "Unsolicited 'پیوی' / DM-me sales pitches",
    "Join-my-channel or t.me invite used as an advertisement",
    "Crypto, forex, lottery, and fake giveaway bait",
    "VPN, proxy, and account selling",
    "Copy-pasted promo text with lots of links, @usernames, or emojis",
]


def _noul(instructions, yes, no):
    return Noul(
        instructions=instructions,
        criteria=NoulCriteria(true=yes, false=no),
    )


# Speculative fan-out: one request, every judgment the router might need.
SPAM_QUESTIONS = {
    "verdict": Choice(
        instructions=(
            "Given `community_policy` and `local_spam_cues`, is `message_text` spam "
            "that a group moderator should review? Use `normalized_text` if character "
            "variants or digits help, but judge the original `message_text`."
        ),
        criteria={
            "spam": (
                "Unsolicited advertising, a scam, phishing, a mass promo, a channel or bot "
                "invite blast, or commercial solicitation. Typical Telegram tells include "
                "فروش، تبلیغ، پیوی، کانال، رفرال and unsolicited t.me / @channel promotions."
            ),
            "normal": (
                "Ordinary group conversation, a question, a joke, a greeting, or on-topic "
                "discussion without selling or recruiting."
            ),
        },
    ),
    "unsolicited_ad": _noul(
        "Does `message_text` look like unsolicited advertising or a sales pitch, given `community_policy`?",
        yes="It promotes a product, service, channel, or bot to the group without being asked.",
        no="It is not an advertisement or sales pitch.",
    ),
    "scam_or_phishing": _noul(
        "Does `message_text` look like a scam, phishing attempt, fake giveaway, or social-engineering attack?",
        yes="It tries to trick someone into sending money, accounts, codes, or personal data.",
        no="It does not try to deceive or defraud anyone.",
    ),
    "mass_promo_or_invite": _noul(
        "Is `message_text` a copy-paste promotional blast or an unsolicited invite to another Telegram channel, group, or bot?",
        yes="It is mass promo or an unsolicited invite/redirect off this group.",
        no="It is not a blast or an unsolicited invite.",
    ),
    "suspicious_link_or_impersonation": _noul(
        "Does `message_text` use a suspicious link, obfuscated URL, or impersonation of a brand, admin, or official account?",
        yes="It uses a deceptive link or pretends to be someone or something it is not.",
        no="It does not impersonate anyone or hide a deceptive link.",
    ),
    "severity": Score(
        instructions=(
            "How harmful or disruptive would it be to leave `message_text` in this Telegram group, "
            "given `community_policy`?"
        ),
        criteria=[
            "Harmless ordinary chat; no promo or deception.",
            "Slightly promotional or off-topic, but not clearly spam a moderator must act on.",
            "Clear unsolicited spam or advertising that should be reviewed and likely removed.",
            "Scam, phishing, malware, or harmful deception that should be removed.",
        ],
    ),
}


def build_moderation_state(message_text):
    """Structured state: policy and cues are named fields, not hidden in the prompt."""
    return {
        "message_text": message_text,
        "normalized_text": normalize_text(message_text),
        "community_policy": COMMUNITY_POLICY,
        "local_spam_cues": LOCAL_SPAM_CUES,
    }


def route_typesafe_answers(answers, spam_threshold, confidence_floor):
    """Turn one TypeSafe response into a label, probability, and flag decision.

    Code owns the policy:
    - Choice says what the message is; its confidence says whether to trust that pick.
    - Each Noul is an independent hazard. Any one over the spam threshold can flag.
    - Score >= SEVERITY_REVIEW is "clear spam" on the written rubric, gated on confidence.
    """
    verdict = answers["verdict"]
    probabilities = dict(getattr(verdict, "probabilities", None) or {})
    spam_probability = float(probabilities.get("spam", 0.0))
    choice_confidence = float(getattr(verdict, "confidence", 0.0) or 0.0)
    choice = getattr(verdict, "choice", "normal")

    hazards = {key: float(getattr(answers[key], "noul", 0.0) or 0.0) for key in HAZARD_KEYS}
    severity_answer = answers["severity"]
    severity = float(getattr(severity_answer, "score", 0.0) or 0.0)
    severity_confidence = float(getattr(severity_answer, "confidence", 0.0) or 0.0)

    reasons = tuple(
        HAZARD_LABELS_FA[key]
        for key, probability in hazards.items()
        if probability > spam_threshold
    )

    choice_spam = (
        choice == "spam"
        and spam_probability > spam_threshold
        and choice_confidence >= confidence_floor
    )
    hazard_spam = any(probability > spam_threshold for probability in hazards.values())
    severity_spam = severity >= SEVERITY_REVIEW and severity_confidence >= confidence_floor

    should_flag = choice_spam or hazard_spam or severity_spam
    max_hazard = max(hazards.values()) if hazards else 0.0
    spam_confidence = max(spam_probability, max_hazard, severity / MAX_SEVERITY)
    label = "spam" if (choice == "spam" or should_flag) else "normal"

    return {
        "label": label,
        "spam_confidence": spam_confidence,
        "should_flag": should_flag,
        "reasons": reasons,
        "choice_confidence": choice_confidence,
        "hazards": hazards,
        "severity": severity,
    }
