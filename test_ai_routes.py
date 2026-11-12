import re
import unittest

from app import create_app
from app.extensions import db
from app.models import StaffUser, Submission
from app.services.ai_assist import find_similar_submissions
from werkzeug.security import generate_password_hash


class LocalAssistRouteTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite://",
            }
        )
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()
        db.session.add(
            StaffUser(
                username="insight-staff",
                password_hash=generate_password_hash("test-password-123"),
            )
        )
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.app_context.pop()

    def _csrf_token(self, path="/"):
        response = self.client.get(path)
        match = re.search(
            rb'name="csrf_token" type="hidden" value="([^"]+)"',
            response.data,
        )
        self.assertIsNotNone(match)
        return match.group(1).decode()

    def test_submission_saves_local_category_suggestion_and_priority(self):
        response = self.client.post(
            "/",
            data={
                "csrf_token": self._csrf_token(),
                "category": "other",
                "description": "Urgent: a large pothole is dangerous.",
                "location": "Ward 7",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        submission = Submission.query.one()
        self.assertEqual(submission.category, "other")
        self.assertEqual(submission.suggested_category, "roads")
        self.assertEqual(submission.priority, "urgent")
        self.assertIn(b"Our local helper suggests this category", response.data)

    def test_similar_submission_is_shown_to_staff(self):
        original = Submission(
            tracking_code="DGB-SIMILAR1",
            category="roads",
            description="A large pothole on the main road needs repair",
            location="Ward 1",
        )
        current = Submission(
            tracking_code="DGB-SIMILAR2",
            category="roads",
            description="Pothole on the main road needs repair soon",
            location="Ward 1",
        )
        db.session.add_all([original, current])
        db.session.commit()
        staff_user = StaffUser.query.filter_by(username="insight-staff").one()
        login_page = self.client.get("/admin/login")
        login_token = re.search(
            rb'name="csrf_token" type="hidden" value="([^"]+)"',
            login_page.data,
        ).group(1).decode()
        self.client.post(
            "/admin/login",
            data={
                "csrf_token": login_token,
                "username": staff_user.username,
                "password": "test-password-123",
            },
        )

        response = self.client.get(f"/admin/submissions/{current.id}")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Possibly similar suggestions", response.data)
        self.assertIn(b"DGB-SIMILAR1", response.data)

    def test_no_match_is_not_reported_as_duplicate(self):
        first = Submission(
            tracking_code="DGB-UNIQUE1",
            category="roads",
            description="Pothole beside the library",
            location="Ward 1",
        )
        second = Submission(
            tracking_code="DGB-UNIQUE2",
            category="water",
            description="The drinking water tap is broken",
            location="Ward 6",
        )
        db.session.add_all([first, second])
        db.session.commit()

        self.assertEqual(find_similar_submissions(second), [])


if __name__ == "__main__":
    unittest.main()
