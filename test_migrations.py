import unittest

from sqlalchemy import inspect, text

from app import create_app
from app.extensions import db
from app.models import Submission


class InsightMigrationTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite://",
            }
        )
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.app_context.pop()

    def test_init_db_adds_insight_columns_to_existing_database(self):
        with db.engine.begin() as connection:
            connection.exec_driver_sql(
                """
                CREATE TABLE submissions (
                    id INTEGER PRIMARY KEY,
                    tracking_code VARCHAR(32) NOT NULL UNIQUE,
                    category VARCHAR(20) NOT NULL,
                    description TEXT NOT NULL,
                    location VARCHAR(200) NOT NULL,
                    is_anonymous BOOLEAN NOT NULL DEFAULT 0,
                    photo_filename VARCHAR(255),
                    status VARCHAR(20) NOT NULL DEFAULT 'Received',
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    resolved_at DATETIME
                )
                """
            )
            connection.execute(
                text(
                    """
                    INSERT INTO submissions (
                        tracking_code, category, description, location,
                        created_at, updated_at
                    ) VALUES (
                        'DGB-LEGACY', 'roads', 'Old report', 'Ward 1',
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                    """
                )
            )

        result = self.app.test_cli_runner().invoke(args=["init-db"])
        self.assertEqual(result.exit_code, 0, result.output)

        columns = {
            column["name"]
            for column in inspect(db.engine).get_columns("submissions")
        }
        self.assertIn("suggested_category", columns)
        self.assertIn("priority", columns)

        existing_submission = db.session.get(Submission, 1)
        self.assertEqual(existing_submission.tracking_code, "DGB-LEGACY")
        self.assertIsNone(existing_submission.suggested_category)
        self.assertEqual(existing_submission.priority, "normal")


if __name__ == "__main__":
    unittest.main()
