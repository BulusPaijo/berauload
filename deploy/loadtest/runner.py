"""Load generator for explicitly marked isolated BerauLoad test instances only."""
import argparse
import asyncio
import json
import math
import os
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit

import httpx


class Stats:
    def __init__(self):
        self.latency = defaultdict(list)
        self.statuses = defaultdict(Counter)
        self.unexpected = Counter()
        self.semantic_errors = Counter()
        self.expected = {}

    def add(self, label, status, seconds, expected_409=False):
        self.latency[label].append(seconds * 1000)
        self.statuses[label][str(status)] += 1
        if not isinstance(status, int) or (not 200 <= status < 300 and not (status == 409 and expected_409)):
            self.unexpected[f'{label}: HTTP {status}'] += 1

    def semantic(self, label, message):
        self.semantic_errors[f'{label}: {message}'] += 1

    def percentile(self, label, value):
        values = sorted(self.latency.get(label, []))
        return values[math.ceil(len(values) * value) - 1] if values else None

    def report(self):
        print('Endpoint                               N    p50ms    p95ms    p99ms  HTTP statuses')
        for label in sorted(self.latency):
            p = [self.percentile(label, q) for q in (.50, .95, .99)]
            print(f'{label:<37} {len(self.latency[label]):>5} '
                  f'{p[0]:>8.1f} {p[1]:>8.1f} {p[2]:>8.1f}  '
                  f'{dict(self.statuses[label])}')
        statuses = Counter()
        for per_endpoint in self.statuses.values():
            statuses.update(per_endpoint)
        print('HTTP codes:', dict(sorted(statuses.items())))
        print('Unexpected HTTP/network errors:', dict(self.unexpected))
        print('Invalid reader payloads:', dict(self.semantic_errors))


async def measured(client, label, method, path, stats, expected_409=False, **kwargs):
    started = time.perf_counter()
    try:
        response = await client.request(method, path, **kwargs)
    except httpx.RequestError as exc:
        stats.add(label, 'network', time.perf_counter() - started)
        stats.unexpected[f'{label}: {type(exc).__name__}'] += 1
        return None
    stats.add(label, response.status_code, time.perf_counter() - started, expected_409)
    return response


async def actor_client(base_url, user, password, transport=None):
    client = httpx.AsyncClient(base_url=base_url, transport=transport, timeout=30.0)
    try:
        response = await client.post('/api/auth/login', json={
            'username': user['username'], 'password': password})
        response.raise_for_status()
        client.headers.update({'X-CSRF-Token': response.json()['csrf'],
                               'X-Unit-Id': str(user['unit_id'])})
        return client
    except Exception:
        await client.aclose()
        raise


def endpoints(user, fixtures):
    unit = user['unit_id']
    start, end = fixtures['previous_day'], fixtures['day']
    return [
        ('GET dashboard', f'/api/dashboard?year={fixtures["year_b"]}&month={int(end[5:7])}'),
        ('GET analytics', f'/api/analytics?metric={user["load_code"]}&start={start}&end={end}&granularity=day'),
        ('GET compare', f'/api/compare?metric={user["load_code"]}&year_a={fixtures["year_a"]}&year_b={fixtures["year_b"]}'),
        ('GET completeness', f'/api/org-units/{unit}/completeness?start={start}&end={end}'),
        ('GET topology', '/api/topology'),
        ('GET completeness export', f'/api/org-units/{unit}/completeness/export?start={start}&end={end}'),
    ]


def check_reader_payload(label, response, stats):
    if response is None or not 200 <= response.status_code < 300:
        return
    if 'export' in label:
        if not response.content.startswith(b'PK'):
            stats.semantic(label, 'XLSX empty/invalid')
        return
    try:
        body = response.json()
        if label in ('GET dashboard', 'GET analytics', 'GET compare'):
            if body.get('configured') is False or not body.get('data' if label != 'GET dashboard' else 'daily'):
                stats.semantic(label, 'missing configuration or sample data')
        elif label == 'GET topology' and not body:
            stats.semantic(label, 'fixture has no diagram')
        elif label == 'GET completeness' and not body.get('rows'):
            stats.semantic(label, 'fixture has no unit matrix')
    except (ValueError, AttributeError, TypeError, KeyError):
        stats.semantic(label, 'malformed JSON')


