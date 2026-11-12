from pathlib import Path
import secrets

import click
from flask import Flask, render_template
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import generate_password_hash

from config import Config
from app.extensions import csrf, db, limiter
from app.i18n import current_language, translate
from app.models import STAFF_ROLES, StaffUser


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    if test_config is not None:
        app.config.update(test_config)

    if app.config.get("APP_ENV") == "production":
        app.config["SESSION_COOKIE_SECURE"] = True

    if not app.config.get("SECRET_KEY"):
        if app.config.get("APP_ENV") == "production":
            raise RuntimeError(
                "Set SECRET_KEY in the production environment before starting the app."
            )
        if app.testing:
            app.config["SECRET_KEY"] = "test-only-secret-key"
        else:
            app.config["SECRET_KEY"] = secrets.token_hex(32)
            app.logger.warning(
                "SECRET_KEY is not set; a temporary key is being used. "
                "Set SECRET_KEY in .env to keep sessions valid across restarts."
            )

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    @app.cli.command("init-db")
    def init_db_command():
        from app import models

        db.create_all()
        _migrate_submission_insights()
        click.echo("Database tables created.")

    @app.cli.command("create-staff")
    @click.option("--username", prompt=True)
    @click.option(
        "--role",
        type=click.Choice(STAFF_ROLES, case_sensitive=False),
        default="staff",
        show_default=True,
    )
    def create_staff_command(username, role):
        """Create a staff login without exposing its password in shell history."""
        username = username.strip()
        if not username or len(username) > 80:
            raise click.ClickException("Username must contain 1 to 80 characters.")

        if StaffUser.query.filter_by(username=username).first() is not None:
            raise click.ClickException("That username already exists.")

        password = click.prompt("Password", hide_input=True, confirmation_prompt=True)
        if len(password) < 12:
            raise click.ClickException("Password must be at least 12 characters.")

        staff_user = StaffUser(
            username=username,
            password_hash=generate_password_hash(password),
            role=role.lower(),
        )
        db.session.add(staff_user)
        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception("Could not create the staff account.")
            raise click.ClickException("Could not create the staff account.")
        click.echo(f"Staff account '{username}' created.")

    @app.cli.command("change-staff-password")
    @click.option("--username", prompt=True)
    def change_staff_password_command(username):
        """Set a staff password using a hidden interactive prompt."""
        username = username.strip()
        staff_user = StaffUser.query.filter_by(username=username).first()
        if staff_user is None:
            raise click.ClickException(f"No staff account exists for '{username}'.")

        password = click.prompt("New password", hide_input=True, confirmation_prompt=True)
        if len(password) < 12:
            raise click.ClickException("Password must be at least 12 characters.")

        staff_user.password_hash = generate_password_hash(password)
        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception("Could not change the staff password.")
            raise click.ClickException("Could not change the staff password.")
        click.echo(f"Password changed for '{username}'. Sign in again with the new password.")

    from app.routes.public import public
    from app.routes.admin import admin

    app.register_blueprint(public)
    app.register_blueprint(admin, url_prefix="/admin")

    @app.context_processor
    def add_language_helpers():
        return {
            "t": translate,
            "current_language": current_language,
        }

    @app.errorhandler(413)
    def request_too_large(_error):
        return (
            render_template(
                "error.html",
                message=translate(
                    "The request is too large. Photos must be smaller than 5 MB."
                ),
            ),
            413,
        )

    @app.errorhandler(429)
    def too_many_requests(_error):
        return (
            render_template(
                "error.html",
                message=translate(
                    "Too many attempts. Please wait a minute and try again."
                ),
            ),
            429,
        )

    return app


def _migrate_submission_insights():
    if db.engine.dialect.name != "sqlite":
        return

    existing_columns = {
        column["name"]
        for column in inspect(db.engine).get_columns("submissions")
    }
    with db.engine.begin() as connection:
        if "suggested_category" not in existing_columns:
            connection.exec_driver_sql(
                "ALTER TABLE submissions ADD COLUMN suggested_category VARCHAR(20)"
            )
        if "priority" not in existing_columns:
            connection.exec_driver_sql(
                "ALTER TABLE submissions ADD COLUMN priority VARCHAR(10) "
                "NOT NULL DEFAULT 'normal' CHECK (priority IN ('normal', 'urgent'))"
            )
