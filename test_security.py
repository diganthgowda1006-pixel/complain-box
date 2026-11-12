import re
import tempfile
import unittest

from app import create_app
from app.extensions import db


class ProductionSecurityTests(unittest.TestCase):
    def test_production_requires_secret_key(self):
        with self.assertRaisesRegex(RuntimeError, "Set SECRET_KEY"):
            create_app(
                {
                    "APP_ENV": "production",
                    "SECRET_KEY": None,
                    "SQLALCHEMY_DATABASE_URI": "sqlite://",
                }
            )

    def test_production_cookie_is_secure_and_http_only(self):
        with tempfile.TemporaryDirectory() as upload_directory:
            app = create_app(
                {
                    "TESTING": True,
                    "APP_ENV": "production",
                    "SECRET_KEY": "test-production-secret",
                    "SQLALCHEMY_DATABASE_URI": "sqlite://",
                    "UPLOAD_FOLDER": upload_directory,
                }
            )
            app_context = app.app_context()
            app_context.push()
            db.create_all()
            client = app.test_client()
            response = client.get("/", base_url="https://localhost")
            token_match = re.search(
                rb'name="csrf_token" type="hidden" value="([^"]+)"',
                response.data,
            )
            self.assertIsNotNone(token_match)
            cookie = response.headers.get("Set-Cookie", "").lower()
            self.assertIn("secure", cookie)
            self.assertIn("httponly", cookie)
            self.assertIn("samesite=lax", cookie)

            client.post(
                "/language",
                base_url="https://localhost",
                data={
                    "csrf_token": token_match.group(1).decode(),
                    "language": "kn",
                },
            )

            db.session.remove()
            db.drop_all()
            db.engine.dispose()
            app_context.pop()


if __name__ == "__main__":
    unittest.main()
