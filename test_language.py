import re
import unittest

from app import create_app
from app.extensions import db


class LanguageSwitchTests(unittest.TestCase):
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

    def _csrf_token(self):
        response = self.client.get("/")
        match = re.search(
            rb'name="csrf_token" type="hidden" value="([^"]+)"',
            response.data,
        )
        self.assertIsNotNone(match)
        return match.group(1).decode()

    def test_kannada_switch_translates_submission_page(self):
        response = self.client.post(
            "/language",
            data={"csrf_token": self._csrf_token(), "language": "kn"},
            headers={"Referer": "http://localhost/"},
        )

        self.assertEqual(response.status_code, 302)
        page = self.client.get("/")
        self.assertIn("ಡಿಜಿಟಲ್ ಸಲಹೆ ಪೆಟ್ಟಿಗೆ".encode(), page.data)
        self.assertIn("ಸಲಹೆ ಅಥವಾ ದೂರನ್ನು ಸಲ್ಲಿಸಿ".encode(), page.data)
        self.assertIn("ವಿದ್ಯುತ್".encode(), page.data)
        self.assertIn(b'<html lang="kn">', page.data)

    def test_language_selection_persists_on_tracking_page(self):
        self.client.post(
            "/language",
            data={"csrf_token": self._csrf_token(), "language": "kn"},
        )

        response = self.client.get("/track")

        self.assertIn("ಟ್ರ್ಯಾಕಿಂಗ್ ಐಡಿ".encode(), response.data)
        self.assertIn(b'<html lang="kn">', response.data)

    def test_unsupported_language_does_not_change_session(self):
        response = self.client.post(
            "/language",
            data={"csrf_token": self._csrf_token(), "language": "xx"},
        )

        self.assertEqual(response.status_code, 302)
        page = self.client.get("/")
        self.assertIn(b'<html lang="en">', page.data)

    def test_language_form_requires_csrf_token(self):
        response = self.client.post("/language", data={"language": "kn"})

        self.assertEqual(response.status_code, 400)
        self.assertIn(b'<html lang="en">', self.client.get("/").data)


if __name__ == "__main__":
    unittest.main()
