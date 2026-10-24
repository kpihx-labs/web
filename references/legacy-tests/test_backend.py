"""Failure/recovery contracts: an outage is never a valid empty search."""

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler
from socketserver import UnixStreamServer

import httpx
import pytest
from typer.testing import CliRunner

import xsearch.backend as module
from xsearch import cli
from xsearch.backend import BackendError, SurfaceSearcher


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch):
    monkeypatch.setattr(module, "settings", lambda: {"search_attempts": 3, "search_retry_delay": 0})


def client(handler):
    return SurfaceSearcher("http://backend.test", transport=httpx.MockTransport(handler))


def test_connection_reset_recovers_without_empty_success():
    attempts = []

    def handler(request):
        attempts.append(request)
        if len(attempts) < 3:
            raise httpx.ReadError("reset", request=request)
        return httpx.Response(200, json={"engines": [{"name": "fixture"}]})

    result = asyncio.run(client(handler).get_engines())
    assert result["engines"][0]["name"] == "fixture"
    assert len(attempts) == 3


def test_unreachable_explains_recovery_without_query_leak():
    def handler(request):
        raise httpx.ConnectError("sensitive query", request=request)

    with pytest.raises(BackendError, match="BACKEND_UNREACHABLE") as info:
        asyncio.run(client(handler).search("private search"))
    assert "make recover" in str(info.value)
    assert "private search" not in str(info.value)
    assert "sensitive query" not in str(info.value)


@pytest.mark.parametrize("response", [
    httpx.Response(200, text="<html>proxy login</html>"),
    httpx.Response(200, json=[]),
    httpx.Response(200, json={"engines": []}),
    httpx.Response(403),
    httpx.Response(503),
])
def test_bad_config_never_becomes_empty_catalogue(response):
    with pytest.raises(BackendError):
        asyncio.run(client(lambda request: response).get_engines())


def test_valid_empty_search_is_distinct_from_failed_search():
    good = client(lambda request: httpx.Response(200, json={"results": [], "unresponsive_engines": []}))
    assert asyncio.run(good.search("nothing")) == []
    bad = client(lambda request: httpx.Response(200, json={"results": [], "unresponsive_engines": [["fixture", "CAPTCHA"]]}))
    with pytest.raises(BackendError, match="UPSTREAM_SEARCH_FAILED"):
        asyncio.run(bad.search("nothing"))


def test_partial_upstream_results_warn(capsys):
    searcher = client(lambda request: httpx.Response(200, json={
        "results": [{"title": "fixture", "url": "https://example.org", "engine": "working"}],
        "unresponsive_engines": [["blocked", "CAPTCHA"]],
    }))
    assert len(asyncio.run(searcher.search("query"))) == 1
    assert "partial upstream coverage" in capsys.readouterr().err


def test_http_503_then_restart_recovery():
    attempts = []

    def handler(request):
        attempts.append(1)
        return httpx.Response(503) if len(attempts) == 1 else httpx.Response(200, json={"results": []})

    assert asyncio.run(client(handler).search("query")) == []
    assert len(attempts) == 2


def test_deadline_bounds_retrying():
    async def handler(request):
        await asyncio.sleep(1)
        return httpx.Response(200, json={"results": []})

    with pytest.raises(BackendError, match="BACKEND_TIMEOUT"):
        asyncio.run(client(handler).search("query", timeout=0.01))


def test_engines_cli_failure_is_not_a_table(monkeypatch):
    class Failed:
        async def get_engines(self):
            raise BackendError("BACKEND_UNREACHABLE", "local", "connection refused")

    monkeypatch.setattr(cli, "SurfaceSearcher", Failed)
    result = CliRunner().invoke(cli.app, ["engines"])
    assert result.exit_code == 2
    assert "BACKEND_UNREACHABLE" in result.stderr
    assert "Engine" not in result.stdout


def test_search_failure_does_not_autosave_empty_results(monkeypatch, tmp_path):
    class Failed:
        async def search(self, **kwargs):
            raise BackendError("BACKEND_UNREACHABLE", "local", "connection refused")

    monkeypatch.setattr(cli, "SurfaceSearcher", Failed)
    result = CliRunner().invoke(cli.app, ["search", "fixture", "-f", "json", "--save-dir", str(tmp_path)])
    assert result.exit_code == 2
    assert result.stdout == ""
    assert not list(tmp_path.iterdir())


def test_successful_json_stdout_is_not_contaminated(monkeypatch, tmp_path):
    class Working:
        unresponsive_engines = ()

        async def search(self, **kwargs):
            return []

    monkeypatch.setattr(cli, "SurfaceSearcher", Working)
    result = CliRunner().invoke(cli.app, ["search", "fixture", "-f", "json", "--save-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert json.loads(result.stdout) == []
    assert "Autosaved" in result.stderr
    assert next(tmp_path.iterdir()).stat().st_mode & 0o777 == 0o600


def test_private_unix_transport_does_not_use_tcp_or_environment_proxy(tmp_path, monkeypatch):
    path = tmp_path / "backend.sock"

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = b'{"engines":[{"name":"fixture"}]}'
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    options = {"searxng_url": "http://127.0.0.1:9", "searxng_socket": str(path)}
    monkeypatch.setattr(module, "settings", lambda: options)
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
    with UnixStreamServer(str(path), Handler) as server:
        thread = threading.Thread(target=server.handle_request, daemon=True)
        thread.start()
        searcher = SurfaceSearcher()
        assert searcher.channel == "unix"
        assert asyncio.run(searcher.get_engines())["engines"][0]["name"] == "fixture"
        thread.join(timeout=2)


def test_explicit_remote_endpoint_is_not_overridden_by_local_socket(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "settings", lambda: {"searxng_transport": "unix", "searxng_socket": str(tmp_path / "socket")})
    assert SurfaceSearcher("http://explicit.test").channel == "tcp"
