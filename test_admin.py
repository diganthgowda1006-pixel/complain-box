import unittest

from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash

from app import create_app
from app.extensions import db, limiter
from app.models import StaffUser, StatusUpdate, Submission


class AdminPanelTests(unittest.TestCase):
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
        limiter.reset()
        self.client = self.app.test_client()
        self.staff_user = StaffUser(
            username="office",
            password_hash=generate_password_hash("test-password-123"),
            role="staff",
        )
        self.submission = Submission(
            tracking_code="DGB-ADMIN123",
            category="roads",
            description="Repair a pothole.",
            location="Ward 5",
        )
        db.session.add_all([self.staff_user, self.submission])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.app_context.pop()

    def _csrf_token(self, path="/admin/login"):
        response = self.client.get(path)
        marker = b'name="csrf_token" type="hidden" value="'
        start = response.data.index(marker) + len(marker)
        end = response.data.index(b'"', start)
        return response.data[start:end].decode()

    def _login(self):
        return self.client.post(
            "/admin/login",
            data={
                "csrf_token": self._csrf_token(),
                "username": "office",
                "password": "test-password-123",
            },
            follow_redirects=True,
        )

    def test_staff_list_redirects_to_login_when_signed_out(self):
        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login", response.headers["Location"])

    def test_login_rejects_wrong_password(self):
        response = self.client.post(
            "/admin/login",
            data={
                "csrf_token": self._csrf_token(),
                "username": "office",
                "password": "wrong-password",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Username or password is incorrect.", response.data)
        self.assertIn("/admin/login", self.client.get("/admin/").headers["Location"])

    def test_login_attempts_are_rate_limited(self):
        csrf_token = self._csrf_token()
        response = None
        for _ in range(6):
            response = self.client.post(
                "/admin/login",
                data={
                    "csrf_token": csrf_token,
                    "username": "office",
                    "password": "wrong-password",
                },
            )

        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 429)

    def test_login_and_submission_filters(self):
        response = self._login()

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"DGB-ADMIN123", response.data)

        filtered = self.client.get("/admin/?status=Resolved")
        self.assertEqual(filtered.status_code, 200)
        self.assertIn(b"No suggestions match these filters.", filtered.data)

        found = self.client.get("/admin/?q=Ward%205&category=roads")
        self.assertIn(b"DGB-ADMIN123", found.data)

    def test_staff_can_update_status_and_public_remarks(self):
        self._login()
        response = self.client.post(
            f"/admin/submissions/{self.submission.id}",
            data={
                "csrf_token": self._csrf_token(
                    f"/admin/submissions/{self.submission.id}"
                ),
                "status": "Resolved",
                "remarks": "The pothole was repaired.",
                "is_public": "y",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        db.session.refresh(self.submission)
        self.assertEqual(self.submission.status, "Resolved")
        self.assertIsNotNone(self.submission.resolved_at)
        update = StatusUpdate.query.one()
        self.assertEqual(update.staff_user_id, self.staff_user.id)
        self.assertTrue(update.is_public)
        self.assertEqual(update.remarks, "The pothole was repaired.")

    def test_logout_clears_staff_session(self):
        self._login()
        response = self.client.post(
            "/admin/logout",
            data={"csrf_token": self._csrf_token("/")},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"sign in", response.data.lower())
        self.assertEqual(self.client.get("/admin/").status_code, 302)

    def test_create_staff_command_hashes_password(self):
        result = self.app.test_cli_runner().invoke(
            args=[
                "create-staff",
                "--username",
                "new-officer",
                "--role",
                "admin",
            ],
            input="new-officer-password\nnew-officer-password\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        new_user = StaffUser.query.filter_by(username="new-officer").one()
        self.assertEqual(new_user.role, "admin")
        self.assertTrue(
            check_password_hash(new_user.password_hash, "new-officer-password")
        )

    def test_change_staff_password_command_replaces_hash(self):
        result = self.app.test_cli_runner().invoke(
            args=["change-staff-password", "--username", "office"],
            input="brand-new-password\nbrand-new-password\n",
        )

        self.assertEqual(result.exit_code, 0, result.output)
        db.session.refresh(self.staff_user)
        self.assertTrue(
            check_password_hash(self.staff_user.password_hash, "brand-new-password")
        )
        self.assertFalse(
            check_password_hash(self.staff_user.password_hash, "test-password-123")
        )

    def test_change_password_rejects_short_new_password(self):
        result = self.app.test_cli_runner().invoke(
            args=["change-staff-password", "--username", "office"],
            input="short\nshort\n",
        )

        self.assertNotEqual(result.exit_code, 0)
        db.session.refresh(self.staff_user)
        self.assertTrue(
            check_password_hash(self.staff_user.password_hash, "test-password-123")
        )


if __name__ == "__main__":
    unittest.main()
