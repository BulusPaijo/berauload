"""Single shared branding row; no unit-specific data."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, CheckConstraint
from ...db import Base, now


class AppBranding(Base):
    __tablename__ = 'app_branding'
    id = Column(Integer, primary_key=True)
    __table_args__ = (CheckConstraint('id = 1', name='ck_app_branding_single_row'),)
    app_name = Column(String(40))
    app_short_name = Column(String(20))
    tagline = Column(String(60))
    login_eyebrow = Column(String(80))
    login_welcome = Column(String(80))
    login_description = Column(String(200))
    login_button_text = Column(String(60))
    login_footnote = Column(String(120))
    organization_name = Column(String(100))
    footer_text = Column(String(120))
    color_primary = Column(String(7))
    color_accent = Column(String(7))
    logo_ext = Column(String(10))
    logo_version = Column(Integer, default=0, nullable=False)
    favicon_ext = Column(String(10))
    favicon_version = Column(Integer, default=0, nullable=False)
    updated_by = Column(Integer, ForeignKey('users.id'))
    updated_at = Column(DateTime(timezone=True), default=now, onupdate=now)