async def writer(base_url, user, password, stats, end, i, fixtures, transport=None):
    client = await actor_client(base_url, user, password, transport)
    try:
        await asyncio.sleep(i * .12)
        hour = cycle = 0
        while hour == 0 or time.monotonic() < end:
            h = hour % 8
            values = {code: float(h * 100 + i + j + cycle / 100)
                      for j, code in enumerate(user['codes'])}
            response = await measured(client, 'PUT records', 'PUT',
                f'/api/records/{fixtures["day"]}/{h}', stats, json={'values': values})
            if response is not None and response.status_code == 200:
                stats.expected[(user['unit_id'], h)] = values
            hour += 1; cycle += 1
            await asyncio.sleep(3 + i % 3)
    finally:
        await client.aclose()


async def reader(base_url, user, password, stats, end, i, fixtures, transport=None):
    client = await actor_client(base_url, user, password, transport)
    try:
        await asyncio.sleep(i * .05)
        cycles = 0
        while cycles == 0 or time.monotonic() < end:
            cycles += 1
            for label, path in endpoints(user, fixtures):
                response = await measured(client, label, 'GET', path, stats)
                check_reader_payload(label, response, stats)
            await asyncio.sleep(3 + i % 6)
    finally:
        await client.aclose()


async def exporter(base_url, user, password, stats, fixtures, transport=None):
    client = await actor_client(base_url, user, password, transport)
    try:
        path = f'/api/reports/export?start={fixtures["previous_day"]}&end={fixtures["day"]}'
        response = await measured(client, 'GET report export', 'GET', path, stats)
        check_reader_payload('GET report export', response, stats)
    finally:
        await client.aclose()


async def collision_check(base_url, fixtures, stats, transport=None):
    primary, peer = fixtures['writers'][0], fixtures['peer']
    a = await actor_client(base_url, primary, fixtures['password'], transport)
    b = await actor_client(base_url, peer, fixtures['password'], transport)
    day = fixtures['day']; code_a, code_b = primary['codes'][:2]
    endpoint = f'/api/records/{day}/12'
    try:
        first = await measured(a, 'PUT collision disjoint', 'PUT', endpoint, stats,
                               json={'values': {code_a: 10}, 'base': {code_a: None}})
        second = await measured(b, 'PUT collision disjoint', 'PUT', endpoint, stats,
                                json={'values': {code_b: 20}, 'base': {code_b: None}})
        stale = await measured(b, 'PUT collision stale', 'PUT', endpoint, stats,
                               expected_409=True,
                               json={'values': {code_a: 30}, 'base': {code_a: None}})
        current = await measured(a, 'GET collision readback', 'GET',
                                 f'/api/records/day?day={day}', stats)
        values = current.json()['hours'][12]['values'] if current and current.status_code == 200 else {}
        return bool(first and second and stale and first.status_code == 200 and
                    second.status_code == 200 and stale.status_code == 409 and
                    values.get(code_a) == 10 and values.get(code_b) == 20)
    finally:
        await a.aclose(); await b.aclose()


async def readback(base_url, fixtures, stats, writers, transport=None):
    mismatch = 0
    for user in fixtures['writers'][:writers]:
        client = await actor_client(base_url, user, fixtures['password'], transport)
        try:
            response = await measured(client, 'GET write readback', 'GET',
                f'/api/records/day?day={fixtures["day"]}', stats)
            if response is None or response.status_code != 200:
                mismatch += 1
                continue
            hours = response.json()['hours']
            for (unit_id, hour), values in stats.expected.items():
                if unit_id == user['unit_id']:
                    actual = hours[hour]['values']
                    mismatch += sum(actual.get(code) != value for code, value in values.items())
        finally:
            await client.aclose()
    return mismatch


def verdict(stats, mismatch, collision, put_ms, dashboard_ms, logic_only=False):
    checks = {
        'no_unexpected_HTTP_or_network': not stats.unexpected,
        'no_bad_reader_payload': not stats.semantic_errors,
        'no_5xx': not any(int(status) >= 500 for counts in stats.statuses.values()
                          for status in counts if status.isdecimal()),
        'PUT_has_samples': bool(stats.latency.get('PUT records')),
        'dashboard_has_samples': bool(stats.latency.get('GET dashboard')),
        'no_lost_updates': mismatch == 0,
        'collision_safe': collision,
    }
    if not logic_only:
        checks['PUT_p95_limit'] = stats.percentile('PUT records', .95) is not None and \
                                 stats.percentile('PUT records', .95) < put_ms
        checks['dashboard_p95_limit'] = stats.percentile('GET dashboard', .95) is not None and \
                                       stats.percentile('GET dashboard', .95) < dashboard_ms
    else:
        print('LOGIC-ONLY: p95 performance limits not evaluated')
    print('Acceptance checks (test instance only):')
    for name, passed in checks.items():
        print(f'  {name}: {"LULUS" if passed else "GAGAL"}')
    print('KEPUTUSAN:', 'LULUS' if all(checks.values()) else 'GAGAL')
    return all(checks.values())


