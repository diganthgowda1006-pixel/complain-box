from datetime import datetime, timezone

from sqlalchemy import CheckConstraint

from app.extensions import db


CATEGORIES = ("roads", "water", "electricity", "sanitation", "other")
STATUSES = ("Received", "In Progress", "Resolved")
STAFF_ROLES = ("admin", "staff")


def utc_now():
    return datetime.now(timezone.utc)


class Submission(db.Model):
    __tablename__ = "submissions"
    __table_args__ = (
        CheckConstraint(
            "category IN ('roads', 'water', 'electricity', 'sanitation', 'other')",
            name="valid_submission_category",
        ),
        CheckConstraint(
            "status IN ('Received', 'In Progress', 'Resolved')",
            name="valid_submission_status",
        ),
        CheckConstraint(
            "suggested_category IS NULL OR suggested_category IN "
            "('roads', 'water', 'electricity', 'sanitation', 'other')",
            name="valid_suggested_category",
        ),
        CheckConstraint(
            "priority IN ('normal', 'urgent')",
            name="valid_submission_priority",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    tracking_code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    category = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    suggested_category = db.Column(db.String(20), nullable=True)
    priority = db.Column(
        db.String(10),
        nullable=False,
        default="normal",
        server_default="normal",
    )
    is_anonymous = db.Column(db.Boolean, nullable=False, default=False)
    photo_filename = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="Received")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)

    status_updates = db.relationship(
        "StatusUpdate",
        back_populates="submission",
        cascade="all, delete-orphan",
    )


class StaffUser(db.Model):
    __tablename__ = "staff_users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'staff')",
            name="valid_staff_role",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="staff")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    status_updates = db.relationship("StatusUpdate", back_populates="staff_user")


class StatusUpdate(db.Model):
    __tablename__ = "status_updates"
    __table_args__ = (
        CheckConstraint(
            "status IN ('Received', 'In Progress', 'Resolved')",
            name="valid_update_status",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(
        db.Integer,
        db.ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    staff_user_id = db.Column(
        db.Integer,
        db.ForeignKey("staff_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    status = db.Column(db.String(20), nullable=False)
    remarks = db.Column(db.Text, nullable=True)
    is_public = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    submission = db.relationship("Submission", back_populates="status_updates")
    staff_user = db.relationship("StaffUser", back_populates="status_updates")
