from __future__ import annotations
import hashlib, hmac, os, secrets
from datetime import timedelta, timezone, datetime
from fastapi import HTTPException, Request, Response, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, delete, text
from .db import get_db, User, LoginSession, now
from .modules.sessions.models import LoginAttempt

COOKIE_NAME = 'berauload_session'
SESSION_HOURS = int(os.getenv('SESSION_HOURS', '12'))
SESSION_MAX_HOURS = int(os.getenv('SESSION_MAX_HOURS', '24'))
SECURE_COOKIE = os.getenv('COOKIE_SECURE', 'false').lower() == 'true'
if SESSION_HOURS < 1 or SESSION_MAX_HOURS < SESSION_HOURS:
    raise ValueError('SESSION_MAX_HOURS harus >= SESSION_HOURS >= 1')
_TOUCH_SECONDS = 300
_last_cleanup: datetime | None = None


def aware(value):
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode('utf-8'), salt=salt,
                       n=2**14, r=8, p=1, dklen=32)
    return 'scrypt$' + salt.hex() + '$' + dk.hex()


def password_ok(password: str, stored: str) -> bool:
    try:
        alg, salt, digest = stored.split('$')
        return alg == 'scrypt' and hmac.compare_digest(
            hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt),
                           n=2**14, r=8, p=1, dklen=32), bytes.fromhex(digest))
    except (ValueError, TypeError):
        return False


def cleanup_sessions(db: Session, force: bool = False) -> None:
    global _last_cleanup
    stamp = now()
    if not force and _last_cleanup and (stamp-_last_cleanup).total_seconds() < 3600:
        return
    db.execute(delete(LoginSession).where(LoginSession.expires_at < stamp))
    db.execute(delete(LoginAttempt).where(
        LoginAttempt.created_at < stamp-timedelta(minutes=15)))
    db.commit()
    _last_cleanup = stamp


def rate_limit(db: Session, ip: str, username: str) -> None:
    username = username.lower()
    stamp = now()
    # A database-backed counter is shared by processes; lock on PostgreSQL
    # prevents simultaneous attempts from bypassing the limit.
    if db.bind.dialect.name == 'postgresql':
        from .modules.records.locking import hour_lock_key
        from datetime import date
        db.execute(text('SELECT pg_advisory_xact_lock(:key)'),
                   {'key': hour_lock_key(0, date(2000, 1, 1),
                                         int.from_bytes(hashlib.sha256((ip+username).encode()).digest()[:4], 'big'))})
    count = db.query(func.count(LoginAttempt.id)).filter(
        LoginAttempt.ip == ip, LoginAttempt.username == username,
        LoginAttempt.created_at >= stamp-timedelta(minutes=15)).scalar() or 0
    if count >= 5:
        raise HTTPException(429, 'Terlalu banyak percobaan login. Coba lagi nanti.')
    db.add(LoginAttempt(ip=ip, username=username, created_at=stamp))
    db.commit()


def clear_attempts(db: Session, ip: str, username: str) -> None:
    db.query(LoginAttempt).filter_by(ip=ip, username=username.lower()).delete()
    db.commit()


def absolute_expiry(row):
    return aware(row.created_at) + timedelta(hours=SESSION_MAX_HOURS)


def effective_expiry(row):
    return min(aware(row.expires_at), absolute_expiry(row))


def cookie_age(row) -> int:
    return max(0, int((effective_expiry(row) - now()).total_seconds()))


def set_session_cookie(response: Response, token: str, age: int) -> None:
    response.set_cookie(COOKIE_NAME, token, httponly=True, secure=SECURE_COOKIE,
                        samesite='strict', max_age=age, path='/')


def new_session(db: Session, user: User):
    token, csrf = secrets.token_urlsafe(40), secrets.token_urlsafe(32)
    stamp = now()
    row = LoginSession(user_id=user.id,
                       token_hash=hashlib.sha256(token.encode()).hexdigest(),
                       csrf_token=csrf, created_at=stamp, last_seen_at=stamp,
                       expires_at=stamp+timedelta(hours=SESSION_HOURS))
    db.add(row)
    db.commit()
    return token, csrf, cookie_age(row)


def resolve_session(request: Request, db: Session, response: Response | None = None):
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(401, 'Silakan login')
    row = db.query(LoginSession).filter(
        LoginSession.token_hash == hashlib.sha256(token.encode()).hexdigest()).first()
    if not row:
        raise HTTPException(401, 'Sesi tidak valid')
    stamp = now()
    if effective_expiry(row) <= stamp:
        raise HTTPException(401, 'Sesi kedaluwarsa')
    u = db.get(User, row.user_id)
    if not u or not u.active:
        raise HTTPException(401, 'Akun tidak aktif')
    last = aware(row.last_seen_at or row.created_at)
    if (stamp-last).total_seconds() >= _TOUCH_SECONDS:
        row.expires_at = min(stamp+timedelta(hours=SESSION_HOURS), absolute_expiry(row))
        row.last_seen_at = stamp
        db.commit()
        if response is not None:
            set_session_cookie(response, token, cookie_age(row))
    return u, row


def current_user(request: Request, response: Response,
                 db: Session = Depends(get_db)) -> User:
    u, session = resolve_session(request, db, response)
    if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
        if not hmac.compare_digest(request.headers.get('x-csrf-token', ''),
                                   session.csrf_token):
            raise HTTPException(403, 'Token CSRF tidak valid; muat ulang halaman')
    return u


def require(*roles):
    def inner(u: User = Depends(current_user)):
        if u.role not in roles:
            raise HTTPException(403, 'Hak akses tidak mencukupi')
        return u
    return inner
