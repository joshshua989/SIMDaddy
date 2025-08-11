# services/wallet.py
from sqlalchemy import select
from extensions import db
from models.wallet import Wallet, CoinTxn, RepEvent, Entitlement

def get_or_create_wallet(user_id: int) -> Wallet:
    w = Wallet.query.filter_by(user_id=user_id).first()
    if not w:
        w = Wallet(user_id=user_id, coins_balance=0, rep_total=0)
        db.session.add(w)
        db.session.flush()
    return w

def add_rep(user_id: int, points: int, reason: str = "") -> int:
    assert points > 0
    w = get_or_create_wallet(user_id)
    w.rep_total += points
    ev = RepEvent(user_id=user_id, points=points, reason=reason, total_after=w.rep_total)
    db.session.add(ev)
    db.session.commit()
    return w.rep_total

def _apply_coin_delta(user_id: int, delta: int, kind: str, reason: str = "", idem: str | None = None) -> int:
    # idempotency
    if idem:
        existing = CoinTxn.query.filter_by(idempotency_key=idem).first()
        if existing:
            return existing.balance_after

    # lock wallet row if exists
    w = db.session.execute(
        select(Wallet).where(Wallet.user_id == user_id).with_for_update()
    ).scalar_one_or_none()
    if not w:
        w = get_or_create_wallet(user_id)

    new_bal = w.coins_balance + delta
    if new_bal < 0:
        raise ValueError("Insufficient coins")

    w.coins_balance = new_bal
    txn = CoinTxn(
        user_id=user_id,
        delta=delta,
        kind=kind,
        reason=reason,
        idempotency_key=idem,
        balance_after=new_bal,
    )
    db.session.add(txn)
    db.session.commit()
    return new_bal

def earn_coins(user_id: int, amount: int, reason: str, idem: str | None = None) -> int:
    return _apply_coin_delta(user_id, +abs(amount), "earn", reason, idem)

def purchase_coins(user_id: int, amount: int, reason: str, idem: str | None = None) -> int:
    return _apply_coin_delta(user_id, +abs(amount), "purchase", reason, idem)

def spend_coins(user_id: int, amount: int, reason: str, idem: str | None = None) -> int:
    return _apply_coin_delta(user_id, -abs(amount), "spend", reason, idem)

def grant_entitlement(user_id: int, scope: str, key: str, source: str) -> Entitlement:
    e = Entitlement(user_id=user_id, scope=scope, key=key, source=source)
    db.session.add(e)
    db.session.commit()
    return e

def has_entitlement(user_id: int, scope: str, key: str) -> bool:
    return db.session.query(
        db.exists().where(Entitlement.user_id == user_id)
                    .where(Entitlement.scope == scope)
                    .where(Entitlement.key == key)
    ).scalar()
