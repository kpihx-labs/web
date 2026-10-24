"""Regression contracts, using synthetic credentials and no paid network calls."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from xsearch import audio
from xsearch.cli import app
from xsearch.extensions_cli import emit
from xsearch.maps import Maps, json_input
from xsearch.user_config import initialize, settings


@pytest.fixture
def config(tmp_path, monkeypatch):
    monkeypatch.setenv("XSEARCH_CONFIG_DIR", str(tmp_path / "config"))
    return initialize()


def test_config_idempotent(config):
    path = config / "config.py"
    path.write_text('SETTINGS = {"timeout": 7}\n')
    initialize()
    assert settings()["timeout"] == 7
    assert (config / ".env").stat().st_mode & 0o777 == 0o600


def test_missing_humming_credentials_is_actionable(config, monkeypatch):
    for suffix in ("HOST", "ACCESS_KEY", "ACCESS_SECRET"):
        monkeypatch.delenv(f"ACRCLOUD_HUM_{suffix}", raising=False)
    result = CliRunner().invoke(app, ["audio", "--record", "12", "--mode", "hum"])
    assert result.exit_code == 1
    assert "ACRCLOUD_HUM_HOST" in result.output
    assert ".env" in result.output


def test_hum_rejects_songrec():
    with pytest.raises(ValueError, match="not hummed"):
        audio.identify(None, "songrec", "hum", 12, "default", 0, 12, 30)


def test_songrec_adapter(tmp_path, monkeypatch):
    path = tmp_path / "sample.wav"
    path.write_bytes(b"synthetic")
    commands = []

    def fake_run(command, timeout):
        commands.append(command)
        return SimpleNamespace(stdout=json.dumps({"track": {"title": "Fixture"}}))

    monkeypatch.setattr(audio, "run", fake_run)
    result = audio.identify(path, "auto", "recording", None, "default", 4, 10, 30)
    assert result["status"] == "matched"
    assert commands[0][0] == "ffmpeg"
    assert commands[1][0] == "songrec"


def test_acrcloud_signed_request(tmp_path, monkeypatch):
    path = tmp_path / "sample.wav"
    path.write_bytes(b"input")
    monkeypatch.setattr(audio, "credentials", lambda mode: ("test.acrcloud.com", "fixture", "synthetic"))

    def fake_run(command, timeout):
        Path(command[-1]).write_bytes(b"normalized")

    monkeypatch.setattr(audio, "run", fake_run)

    def post(url, data, files, timeout):
        assert url == "https://test.acrcloud.com/v1/identify"
        assert data["signature"] == audio.signature("fixture", "synthetic", data["timestamp"])
        assert data["sample_bytes"] == 10
        return SimpleNamespace(raise_for_status=lambda: None,
                               json=lambda: {"status": {"code": 0}, "metadata": {"humming": []}})

    monkeypatch.setattr(audio.requests, "post", post)
    assert audio.identify(path, "acrcloud", "hum", None, "default", 0, 12, 30)["status"] == "matched"


def test_map_route_arbitrary_profile_and_vertices(monkeypatch):
    maps = Maps({"router": "https://example.test/route", "route_profile": "trekking", "user_agent": "test"})
    monkeypatch.setattr(maps, "search", lambda *args: [{"lon": "2.1", "lat": "48.1"}])
    monkeypatch.setattr(maps, "request", lambda url, **kw: kw["params"])
    result = maps.route(["A", [2.2, 48.2], "B"], "future-vehicle", {"custom_parameter": 42})
    assert result["profile"] == "future-vehicle"
    assert result["lonlats"] == "2.1,48.1|2.2,48.2|2.1,48.1"
    assert result["custom_parameter"] == 42
    assert result["xsearch_resolved_vertices"] == [[2.1, 48.1], [2.2, 48.2], [2.1, 48.1]]


def test_invalid_route():
    maps = Maps({"user_agent": "test"})
    with pytest.raises(ValueError):
        maps.route([], None, {})
    with pytest.raises(ValueError):
        maps.point([200, 90])


def test_json_file_input(tmp_path):
    file = tmp_path / "params.json"
    file.write_text('{"new_provider_option": 123}')
    assert json_input(f"@{file}")["new_provider_option"] == 123


def test_autosave_private_unique_and_json_stdout(tmp_path, capsys):
    emit({"fixture": True}, "audio", "json", tmp_path, False)
    emit({"fixture": True}, "audio", "json", tmp_path, False)
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 2
    assert all(f.stat().st_mode & 0o777 == 0o600 for f in files)
    assert "Autosaved" not in capsys.readouterr().out
    assert "timestamp" in json.loads(files[0].read_text())


def test_help_options():
    runner = CliRunner()
    for arguments in (["audio", "--help"], ["map", "route", "--help"], ["map", "request", "--help"]):
        assert runner.invoke(app, arguments).exit_code == 0


def test_geocode_cache_shared_across_instances(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    calls = []
    monkeypatch.setattr(Maps, "request", lambda *args, **kwargs: calls.append(kwargs) or [{"lat": "48"}])
    configuration = {"geocoder": "https://example.test", "user_agent": "test"}
    assert Maps(configuration).search("A", {}) == Maps(configuration).search("A", {})
    assert len(calls) == 1


def test_query_preserves_arbitrary_predicates(monkeypatch):
    maps = Maps({"overpass": "https://example.test", "user_agent": "test"})
    monkeypatch.setattr(maps, "request", lambda endpoint, **kwargs: kwargs["params"])
    text = '[out:json];nwr["future:tag"="value"](0,0,1,1);out;'
    assert maps.query(text, {"anything": "new"}) == {"data": text, "anything": "new"}
