"""Serialize competing updates of one unit/hour on PostgreSQL only.

A transaction-scoped advisory lock is automatically released at commit/rollback.
SQLite's database write locking is used for offline tests; it isn't a substitute
for PostgreSQL concurrency validation.
"""
from datetime import date
from hashlib import blake2b
from sqlalchemy import text


def hour_lock_key(unit_id: int, day: date, hour: int) -> int:
    raw = f'berauload-hour:{unit_id}:{day.isoformat()}:{hour}'.encode()
    return int.from_bytes(blake2b(raw, digest_size=8).digest(), 'big', signed=True)


def lock_hour(db, unit_id: int, day: date, hour: int) -> None:
    if db.bind.dialect.name == 'postgresql':
        db.execute(text('SELECT pg_advisory_xact_lock(:key)'),
                   {'key': hour_lock_key(unit_id, day, hour)})
