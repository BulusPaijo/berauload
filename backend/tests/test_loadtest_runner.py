"""Stage 7 load runner: test both CLI branches without touching production."""
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
from deploy.loadtest.runner import Stats, verdict, check_reader_payload

ROOT = Path(__file__).resolve().parents[2]
PYTHONPATH = f'{ROOT / "backend"}{os.pathsep}{ROOT}'


def command(*args):
    return [sys.executable, '-m', *args]


def environment(tmp_path):
    env = os.environ.copy()
    env.update(PYTHONPATH=PYTHONPATH,
               DATABASE_URL=f'sqlite:///{tmp_path}/test.db',
               UPLOAD_DIR=str(tmp_path / 'uploads'),
               BERAULOAD_TEST_INSTANCE='true',
               ADMIN_PASSWORD='Stage7-Admin-Isolated-Password')
    return env


def test_sqlite_inprocess_branch(tmp_path):
    args = ['deploy.loadtest.runner', '--confirm-isolated', '--asgi-sqlite',
            '--fixture', str(tmp_path / 'ignored.json'), '--duration', '1',
            '--writers', '1', '--readers', '1', '--exports', '1']
    result = subprocess.run(command(*args), cwd=ROOT, env=environment(tmp_path),
                            capture_output=True, text=True, timeout=80)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'GET topology' in result.stdout
    assert 'GET completeness export' in result.stdout
    assert 'KEPUTUSAN: LULUS' in result.stdout


def test_http_branch_with_local_isolated_server(tmp_path):
    """Exercise the branch that formerly raised UnboundLocalError: Path."""
    env = environment(tmp_path)
    fixture = tmp_path / 'synthetic-users.json'
    create = subprocess.run(command('deploy.loadtest.fixture', str(fixture)),
                            env=env, cwd=ROOT, capture_output=True, text=True, timeout=80)
    assert create.returncode == 0, create.stderr
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    base = f'http://127.0.0.1:{port}'
    server = subprocess.Popen(command('uvicorn', 'app.main:app', '--host',
             '127.0.0.1', '--port', str(port)), env=env, cwd=ROOT,
             stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    try:
        for _ in range(100):
            if server.poll() is not None:
                raise AssertionError(f'Server exited: {server.stderr.read()}')
            try:
                reply = httpx.get(base + '/api/health', timeout=.4)
                if reply.status_code == 200 and reply.json()['test_instance']:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(.1)
        else:
            raise AssertionError('Local isolated HTTP server did not start')
        args = ['deploy.loadtest.runner', '--confirm-isolated', '--base-url', base,
                '--fixture', str(fixture), '--duration', '1', '--writers', '1',
                '--readers', '1', '--exports', '1']
        run = subprocess.run(command(*args), env=env, cwd=ROOT,
                             capture_output=True, text=True, timeout=80)
        assert run.returncode == 0, run.stdout + run.stderr
        assert 'GET topology' in run.stdout
        assert 'PUT collision stale' in run.stdout
        assert "'409': 1" in run.stdout
        assert 'KEPUTUSAN: LULUS' in run.stdout
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)


def test_reader_failure_is_reported_even_without_5xx(capsys):
    stats = Stats()
    stats.add('PUT records', 200, .05)
    stats.add('GET dashboard', 200, .05)
    stats.add('GET topology', 404, .05)
    assert not verdict(stats, 0, True, 1000, 2000)
    assert 'KEPUTUSAN: GAGAL' in capsys.readouterr().out


def test_unconfigured_reader_payload_fails_even_with_http_200():
    stats = Stats()
    request = httpx.Request('GET', 'http://127.0.0.1/api/dashboard')
    response = httpx.Response(200, json={'configured': False, 'daily': []}, request=request)
    check_reader_payload('GET dashboard', response, stats)
    assert stats.semantic_errors


def test_unmarked_instance_guard(tmp_path):
    result = subprocess.run(command('deploy.loadtest.runner', '--fixture',
        str(tmp_path / 'unused.json'), '--duration', '1'), cwd=ROOT,
        env=environment(tmp_path), capture_output=True, text=True, timeout=10)
    assert result.returncode != 0
    assert '--confirm-isolated' in result.stderr
