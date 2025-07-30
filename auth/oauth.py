# auth/oauth.py

from flask_dance.contrib.google import make_google_blueprint, google
from flask import flash, redirect, url_for
from flask_login import login_user
from app import db
from models.user import User
import os

google_bp = make_google_blueprint(
    client_id=os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
    scope=["profile", "email"],
    redirect_to="auth.google_login"
)

def register_oauth_blueprints(app):
    app.register_blueprint(google_bp, url_prefix="/auth/google")

@google_bp.route("/login/google/callback")
def google_login():
    if not google.authorized:
        flash("Google login failed", "danger")
        return redirect(url_for("auth.login"))

    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        flash("Failed to fetch user info from Google.", "danger")
        return redirect(url_for("auth.login"))

    data = resp.json()
    email = data["email"]

    user = User.query.filter_by(email=email).first()
    if not user:
        # Auto-create user
        user = User(email=email, first_name=data.get("given_name", ""), last_name=data.get("family_name", ""))
        db.session.add(user)
        db.session.commit()

    login_user(user)
    return redirect(url_for("views.home"))
