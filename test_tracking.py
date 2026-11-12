import unittest

from app import create_app
from app.extensions import db
from app.models import StatusUpdate, Submission


class TrackingPageTests(unittest.TestCase):
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

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.app_context.pop()

    def test_tracking_code_displays_current_status_and_public_history(self):
        submission = Submission(
            tracking_code="DGB-ABC123",
            category="roads",
            description="A pothole needs repair.",
            location="Ward 2",
            status="In Progress",
        )
        submission.status_updates.extend(
            [
                StatusUpdate(
                    status="Received",
                    remarks="Your suggestion has been received.",
                    is_public=True,
                ),
                StatusUpdate(
                    status="In Progress",
                    remarks="The repair team has been notified.",
                    is_public=True,
                ),
                StatusUpdate(
                    status="In Progress",
                    remarks="Internal staff note.",
                    is_public=False,
                ),
            ]
        )
        db.session.add(submission)
        db.session.commit()

        response = self.client.get("/track?tracking_code=%20dgb-abc123%20")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"In Progress", response.data)
        self.assertIn(b"Your suggestion has been received.", response.data)
        self.assertIn(b"The repair team has been notified.", response.data)
        self.assertNotIn(b"Internal staff note.", response.data)

    def test_unknown_tracking_code_shows_helpful_message(self):
        response = self.client.get("/track?tracking_code=DGB-MISSING")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Check the ID and try again.", response.data)

    def test_empty_tracking_page_shows_lookup_form(self):
        response = self.client.get("/track")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'name="tracking_code"', response.data)
        self.assertNotIn(b"Check the ID and try again.", response.data)

    def test_tracking_code_longer_than_column_limit_is_not_looked_up(self):
        response = self.client.get(f"/track?tracking_code={'A' * 33}")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Check the ID and try again.", response.data)


if __name__ == "__main__":
    unittest.main()
