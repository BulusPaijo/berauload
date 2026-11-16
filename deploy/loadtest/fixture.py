"""Create synthetic users and historical readings ONLY in an isolated test DB."""
import calendar
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


def dates():
    today = datetime.now(ZoneInfo('Asia/Makassar')).date()
    day = today - timedelta(days=2)
    previous = day.replace(year=day.year - 1,
                           day=min(day.day, calendar.monthrange(day.year - 1, day.month)[1]))
    return day, day - timedelta(days=1), previous


def add_sample_readings(db, metrics, dates_to_seed):
    from app.db import HourRecord, Reading
    from app.db import now
    for day, hours in dates_to_seed:
        for hour in hours:
            timestamp = datetime(day.year, day.month, day.day, hour,
                                 tzinfo=ZoneInfo('Asia/Makassar')).astimezone(timezone.utc)
            slot = db.query(HourRecord).filter_by(day=day, hour=hour).first()
            if slot is None:
                slot = HourRecord(day=day, hour=hour, timestamp_utc=timestamp,
                                  updated_at=now())
                db.add(slot)
                db.flush()
            for index, (load, capacity) in enumerate(metrics):
                for metric, value in ((load, 250.0 + index * 10 + hour),
                                      (capacity, 400.0 + index * 10)):
                    db.add(Reading(hour_id=slot.id, metric_id=metric.id, value=value,
                                   source='loadtest_fixture'))


def seed(path, writers=20, readers=60):
    if os.getenv('BERAULOAD_TEST_INSTANCE', '').lower() != 'true':
        raise SystemExit('Refusing fixture creation outside marked test instance')
    if not 1 <= writers <= 100 or not 1 <= readers <= 300:
        raise ValueError('Synthetic fixture requires 1..100 writers and 1..300 readers')
    from app.main import setup
    from app.db import SessionLocal, User, Metric, Asset
    from app.security import hash_password
    from app.modules.org_units.models import OrgUnit, UserUnitAccess
    from app.modules.org_units.repository import root
    from app.modules.topology.models import TopologyDiagram
    from app.modules.topology.service import EMPTY_LAYOUT
    setup()
    password = os.environ.get('LOADTEST_ACCOUNT_PASSWORD', 'Stage7-Only-Test-Password-2026')
    password_hash = hash_password(password)
    day, previous_day, previous_year_day = dates()
    results = {'writers': [], 'readers': [], 'password': password,
               'day': day.isoformat(), 'previous_day': previous_day.isoformat(),
               'previous_year_day': previous_year_day.isoformat(),
               'year_a': previous_year_day.year, 'year_b': day.year}
    with SessionLocal() as db:
        top = root(db)
        metric_pairs = []
        for i in range(writers):
            unit = OrgUnit(code=f'loadtest_ulp_{i}', name=f'Test ULP {i}',
                           parent_id=top.id, level='ulp', active=True)
            db.add(unit); db.flush()
            asset = Asset(code=f'loadtest_asset_{i}', name=f'Test Asset {i}',
                          kind='pembangkit', unit_id=unit.id)
            db.add(asset); db.flush()
            params = []
            for j in range(60):
                metric = Metric(code=f'loadtest_{i}_{j}',
                                name=f'Test parameter {i} {j}', unit='kW',
                                group_name='PEMBANGKIT', input_mode='input',
                                asset_id=asset.id, unit_id=unit.id, active=True,
                                role_key={0: 'system.load', 1: 'system.capacity'}.get(j))
                db.add(metric)
                params.append(metric)
            db.flush()
            metric_pairs.append((params[0], params[1]))
            db.add(TopologyDiagram(unit_id=unit.id, name=f'Test diagram {i}',
                                   description='Data sintetis uji baca',
                                   layout=EMPTY_LAYOUT.copy(), version=1))
            user = User(username=f'lt_writer_{i}', display_name=f'LT Writer {i}',
                        password_hash=password_hash, role='operator')
            db.add(user); db.flush()
            db.add(UserUnitAccess(user_id=user.id, unit_id=unit.id, role='operator'))
            results['writers'].append({'username': user.username, 'unit_id': unit.id,
                                      'codes': [p.code for p in params]})
        peer = User(username='lt_peer_0', display_name='LT Peer 0',
                    password_hash=password_hash, role='operator')
        db.add(peer); db.flush()
        db.add(UserUnitAccess(user_id=peer.id, unit_id=results['writers'][0]['unit_id'],
                              role='operator'))
        results['peer'] = {'username': peer.username,
                           'unit_id': results['writers'][0]['unit_id']}
        for i in range(readers):
            writer = results['writers'][i % writers]
            viewer = User(username=f'lt_view_{i}', display_name=f'LT Viewer {i}',
                          password_hash=password_hash, role='management')
            db.add(viewer); db.flush()
            db.add(UserUnitAccess(user_id=viewer.id, unit_id=writer['unit_id'],
                                  role='management'))
            results['readers'].append({'username': viewer.username,
                'unit_id': writer['unit_id'], 'load_code': writer['codes'][0],
                'capacity_code': writer['codes'][1]})
        add_sample_readings(db, metric_pairs, [(previous_year_day, range(4)),
                                               (previous_day, range(8)),
                                               (day, range(8, 12))])
        db.commit()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2))
    return results


if __name__ == '__main__':
    import sys
    seed(sys.argv[1])
