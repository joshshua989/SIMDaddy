
# models/dk.py

from datetime import datetime
from extensions import db

class DKEntry(db.Model):
    __tablename__ = "dk_entries"

    id = db.Column(db.Integer, primary_key=True)

    # ⚠️ Make sure this matches your User.__tablename__ ("users" in your DB list)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # NEW: keep DraftKings' contest identifier (string)
    contest_id = db.Column(db.String(64), index=True, nullable=True)

    # Native DraftKings entry identifier (primary dedupe key per user)
    entry_id = db.Column(db.String(64), nullable=False, index=True)

    contest_name = db.Column(db.String(255))
    buy_in = db.Column(db.Float, default=0.0)
    payout = db.Column(db.Float, default=0.0)
    fpts = db.Column(db.Float, default=0.0)
    contest_date = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "entry_id", name="uq_dk_user_entry"),
    )

    def __repr__(self):
        return f"<DKEntry user={self.user_id} entry={self.entry_id} contest_id={self.contest_id}>"
