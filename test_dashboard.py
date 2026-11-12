import unittest
from datetime import datetime, timedelta, timezone

from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import StaffUser, Submission


class DashboardTests(unittest.TestCase):
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
        staff_user = StaffUser(
            username="dashboard-staff",
            password_hash=generate_password_hash("test-password-123"),
            role="staff",
        )
        db.session.add(staff_user)
        db.session.commit()
        self._login()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.app_context.pop()

    def _login(self):
        response = self.client.get("/admin/login")
        token = response.data.split(b'name="csrf_token" type="hidden" value="')[1]
        token = token.split(b'"', 1)[0].decode()
        self.client.post(
            "/admin/login",
            data={
                "csrf_token": token,
                "username": "dashboard-staff",
                "password": "test-password-123",
            },
        )

    def test_dashboard_shows_category_status_trend_and_resolution_average(self):
        now = datetime.now(timezone.utc)
        db.session.add_all(
            [
                Submission(
                    tracking_code="DGB-DASH001",
                    category="roads",
                    description="Road repaired.",
                    location="Ward 1",
                    status="Resolved",
                    created_at=now - timedelta(hours=4),
                    updated_at=now,
                    resolved_at=now,
                ),
                Submission(
                    tracking_code="DGB-DASH002",
                    category="water",
                    description="Water issue.",
                    location="Ward 2",
                    status="In Progress",
                    created_at=now,
                    updated_at=now,
                ),
            ]
        )
        db.session.commit()

        response = self.client.get("/admin/dashboard")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Suggestions by category", response.data)
        self.assertIn(b"Received", response.data)
        self.assertIn(b"Average resolution time", response.data)
        self.assertIn(b"4.0 hours", response.data)
        self.assertIn(b"const categoryValues = [1, 1, 0, 0, 0]", response.data)

    def test_dashboard_shows_empty_resolution_message(self):
        response = self.client.get("/admin/dashboard")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No resolved suggestions yet", response.data)

    def test_dashboard_requires_staff_login(self):
        with self.client.session_transaction() as staff_session:
            staff_session.clear()

        response = self.client.get("/admin/dashboard")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login", response.headers["Location"])


if __name__ == "__main__":
    unittest.main()
