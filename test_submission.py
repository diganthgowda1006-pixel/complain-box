import re
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from PIL import Image

from app import create_app
from app.extensions import db, limiter
from app.models import Submission


class SubmissionFormTests(unittest.TestCase):
    def setUp(self):
        self.upload_directory = tempfile.TemporaryDirectory()
        self.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite://",
                "UPLOAD_FOLDER": self.upload_directory.name,
            }
        )
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()
        limiter.reset()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.app_context.pop()
        self.upload_directory.cleanup()

    def _csrf_token(self):
        response = self.client.get("/")
        match = re.search(
            rb'name="csrf_token" type="hidden" value="([^"]+)"',
            response.data,
        )
        self.assertIsNotNone(match)
        return match.group(1).decode()

    def test_submit_suggestion_shows_tracking_code(self):
        response = self.client.post(
            "/",
            data={
                "csrf_token": self._csrf_token(),
                "category": "roads",
                "description": "There is a pothole.",
                "location": "Ward 2",
                "is_anonymous": "y",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        submission = db.session.query(Submission).one()
        self.assertTrue(submission.tracking_code.startswith("DGB-"))
        self.assertIn(submission.tracking_code.encode(), response.data)
        self.assertTrue(submission.is_anonymous)
        self.assertEqual(submission.status_updates[0].status, "Received")

    def test_valid_photo_is_saved_with_generated_filename(self):
        image_buffer = BytesIO()
        Image.new("RGB", (4, 4), color="blue").save(image_buffer, format="PNG")
        image_buffer.seek(0)
        response = self.client.post(
            "/",
            data={
                "csrf_token": self._csrf_token(),
                "category": "water",
                "description": "A water pipe is leaking.",
                "location": "Ward 3",
                "photo": (image_buffer, "my-photo.png"),
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        submission = db.session.query(Submission).one()
        self.assertIsNotNone(submission.photo_filename)
        self.assertNotEqual(submission.photo_filename, "my-photo.png")
        self.assertTrue(Path(self.upload_directory.name, submission.photo_filename).is_file())

    def test_malformed_image_with_valid_extension_is_rejected(self):
        response = self.client.post(
            "/",
            data={
                "csrf_token": self._csrf_token(),
                "category": "water",
                "description": "There is a leak.",
                "location": "Ward 3",
                "photo": (BytesIO(b"\x89PNG\r\n\x1a\nnot a real png"), "fake.png"),
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn(b"20 megapixels", response.data)
        self.assertEqual(db.session.query(Submission).count(), 0)

    def test_invalid_photo_is_rejected(self):
        response = self.client.post(
            "/",
            data={
                "csrf_token": self._csrf_token(),
                "category": "water",
                "description": "There is a leak.",
                "location": "Ward 3",
                "photo": (BytesIO(b"not an image"), "photo.jpg"),
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Photo must be a valid JPEG", response.data)
        self.assertEqual(db.session.query(Submission).count(), 0)

    def test_whitespace_only_description_is_rejected(self):
        response = self.client.post(
            "/",
            data={
                "csrf_token": self._csrf_token(),
                "category": "roads",
                "description": "   ",
                "location": "Ward 2",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Please describe the issue.", response.data)
        self.assertEqual(db.session.query(Submission).count(), 0)

    def test_submission_requires_csrf_token(self):
        response = self.client.post(
            "/",
            data={
                "category": "roads",
                "description": "There is a pothole.",
                "location": "Ward 2",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(db.session.query(Submission).count(), 0)

    def test_submission_rate_limit_returns_429(self):
        csrf_token = self._csrf_token()
        response = None
        for index in range(6):
            response = self.client.post(
                "/",
                data={
                    "csrf_token": csrf_token,
                    "category": "roads",
                    "description": f"Report number {index}.",
                    "location": "Ward 2",
                },
            )

        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 429)
        self.assertIn(b"Too many attempts", response.data)

    def test_oversized_request_returns_413(self):
        response = self.client.post(
            "/",
            data=b"x" * (5 * 1024 * 1024 + 1),
            content_type="application/octet-stream",
        )

        self.assertEqual(response.status_code, 413)
        self.assertIn(b"request is too large", response.data)


if __name__ == "__main__":
    unittest.main()
