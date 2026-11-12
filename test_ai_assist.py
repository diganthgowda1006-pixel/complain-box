import unittest
from types import SimpleNamespace

from app.services.ai_assist import (
    detect_priority,
    find_similar_submissions,
    suggest_category,
    weekly_issue_summary,
)


class LocalAssistTests(unittest.TestCase):
    def test_suggest_category_from_english_or_kannada_keywords(self):
        self.assertEqual(
            suggest_category("There is a large pothole on our road."),
            "roads",
        )
        self.assertEqual(
            suggest_category("ನಮ್ಮ ರಸ್ತೆಯಲ್ಲಿ ದೊಡ್ಡ ಗುಂಡಿ ಇದೆ"),
            "roads",
        )
        self.assertEqual(
            suggest_category("The street light has no electricity."),
            "electricity",
        )

    def test_unclear_or_equal_category_keywords_produce_no_suggestion(self):
        self.assertIsNone(suggest_category("Please improve our area."))
        self.assertIsNone(suggest_category("The road drain is blocked."))

    def test_priority_flags_only_known_urgent_terms(self):
        self.assertEqual(detect_priority("There is an urgent power line danger."), "urgent")
        self.assertEqual(detect_priority("ವಿದ್ಯುತ್ ತಂತಿ ಅಪಾಯದಲ್ಲಿದೆ"), "urgent")
        self.assertEqual(detect_priority("Please repair the road."), "normal")

    def test_weekly_summary_uses_counts_not_free_text(self):
        reports = [
            SimpleNamespace(
                category="roads",
                location="Ward 1",
                priority="urgent",
                description="Private report text should not be copied.",
            ),
            SimpleNamespace(
                category="roads",
                location="Ward 1",
                priority="normal",
                description="Another private report.",
            ),
            SimpleNamespace(
                category="water",
                location="Ward 2",
                priority="normal",
                description="Private water report.",
            ),
        ]

        summary = weekly_issue_summary(reports)

        self.assertEqual(summary, {
            "total": 3,
            "top_category": "roads",
            "top_location": "Ward 1",
            "urgent_count": 1,
        })
        self.assertNotIn("description", summary)


if __name__ == "__main__":
    unittest.main()
