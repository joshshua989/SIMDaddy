
# auth/routes.py

from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db
from models.user import User
from forms.login_form import LoginForm
from forms.signup_form import SignupForm
from utils.phone_verification import verify_sms_code, send_sms_code

auth_bp = Blueprint('auth', __name__, url_prefix='')

# -------------------------------
# Login
# -------------------------------
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.username.data.lower()).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            session['user'] = user.email
            return redirect(url_for('views.home'))
        else:
            flash("Invalid email or password.", "danger")
    return render_template("login.html", form=form)

# -------------------------------
# Logout
# -------------------------------
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('user', None)
    flash("You’ve been logged out.", "info")
    return redirect(url_for("auth.login"))

# -------------------------------
# Signup
# -------------------------------
@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        if not form.agree_terms.data or not form.agree_privacy.data:
            flash("You must agree to the terms and privacy policy.", "warning")
            return render_template("signup.html", form=form)

        existing_user = User.query.filter_by(email=form.email.data.lower()).first()
        if existing_user:
            flash("An account with this email already exists.", "danger")
            return render_template("signup.html", form=form)

        # Phone verification (using a hidden input for SMS code)
        sms_code = request.form.get("sms_code")
        if not verify_sms_code(form.phone.data, sms_code):
            flash("Invalid or missing SMS verification code.", "danger")
            return render_template("signup.html", form=form)

        # Create new user
        new_user = User(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            phone=form.phone.data,
            email=form.email.data.lower(),
            password=generate_password_hash(form.password.data)
        )
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        session['user'] = new_user.email
        flash("Account created successfully!", "success")
        return redirect(url_for("views.home"))

    return render_template("signup.html", form=form)

# -------------------------------
# (Optional) Send SMS for Verification
# -------------------------------
@auth_bp.route('/send_code', methods=['POST'])
def send_code():
    phone = request.form.get("phone")
    if phone:
        success = send_sms_code(phone)
        if success:
            return {"status": "ok"}
    return {"status": "error"}, 400

