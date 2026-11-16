from __future__ import annotations
import os
from datetime import datetime, timezone
from sqlalchemy import (create_engine, Column, Integer, String, Boolean, DateTime, Date,
                        ForeignKey, UniqueConstraint, Index, Numeric, Text, JSON, SmallInteger)
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import QueuePool

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./berauload.db')
def _env_int(name: str, default: int, minimum: int = 0) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f'{name} harus bilangan bulat') from exc
    if value < minimum:
        raise ValueError(f'{name} minimal {minimum}')
    return value


DB_POOL_SIZE = _env_int('DB_POOL_SIZE', 5, 1)
DB_MAX_OVERFLOW = _env_int('DB_MAX_OVERFLOW', 5)
DB_POOL_TIMEOUT = _env_int('DB_POOL_TIMEOUT', 30, 1)
DB_POOL_RECYCLE = _env_int('DB_POOL_RECYCLE', 1800, 1)
UVICORN_WORKERS = _env_int('UVICORN_WORKERS', 1, 1)
if UVICORN_WORKERS != 1:
    raise ValueError('UVICORN_WORKERS > 1 belum didukung: cache/setup lintas proses belum teruji')

_kwargs = {'pool_pre_ping': True, 'future': True, 'pool_size': DB_POOL_SIZE,
           'max_overflow': DB_MAX_OVERFLOW, 'pool_timeout': DB_POOL_TIMEOUT,
           'pool_recycle': DB_POOL_RECYCLE}
if DATABASE_URL.startswith('sqlite'):
    _kwargs.update(poolclass=QueuePool, connect_args={'check_same_thread': False})
engine = create_engine(DATABASE_URL, **_kwargs)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

class Base(DeclarativeBase): pass

def now(): return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(70), unique=True, nullable=False, index=True)
    display_name = Column(String(150), nullable=False)
    password_hash = Column(String(300), nullable=False)
    role = Column(String(20), nullable=False, default='operator')
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)

class LoginSession(Base):
    __tablename__ = 'login_sessions'
    id = Column(Integer, primary_key=True)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    csrf_token = Column(String(70), nullable=False)
    user_id = Column(ForeignKey('users.id'), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=now)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)

class Asset(Base):
    __tablename__ = 'assets'
    id = Column(Integer, primary_key=True)
    code = Column(String(80), unique=True, nullable=False)
    name = Column(String(180), nullable=False)
    kind = Column(String(35), nullable=False)
    unit_id = Column(Integer, ForeignKey('org_units.id'), nullable=True)
    active = Column(Boolean, default=True, nullable=False)

class Metric(Base):
    __tablename__ = 'metrics'
    id = Column(Integer, primary_key=True)
    code = Column(String(90), unique=True, nullable=False, index=True)
    name = Column(String(180), nullable=False)
    unit = Column(String(12), nullable=False)
    group_name = Column(String(35), nullable=False)
    input_mode = Column(String(20), nullable=False, default='input')  # input | computed | imported
    asset_id = Column(ForeignKey('assets.id'), nullable=True)
    unit_id = Column(Integer, ForeignKey('org_units.id'), nullable=True)
    role_key = Column(String(60), nullable=True)
    display_order = Column(Integer, default=0)
    active = Column(Boolean, default=True, nullable=False)

class HourRecord(Base):
    __tablename__ = 'hour_records'
    id = Column(Integer, primary_key=True)
    day = Column(Date, nullable=False, index=True)  # local Asia/Makassar civil date
    hour = Column(SmallInteger, nullable=False)
    timestamp_utc = Column(DateTime(timezone=True), nullable=False, index=True)
    entered_by = Column(ForeignKey('users.id'), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=now, onupdate=now)
    __table_args__ = (UniqueConstraint('day','hour',name='uq_day_hour'),)

class Reading(Base):
    __tablename__ = 'readings'
    id = Column(Integer, primary_key=True)
    hour_id = Column(ForeignKey('hour_records.id', ondelete='CASCADE'), nullable=False)
    metric_id = Column(ForeignKey('metrics.id'), nullable=False)
    value = Column(Numeric(18, 5), nullable=False)
    source = Column(String(32), nullable=False, default='manual')
    import_batch_id = Column(String(36), nullable=True)
    __table_args__ = (UniqueConstraint('hour_id','metric_id',name='uq_hour_metric'),
                      Index('ix_reading_metric_hour','metric_id','hour_id'))

class DayState(Base):
    __tablename__ = 'day_states'
    day = Column(Date, primary_key=True)
    status = Column(String(15), default='draft', nullable=False)  # draft/verified/final
    verified_by = Column(ForeignKey('users.id'), nullable=True)
    finalized_by = Column(ForeignKey('users.id'), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=now, onupdate=now)
    note = Column(Text, nullable=True)

class ImportBatch(Base):
    __tablename__ = 'import_batches'
    id = Column(String(36), primary_key=True)
    filename = Column(String(255), nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)
    year = Column(Integer, nullable=False)
    unit_id = Column(Integer, ForeignKey('org_units.id'), nullable=True)
    month = Column(Integer, nullable=False)
    kind = Column(String(20), nullable=True, default='legacy_excel', server_default='legacy_excel')
    created_at = Column(DateTime(timezone=True), default=now)
    created_by = Column(ForeignKey('users.id'), nullable=True)
    hours_created = Column(Integer, default=0)
    hours_skipped = Column(Integer, default=0)
    readings_created = Column(Integer, default=0)
    warnings = Column(JSON, default=list)

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True)
    unit_id = Column(Integer, ForeignKey('org_units.id'), nullable=True)
    created_at = Column(DateTime(timezone=True), default=now, index=True)
    user_id = Column(ForeignKey('users.id'), nullable=True)
    action = Column(String(90), nullable=False)
    target = Column(String(140), nullable=True)
    detail = Column(JSON, default=dict)

def get_db():
    with SessionLocal() as db:
        yield db
