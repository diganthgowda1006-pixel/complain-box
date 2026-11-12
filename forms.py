from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    FileField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.fields.choices import SelectChoice
from wtforms.validators import DataRequired, Length

from app.i18n import translate
from app.models import CATEGORIES


def strip_text(value):
    return value.strip() if isinstance(value, str) else value


class SubmissionForm(FlaskForm):
    category = SelectField(
        "Category",
        choices=[
            SelectChoice(category, category.replace("_", " ").title())
            for category in CATEGORIES
        ],
        validators=[DataRequired(message="Please choose a category.")],
    )
    description = TextAreaField(
        "What would you like to report?",
        filters=[strip_text],
        validators=[
            DataRequired(message="Please describe the issue."),
            Length(max=2000, message="Description must be 2000 characters or fewer."),
        ],
    )
    location = StringField(
        "Ward or location",
        filters=[strip_text],
        validators=[
            DataRequired(message="Please enter a ward or location."),
            Length(max=200, message="Location must be 200 characters or fewer."),
        ],
    )
    photo = FileField("Photo (optional)")
    is_anonymous = BooleanField("Submit anonymously")
    submit = SubmitField("Submit suggestion")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.category.label.text = translate("Category")
        self.category.choices = [
            SelectChoice(category, translate(category.replace("_", " ").title()))
            for category in CATEGORIES
        ]
        self.description.label.text = translate("What would you like to report?")
        self.location.label.text = translate("Ward or location")
        self.photo.label.text = translate("Photo (optional)")
        self.is_anonymous.label.text = translate("Submit anonymously")
        self.submit.label.text = translate("Submit a suggestion")


class StaffLoginForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[
            DataRequired(message="Enter your username."),
            Length(max=80),
        ],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(message="Enter your password.")],
    )
    submit = SubmitField("Sign in")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.username.label.text = translate("Username")
        self.password.label.text = translate("Password")
        self.submit.label.text = translate("Sign in")


class StatusUpdateForm(FlaskForm):
    status = SelectField(
        "Status",
        choices=[
            SelectChoice(status, status)
            for status in ("Received", "In Progress", "Resolved")
        ],
        validators=[DataRequired(message="Choose a status.")],
    )
    remarks = TextAreaField(
        "Remarks",
        filters=[strip_text],
        validators=[Length(max=2000, message="Remarks must be 2000 characters or fewer.")],
    )
    is_public = BooleanField("Show these remarks on the citizen tracking page", default=True)
    submit = SubmitField("Save update")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status.label.text = translate("Status")
        self.status.choices = [
            SelectChoice(status, translate(status))
            for status in ("Received", "In Progress", "Resolved")
        ]
        self.remarks.label.text = translate("Remarks")
        self.is_public.label.text = translate(
            "Show these remarks on the citizen tracking page"
        )
        self.submit.label.text = translate("Save update")
