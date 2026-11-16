"""Persisted authentication attempt counts; never store entered passwords."""
from sqlalchemy import Column, DateTime, Integer, String, Index
from ...db import Base, now


class LoginAttempt(Base):
    __tablename__ = 'login_attempts'
    id = Column(Integer, primary_key=True)
    ip = Column(String(100), nullable=False)
    username = Column(String(70), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=now)
    __table_args__ = (Index('ix_login_attempts_identity_time', 'ip', 'username', 'created_at'),)
