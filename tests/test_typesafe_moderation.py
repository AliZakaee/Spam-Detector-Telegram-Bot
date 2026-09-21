import unittest
from types import SimpleNamespace

from core.typesafe_moderation import (
    HAZARD_KEYS,
    SPAM_QUESTIONS,
    build_moderation_state,
    route_typesafe_answers,
)


def _answers(**overrides):
    data = {
        "verdict": SimpleNamespace(
            choice="normal",
            confidence=1.0,
            probabilities={"spam": 0.05, "normal": 0.95},
        ),
        "unsolicited_ad": SimpleNamespace(noul=0.02),
        "scam_or_phishing": SimpleNamespace(noul=0.01),
        "mass_promo_or_invite": SimpleNamespace(noul=0.01),
        "suspicious_link_or_impersonation": SimpleNamespace(noul=0.01),
        "severity": SimpleNamespace(score=0.1, confidence=1.0),
    }
    data.update(overrides)
    return data


class SpamQuestionsTests(unittest.TestCase):
    def test_battery_covers_choice_hazards_and_severity(self):
        self.assertEqual(SPAM_QUESTIONS["verdict"].type, "choice")
        self.assertEqual(set(SPAM_QUESTIONS["verdict"].criteria), {"spam", "normal"})
        for key in HAZARD_KEYS:
            self.assertEqual(SPAM_QUESTIONS[key].type, "noul")
        self.assertEqual(SPAM_QUESTIONS["severity"].type, "score")
        self.assertEqual(len(SPAM_QUESTIONS["severity"].criteria), 4)

    def test_state_keeps_original_text_and_policy_fields(self):
        state = build_moderation_state("فروش ویژه پیوی")
        self.assertEqual(state["message_text"], "فروش ویژه پیوی")
        self.assertIn("normalized_text", state)
        self.assertIn("community_policy", state)
        self.assertTrue(state["local_spam_cues"])


class RouteTypeSafeAnswersTests(unittest.TestCase):
    def test_ordinary_chat_is_not_flagged(self):
        routed = route_typesafe_answers(_answers(), spam_threshold=0.4, confidence_floor=0.5)

        self.assertEqual(routed["label"], "normal")
        self.assertFalse(routed["should_flag"])
        self.assertEqual(routed["reasons"], ())

    def test_confident_spam_choice_is_flagged(self):
        routed = route_typesafe_answers(
            _answers(
                verdict=SimpleNamespace(
                    choice="spam",
                    confidence=0.9,
                    probabilities={"spam": 0.88, "normal": 0.12},
                )
            ),
            spam_threshold=0.4,
            confidence_floor=0.5,
        )

        self.assertEqual(routed["label"], "spam")
        self.assertTrue(routed["should_flag"])
        self.assertAlmostEqual(routed["spam_confidence"], 0.88)

    def test_low_confidence_spam_choice_is_not_flagged(self):
        routed = route_typesafe_answers(
            _answers(
                verdict=SimpleNamespace(
                    choice="spam",
                    confidence=0.2,
                    probabilities={"spam": 0.7, "normal": 0.3},
                )
            ),
            spam_threshold=0.4,
            confidence_floor=0.5,
        )

        self.assertEqual(routed["label"], "spam")
        self.assertFalse(routed["should_flag"])

    def test_hazard_can_flag_even_when_choice_says_normal(self):
        routed = route_typesafe_answers(
            _answers(scam_or_phishing=SimpleNamespace(noul=0.91)),
            spam_threshold=0.4,
            confidence_floor=0.5,
        )

        self.assertTrue(routed["should_flag"])
        self.assertEqual(routed["label"], "spam")
        self.assertIn("کلاهبرداری یا فیشینگ", routed["reasons"])

    def test_clear_severity_with_confidence_flags(self):
        routed = route_typesafe_answers(
            _answers(severity=SimpleNamespace(score=2.4, confidence=0.8)),
            spam_threshold=0.4,
            confidence_floor=0.5,
        )

        self.assertTrue(routed["should_flag"])
        self.assertEqual(routed["label"], "spam")

    def test_clear_severity_without_confidence_does_not_flag_alone(self):
        routed = route_typesafe_answers(
            _answers(severity=SimpleNamespace(score=2.4, confidence=0.1)),
            spam_threshold=0.4,
            confidence_floor=0.5,
        )

        self.assertFalse(routed["should_flag"])
        self.assertEqual(routed["label"], "normal")


if __name__ == "__main__":
    unittest.main()
