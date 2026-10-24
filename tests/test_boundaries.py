"""Privacy, hidden-network routing and media capability regression boundaries."""

import asyncio
import json
import socket
import urllib.request
from types import SimpleNamespace

import pytest
import requests
from PIL import Image
from typer.testing import CliRunner

from k_web import audio, cli, images
from k_web.http import Session, WebError


def test_custom_backend_does_not_reuse_surface_socket(monkeypatch):
    import k_web.backend as backend

    monkeypatch.setattr(
        backend,
        "settings",
        lambda: {"search_backends": {"custom": {"url": "http://127.0.0.1:9000"}}},
    )
    client = backend.SurfaceSearcher(service="custom")
    assert client.channel == "tcp" and client.base_url.endswith(":9000")


def test_purge_refuses_an_active_gateway_without_touching_real_state(
    tmp_path, monkeypatch
):
    path = tmp_path / "gateway.sock"
    monkeypatch.setattr(cli, "settings", lambda: {"searxng_socket": str(path)})
    monkeypatch.setattr(cli, "config_dir", lambda: tmp_path / "config/web")
    monkeypatch.setattr(cli, "results_dir", lambda: tmp_path / "web-results")
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind(str(path))
        server.listen()
        result = CliRunner().invoke(cli.app, ["purge", "--yes"])
    assert result.exit_code != 0 and "still active" in result.output


def test_tor_redirect_never_downgrades_or_leaks_dns(monkeypatch):
    calls = []
    session = Session("http://fixture.onion")

    def reply(url, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            is_redirect=len(calls) == 1,
            headers={"Location": "https://example.org", "Content-Type": "text/plain"},
            status_code=200,
            iter_content=lambda size: iter([b"public content"]),
            close=lambda: None,
        )

    monkeypatch.setattr(session.client, "get", reply)
    monkeypatch.setattr(
        "socket.getaddrinfo",
        lambda *args, **kwargs: pytest.fail("Tor redirect attempted local DNS"),
    )
    assert session.fetch("http://fixture.onion")[0]["text"] == "public content"
    assert all(call["proxies"]["http"].startswith("socks5h://") for call in calls)


def test_proxy_failure_never_retries_direct(monkeypatch):
    session = Session("http://fixture.onion")

    def fail(*args, **kwargs):
        raise requests.exceptions.ProxyError("fixture")

    monkeypatch.setattr(session.client, "get", fail)
    with pytest.raises(WebError, match="no direct fallback"):
        session.fetch("http://fixture.onion")


def test_authorization_not_forwarded_across_ports(monkeypatch):
    session = Session(
        "http://127.0.0.1:10001", headers=["Authorization: fixture"], allow_private=True
    )
    calls = []

    def reply(url, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            is_redirect=len(calls) == 1,
            headers={
                "Location": "http://127.0.0.1:10002",
                "Content-Type": "text/plain",
            },
            status_code=200,
            iter_content=lambda size: iter([b"fixture"]),
            close=lambda: None,
        )

    monkeypatch.setattr(session.client, "get", reply)
    session.fetch("http://127.0.0.1:10001")
    assert calls[0]["headers"].get("Authorization") == "fixture"
    assert "Authorization" not in calls[1]["headers"]


def test_cookie_scope_secure_httponly_and_path(tmp_path):
    path = tmp_path / "cookies.txt"
    path.write_text(
        "# Netscape HTTP Cookie File\n#HttpOnly_.example.org\tTRUE\t/private\tTRUE\t2147483647\tsid\tfixture\n"
    )
    session = Session("https://example.org", cookies=path)
    for url, allowed in (
        ("https://example.org/private/a", True),
        ("http://example.org/private/a", False),
        ("https://unrelated.org/private", False),
        ("https://example.org/public", False),
    ):
        request = urllib.request.Request(url)
        session.client.cookies.add_cookie_header(request)
        assert bool(request.get_header("Cookie")) == allowed


def test_offline_image_metadata_has_no_upload(tmp_path):
    path = tmp_path / "image.jpg"
    image = Image.new("RGB", (100, 100), "blue")
    exif = image.getexif()
    exif[271] = "Fixture camera"
    image.save(path, exif=exif)
    result = asyncio.run(images.inspect(path))
    assert result["metadata"]["make"] == "Fixture camera"
    assert not result["uploaded_sanitized_pixels"] and not result["results"]


def test_hum_is_a_qualified_default_attempt_without_paid_provider(monkeypatch):
    monkeypatch.setattr(audio.shutil, "which", lambda command: command)
    monkeypatch.setattr(
        audio.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout=json.dumps({})),
    )
    result = audio.identify("fixture.wav", mode="hum")
    assert (
        result["provider"] == "songrec" and result["partial"] and not result["matched"]
    )