async def run(base_url, fixtures, duration, writers, readers, exports, transport=None,
              put_ms=1000, dashboard_ms=2000, logic_only=False):
    if len(fixtures['writers']) < writers or len(fixtures['readers']) < readers:
        raise ValueError('Fixture tidak cukup untuk jumlah pengguna yang diminta')
    stats = Stats(); end = time.monotonic() + duration
    tasks = [writer(base_url, user, fixtures['password'], stats, end, i, fixtures, transport)
             for i, user in enumerate(fixtures['writers'][:writers])]
    tasks += [reader(base_url, user, fixtures['password'], stats, end, i, fixtures, transport)
              for i, user in enumerate(fixtures['readers'][:readers])]
    tasks += [exporter(base_url, fixtures['readers'][i % readers], fixtures['password'],
                       stats, fixtures, transport) for i in range(exports)]
    for result in await asyncio.gather(*tasks, return_exceptions=True):
        if isinstance(result, Exception):
            stats.unexpected[f'actor exception: {type(result).__name__}'] += 1
            print('Task error:', repr(result))
    mismatch = await readback(base_url, fixtures, stats, writers, transport)
    collision = await collision_check(base_url, fixtures, stats, transport)
    print('Lost / mismatched values:', mismatch)
    print('Disjoint writes and expected stale-base 409:', collision)
    stats.report()
    passed = verdict(stats, mismatch, collision, put_ms, dashboard_ms, logic_only)
    if transport is not None:
        print('SQLITE LOGIC TEST — NOT A POSTGRESQL CAPACITY BENCHMARK')
    if not passed:
        raise RuntimeError('Load test GAGAL: see checks and endpoint errors above')
    return stats


def arguments():
    p = argparse.ArgumentParser()
    p.add_argument('--base-url', default='http://127.0.0.1:18093')
    p.add_argument('--fixture', required=True)
    p.add_argument('--duration', type=int, default=300)
    p.add_argument('--writers', type=int, default=20)
    p.add_argument('--readers', type=int, default=60)
    p.add_argument('--exports', type=int, default=3)
    p.add_argument('--put-p95-ms', type=float, default=1000)
    p.add_argument('--dashboard-p95-ms', type=float, default=2000)
    p.add_argument('--confirm-isolated', action='store_true')
    p.add_argument('--asgi-sqlite', action='store_true')
    p.add_argument('--logic-only', action='store_true',
                   help='Check functional correctness without enforcing capacity p95 SLAs')
    args = p.parse_args()
    if not args.confirm_isolated:
        raise SystemExit('Requires explicit --confirm-isolated')
    if not 1 <= args.duration <= 900 or args.writers < 1 or args.readers < 1 or args.exports < 0:
        raise SystemExit('Invalid test duration/actor count')
    base = urlsplit(args.base_url)
    if base.scheme != 'http' or base.hostname not in ('localhost', '127.0.0.1') or base.port == 8092:
        raise SystemExit('Refusing non-loopback / known production port 8092')
    return args


async def main():
    args = arguments()
    transport = None
    if args.asgi_sqlite:
        root = Path(tempfile.mkdtemp(prefix='berauload_stage7_loadtest_'))
        os.environ.update(DATABASE_URL=f'sqlite:///{root}/test.db',
            UPLOAD_DIR=str(root / 'uploads'), BERAULOAD_TEST_INSTANCE='true',
            ADMIN_PASSWORD='Stage7-Admin-Isolated-Password')
        from app.main import app
        from deploy.loadtest.fixture import seed
        fixtures = seed(root / 'fixture.json', args.writers, args.readers)
        transport = httpx.ASGITransport(app=app)
        print('Synthetic SQLite test database:', root)
    else:
        fixtures = json.loads(Path(args.fixture).read_text())
        async with httpx.AsyncClient(base_url=args.base_url, timeout=10.0) as client:
            response = await client.get('/api/health')
            response.raise_for_status()
            if response.json().get('test_instance') is not True:
                raise SystemExit('Refusing unmarked instance; BERAULOAD_TEST_INSTANCE not true')
    await run(args.base_url, fixtures, args.duration, args.writers, args.readers,
              args.exports, transport, args.put_p95_ms, args.dashboard_p95_ms,
              args.logic_only)


if __name__ == '__main__':
    asyncio.run(main())
