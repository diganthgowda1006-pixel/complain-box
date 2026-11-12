import unittest

from sqlalchemy.exc import IntegrityError

from app import create_app
from app.extensions import db
from app.models import StaffUser, StatusUpdate, Submission


class SubmissionModelTests(unittest.TestCase):
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

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        db.engine.dispose()
        self.app_context.pop()

    def test_submission_defaults_and_status_history(self):
        staff_user = StaffUser(
            username="office-admin",
            password_hash="test-hash",
            role="admin",
        )
        submission = Submission(
            tracking_code="TEST-123",
            category="roads",
            description="A pothole needs repair.",
            location="Ward 2",
        )
        update = StatusUpdate(
            status="Received",
            remarks="Report received.",
            staff_user=staff_user,
        )
        submission.status_updates.append(update)

        db.session.add(submission)
        db.session.commit()

        self.assertEqual(submission.status, "Received")
        self.assertFalse(submission.is_anonymous)
        self.assertEqual(submission.status_updates[0].staff_user.username, "office-admin")
        self.assertIsNotNone(submission.created_at)

    def test_database_rejects_unknown_category(self):
        submission = Submission(
            tracking_code="TEST-456",
            category="unknown",
            description="Invalid category.",
            location="Ward 1",
        )
        db.session.add(submission)

        with self.assertRaises(IntegrityError):
            db.session.commit()

        db.session.rollback()


if __name__ == "__main__":
    unittest.main()
