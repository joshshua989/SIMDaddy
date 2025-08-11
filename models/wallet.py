# models/wallet.py
from datetime import datetime
from extensions import db

class Wallet(db.Model):
    __tablename__ = "wallets"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, index=True, nullable=False)
    coins_balance = db.Column(db.Integer, default=0, nullable=False)
    rep_total = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CoinTxn(db.Model):
    __tablename__ = "coin_txns"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True, nullable=False)
    delta = db.Column(db.Integer, nullable=False)  # +earn / -spend
    kind = db.Column(db.String(40), nullable=False)  # 'earn', 'purchase', 'spend', 'refund', ...
    reason = db.Column(db.String(120))              # 'unlock_week:2025-03', 'daily_bonus', ...
    idempotency_key = db.Column(db.String(64), unique=True)  # to prevent double-apply
    balance_after = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

class RepEvent(db.Model):
    __tablename__ = "rep_events"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True, nullable=False)
    points = db.Column(db.Integer, nullable=False)   # always positive
    reason = db.Column(db.String(120))
    total_after = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

class Entitlement(db.Model):
    __tablename__ = "entitlements"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True, nullable=False)
    scope = db.Column(db.String(20), nullable=False)        # 'week' | 'season' | 'merch'
    key = db.Column(db.String(64), nullable=False)          # e.g., '2025-W03' or '2025-SEASON'
    source = db.Column(db.String(20), nullable=False)       # 'coins' | 'purchase' | 'grant'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('user_id','scope','key', name='uq_user_scope_key'),)
