"""Permanent operator privacy policy: no search/geocoding result files."""

import asyncio

import pytest

from k_web import research
from k_web.http import WebError
from k_web.maps import Maps
from k_web.output import emit


def test_export_override_cannot_recreate_persistent_result_cache(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    with pytest.raises(WebError, match="forbidden under XDG_CACHE_HOME"):
        emit("search", {"results": []}, save_dir=cache / "web/search")
    monkeypatch.setenv("WEB_RESULTS_DIR", str(cache / "web/geocode"))
    with pytest.raises(WebError, match="forbidden under XDG_CACHE_HOME"):
        emit("map-search", {})
    assert not cache.exists()


def test_search_does_not_touch_xdg_cache_even_with_old_cache_settings(
    tmp_path, monkeypatch
):
    cache = tmp_path / "cache"
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    settings = research.settings()
    monkeypatch.setattr(
        research,
        "settings",
        lambda: {**settings, "search_cache_ttl": 999999, "search_stale_ttl": 999999},
    )

    async def collect(*args, **kwargs):
        return {
            "results": [{"url": "https://example.org"}],
            "backends": [],
            "partial": False,
        }

    monkeypatch.setattr(research, "_collect", collect)
    result = asyncio.run(
        research.search("synthetic private query", limit=1, persist=True, fresh=False)
    )
    assert result["cache"]["disk_persistence"] is False
    assert not cache.exists()


def test_geocoding_coalesces_in_ram_only_and_runtime_has_no_query(
    tmp_path, monkeypatch
):
    cache = tmp_path / "cache"
    runtime = tmp_path / "runtime"
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(runtime))
    monkeypatch.setattr("k_web.maps.time.sleep", lambda delay: None)
    calls = []

    def request(*args, **kwargs):
        calls.append(kwargs)
        return [{"lat": "1", "lon": "2"}]

    opts = {
        "geocoder": "https://example.test",
        "user_agent": "fixture",
        "geocode_cache_seconds": 999999,
    }
    first = Maps(opts)
    monkeypatch.setattr(first, "request", request)
    first.search("synthetic confidential place", {})
    first.search("synthetic confidential place", {})
    assert len(calls) == 1
    second = Maps(opts)
    monkeypatch.setattr(second, "request", request)
    second.search("synthetic confidential place", {})
    assert len(calls) == 2 and not cache.exists()
    files = list(runtime.rglob("*"))
    assert not any(item.suffix == ".json" for item in files)
    for item in files:
        if item.is_file():
            assert item.name == "geocode.lock"
            assert float(item.read_text()) > 0
