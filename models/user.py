# models/user.py
from flask_login import UserMixin
from sqlalchemy.sql import func
from extensions import db

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    phone_verified = db.Column(db.Boolean, default=False)
    agreed_terms = db.Column(db.Boolean, default=False)
    agreed_privacy = db.Column(db.Boolean, default=False)

    # NEW
    avatar_url = db.Column(db.String(255))
    points = db.Column(db.Integer, default=0, nullable=False)
    tokens = db.Column(db.Integer, default=0, nullable=False)
    is_premium = db.Column(db.Boolean, default=False, nullable=False)
    subscription_tier = db.Column(db.String(50))
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<User {self.email}>"

class PointsLog(db.Model):
    __tablename__ = "points_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    amount = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(120))
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

class TokenTransaction(db.Model):
    __tablename__ = "token_transactions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    delta = db.Column(db.Integer, nullable=False)  # +earn, -spend
    reason = db.Column(db.String(120))
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

class Course(db.Model):
    __tablename__ = "courses"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price_cents = db.Column(db.Integer, default=0, nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)

class Lesson(db.Model):
    __tablename__ = "lessons"
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    video_url = db.Column(db.String(500))
    order_index = db.Column(db.Integer, default=0)

class Purchase(db.Model):
    __tablename__ = "purchases"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
