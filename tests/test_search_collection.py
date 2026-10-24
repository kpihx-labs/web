"""Target collection and presentation use the exact same candidate snapshots."""

import asyncio
import json

import pytest
from rich.console import Console
from typer.testing import CliRunner

from k_web import cli, output, research
from k_web.backend import BackendError
from k_web.http import WebError
from k_web.models import SearchResult


def row(number, score=1.0, engines=None, url=None):
    names = engines or ["google cse"]
    return SearchResult(
        "fixture",
        url or f"https://example.org/{number}",
        "evidence",
        names[0],
        names[0],
        "surface",
        "now",
        score=score,
        engines=names,
    )


class Backend:
    def __init__(self):
        self.calls = []
        self.unresponsive_engines = []
        self.down = False

    async def get_engines(self):
        return {
            "engines": [
                {
                    "name": name,
                    "enabled": name not in {"yahoo", "yep", "mwmbl"},
                    "categories": ["general"],
                    "paging": True,
                }
                for name in ("google cse", "duckduckgo", "yahoo", "yep", "mwmbl")
            ]
        }

    async def search(self, query, **kwargs):
        self.calls.append(kwargs)
        if self.down:
            raise BackendError("BACKEND_UNREACHABLE", "fixture", "offline")
        start = (kwargs["page"] - 1) * 20
        return [row(i) for i in range(start, start + 20)]


def test_count_is_a_target_and_stops_as_soon_as_met(monkeypatch):
    backend = Backend()
    monkeypatch.setattr(research, "SurfaceSearcher", lambda: backend)
    result = asyncio.run(research.search("fixture", limit=30, persist=False))
    assert len(result["results"]) == 30
    assert result["attempted_pages"] == [1, 2]
    assert result["target_reached"] and result["stop_reason"] == "target_reached"
    assert len(backend.calls) == 2


def test_same_snapshot_reused_without_another_provider_request(monkeypatch):
    backend = Backend()
    monkeypatch.setattr(research, "SurfaceSearcher", lambda: backend)
    first = asyncio.run(research.search("fixture", limit=10))
    second = asyncio.run(research.search("fixture", limit=10))
    assert first["results"] == second["results"]
    assert second["cache"]["state"] == "snapshot"
    assert len(backend.calls) == 1


def test_shortfall_is_explicit_and_explicit_engines_never_fallback(monkeypatch):
    backend = Backend()

    async def replies(query, **kwargs):
        backend.calls.append(kwargs)
        return [row(i) for i in range(5)]

    backend.search = replies
    monkeypatch.setattr(research, "SurfaceSearcher", lambda: backend)
    result = asyncio.run(
        research.search(
            "fixture", engines="google cse", limit=30, pages=5, persist=False
        )
    )
    assert (
        len(result["results"]) == 5
        and result["partial"]
        and not result["target_reached"]
    )
    assert result["stop_reason"] == "no_new_candidates"
    assert len(backend.calls) == 2
    assert not result["fallback_engines_used"]


def test_provider_failure_does_not_erase_a_labelled_stale_snapshot(monkeypatch):
    backend = Backend()
    monkeypatch.setattr(research, "SurfaceSearcher", lambda: backend)
    asyncio.run(research.search("fixture", limit=10))
    backend.down = True
    options = research.settings()
    monkeypatch.setattr(
        research, "settings", lambda: {**options, "search_cache_ttl": 0}
    )
    result = asyncio.run(research.search("fixture", limit=10))
    assert result["partial"] and result["cache"]["state"] == "stale_on_error"
    with pytest.raises(WebError):
        asyncio.run(research.search("fixture", limit=10, fresh=True))


def test_free_fallback_is_bounded_and_explicit(monkeypatch):
    backend = Backend()

    async def replies(query, **kwargs):
        backend.calls.append(kwargs)
        if not kwargs["engines"]:
            backend.unresponsive_engines = [["google cse", "too many requests"]]
            raise BackendError("UPSTREAM_SEARCH_FAILED", "fixture", "rate limited")
        return [row(i, engines=["yahoo"]) for i in range(30)]

    backend.search = replies
    monkeypatch.setattr(research, "SurfaceSearcher", lambda: backend)
    result = asyncio.run(research.search("fixture", limit=30, persist=False))
    assert len(result["results"]) == 30 and result["partial"]
    assert len(backend.calls) == 2
    assert result["backends"][0]["fallback_engines_used"] == ["yahoo", "yep", "mwmbl"]
    assert "make recover" not in str(
        BackendError("UPSTREAM_SEARCH_FAILED", "fixture", "limited")
    )


def test_score_sorting_and_all_duplicate_contributors(monkeypatch):
    backend = Backend()

    async def replies(query, **kwargs):
        return [row(1, 0.1), row(2, 0.9, ["duckduckgo"]), row(1, 0.5, ["duckduckgo"])]

    backend.search = replies
    monkeypatch.setattr(research, "SurfaceSearcher", lambda: backend)
    result = asyncio.run(research.search("fixture", limit=2, persist=False))
    assert result["results"][0]["url"].endswith("/2")
    assert result["results"][1]["sources"] == ["google cse", "duckduckgo"]


def test_table_urls_are_folded_not_ellipsized_and_sources_are_plural(
    tmp_path, monkeypatch
):
    url = "https://example.org/" + "verylongsegment/" * 10 + "?document=123456789"
    record = {
        "action": "search",
        "status": "ok",
        "timestamp": "fixture",
        "data": {
            "results": [
                {
                    "title": "fixture",
                    "url": url,
                    "sources": ["google cse", "duckduckgo"],
                }
            ],
            "limit": 1,
        },
    }
    console = Console(width=70, record=True, color_system=None)
    monkeypatch.setattr(output, "Console", lambda *args, **kwargs: console)
    output.render(record)
    text = console.export_text()
    assert "Sources" in text and "…" not in text
    pieces = [
        line.split("│")[3].strip()
        for line in text.splitlines()
        if line.startswith("│") and len(line.split("│")) == 6
    ]
    assert "".join(pieces) == url
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(record))
    shown = CliRunner().invoke(cli.app, ["show", str(path), "-f", "json"])
    assert shown.exit_code == 0 and json.loads(shown.stdout) == record


def test_cli_lowercase_p_is_a_budget_not_start_page(monkeypatch):
    captured = {}

    async def fake(query, **kwargs):
        captured.update(kwargs)
        return {"results": [], "partial": False}

    monkeypatch.setattr(cli, "search_web", fake)
    result = CliRunner().invoke(
        cli.app, ["search", "fixture", "-p", "5", "-n", "30", "-N", "-f", "json"]
    )
    assert result.exit_code == 0 and captured["pages"] == 5 and captured["page"] == 1
