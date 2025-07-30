# forms/signup_form.py

from flask_wtf import RecaptchaField
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TelField
from wtforms.validators import DataRequired, Email, Length, EqualTo

class SignupForm(FlaskForm):
    first_name = StringField("First Name", validators=[DataRequired(), Length(min=2)])
    last_name = StringField("Last Name", validators=[DataRequired(), Length(min=2)])
    phone = TelField("Phone Number", validators=[DataRequired(), Length(min=10)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField("Confirm Password", validators=[
        DataRequired(), EqualTo("password", message="Passwords must match")
    ])

    agree_terms = BooleanField("I agree to the Terms and Conditions", validators=[DataRequired()])
    agree_privacy = BooleanField("I agree to the Privacy Policy", validators=[DataRequired()])

    submit = SubmitField("Sign Up")
