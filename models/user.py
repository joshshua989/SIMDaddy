# models/user.py

from flask_login import UserMixin
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

    def __repr__(self):
        return f"<User {self.email}>"
