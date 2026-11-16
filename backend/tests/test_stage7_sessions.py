"""Stage 7 session bounded sliding expiry and persisted login rate limiting."""
from datetime import timedelta, datetime, timezone
import pytest
from fastapi.testclient import TestClient
from app import security, main
from app.db import LoginSession, User, get_db
from app.modules.sessions.models import LoginAttempt
from app.modules.sessions.migrations import run, VERSION
from app.modules.formulas.models import SchemaMigration
from test_stage4a_units import site, login


def test_session_touch_throttle_absolute_and_me_expiry(site, monkeypatch):
    client, Session, headers, ids = site
    with Session() as db:
        row=db.query(LoginSession).order_by(LoginSession.id.desc()).first()
        original=security.aware(row.created_at)
        initial=security.aware(row.expires_at)
        session_id=row.id
    monkeypatch.setattr(security,'now',lambda:original+timedelta(minutes=2))
    response=client.get('/api/auth/me')
    assert response.status_code==200 and 'expires_at' in response.json()
    with Session() as db:
        assert security.aware(db.get(LoginSession,session_id).expires_at)==initial
    monkeypatch.setattr(security,'now',lambda:original+timedelta(minutes=6))
    assert client.get('/api/auth/me').status_code==200
    with Session() as db:
        new=security.aware(db.get(LoginSession,session_id).expires_at)
        assert new>initial
    monkeypatch.setattr(security,'now',lambda:original+timedelta(hours=23,minutes=58))
    # No refresh from >12 hour inactivity: the earlier session expiry is honored.
    assert client.get('/api/auth/me').status_code==401


def test_rate_limit_is_persisted_and_cleanup_is_idempotent(site):
    client, Session, headers, ids=site
    username='user-stage7-not-exist'
    for _ in range(5):
        assert client.post('/api/auth/login',json={'username':username,'password':'wrong'}).status_code==401
    assert client.post('/api/auth/login',json={'username':username,'password':'wrong'}).status_code==429
    with Session() as db:
        assert db.query(LoginAttempt).filter_by(username=username).count()==5
        security.cleanup_sessions(db,force=True)
        assert db.query(LoginAttempt).filter_by(username=username).count()==5


def test_session_migration_runs_once(site):
    client, Session, headers, ids=site
    engine=Session.kw['bind']
    with Session() as db:
        first=db.query(SchemaMigration).filter_by(version=VERSION).count()
        attempts=db.query(LoginAttempt).count()
    run(engine);run(engine)
    with Session() as db:
        assert first==1 and db.query(SchemaMigration).filter_by(version=VERSION).count()==1
        assert db.query(LoginAttempt).count()==attempts


def test_absolute_expiry_caps_even_active_sessions(site,monkeypatch):
    client, Session, headers, ids=site
    stamp=datetime.now(timezone.utc)
    with Session() as db:
        session=db.query(LoginSession).order_by(LoginSession.id.desc()).first()
        session.created_at=stamp-timedelta(hours=23)
        session.last_seen_at=stamp-timedelta(minutes=6)
        session.expires_at=stamp+timedelta(hours=1)
        db.commit()
    monkeypatch.setattr(security,'now',lambda:stamp)
    assert client.get('/api/auth/me').status_code==200
    with Session() as db:
        session=db.query(LoginSession).order_by(LoginSession.id.desc()).first()
        assert security.aware(session.expires_at)==stamp+timedelta(hours=1)
    monkeypatch.setattr(security,'now',lambda:stamp+timedelta(hours=1,seconds=1))
    assert client.get('/api/auth/me').status_code==401


def test_stage6_schema_additive_upgrade_is_once(tmp_path):
    from sqlalchemy import create_engine,text,inspect
    from app.modules.sessions.migrations import run
    engine=create_engine('sqlite:///'+str(tmp_path/'stage6-upgrade.db'))
    with engine.begin() as conn:
        conn.execute(text('CREATE TABLE login_sessions (id INTEGER PRIMARY KEY, token_hash VARCHAR(64), csrf_token VARCHAR(70), user_id INTEGER, expires_at TIMESTAMP, created_at TIMESTAMP)'))
        conn.execute(text("INSERT INTO login_sessions (id,token_hash,csrf_token,user_id,expires_at) VALUES (1,'old','old',1,'2033-01-01')"))
    run(engine)
    with engine.connect() as conn:
        assert 'last_seen_at' in {x['name'] for x in inspect(conn).get_columns('login_sessions')}
        assert conn.execute(text('SELECT count(*) FROM login_sessions')).scalar()==1
        assert conn.execute(text('SELECT count(*) FROM login_attempts')).scalar()==0
    run(engine)
    with engine.connect() as conn:
        assert conn.execute(text('SELECT count(*) FROM login_sessions')).scalar()==1
        assert conn.execute(text('SELECT count(*) FROM schema_migrations WHERE version=:v'),{'v':VERSION}).scalar()==1


def test_invalid_pool_settings_refused_on_import(tmp_path):
    import subprocess,sys,os
    env={**os.environ,'PYTHONPATH':'backend','DB_POOL_SIZE':'not-a-number'}
    done=subprocess.run([sys.executable,'-c','import app.db'],env=env,
                        capture_output=True,text=True,timeout=15)
    assert done.returncode!=0 and 'DB_POOL_SIZE' in done.stderr
    env={**os.environ,'PYTHONPATH':'backend','UVICORN_WORKERS':'2'}
    done=subprocess.run([sys.executable,'-c','import app.db'],env=env,
                        capture_output=True,text=True,timeout=15)
    assert done.returncode!=0 and 'UVICORN_WORKERS' in done.stderr
