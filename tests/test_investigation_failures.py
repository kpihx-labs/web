"""Inspection must not become a false clean audit when discovery/access fails."""

import asyncio
import json
from types import SimpleNamespace

import pytest
from PIL import Image
from typer.testing import CliRunner

from k_web import cli, images, research
from k_web.documents import compare
from k_web.http import WebError

TEXT = "This is a synthetic public technical report with enough significant words to exercise discovery reliably."


def test_empty_text_is_not_a_perfect_lexical_match():
    result = compare({"text": "", "sha256": "a"}, {"text": "", "sha256": "b"})
    assert result["lexical_similarity"] is None
    assert result["comparison_state"] == "insufficient_text"
    assert not result["exact_bytes"]


def test_doc_keeps_local_inspection_when_every_discovery_query_fails(
    tmp_path, monkeypatch
):
    path = tmp_path / "public.md"
    path.write_text(TEXT)

    async def failed(*args, **kwargs):
        raise WebError("Provider quota unavailable; no inference of absence")

    monkeypatch.setattr(cli, "search_web", failed)
    result = CliRunner().invoke(
        cli.app, ["doc", str(path), "--online", "-N", "-f", "json"]
    )
    assert result.exit_code == 3, result.output
    data = json.loads(result.stdout)["data"]
    assert data["text"] == TEXT and data["errors"]
    assert data["queries_disclosed"] == 1 and not data["verified_candidates"]


def test_doc_propagates_partial_search_and_does_not_compare_login_wall(
    tmp_path, monkeypatch
):
    path = tmp_path / "public.md"
    path.write_text(TEXT)

    async def partial(*args, **kwargs):
        return {
            "results": [{"url": "https://example.org/private"}],
            "partial": True,
            "upstream_issues": [["fixture", "CAPTCHA"]],
        }

    monkeypatch.setattr(cli, "search_web", partial)
    monkeypatch.setattr(
        cli,
        "Session",
        lambda url: SimpleNamespace(
            fetch=lambda url: ({"access_state": "auth_required"}, b"login")
        ),
    )
    result = CliRunner().invoke(
        cli.app, ["doc", str(path), "--online", "-N", "-f", "json"]
    )
    assert result.exit_code == 3, result.output
    data = json.loads(result.stdout)["data"]
    assert data["searches"][0]["partial"]
    assert data["verified_candidates"][0]["verification"] == "not_checked_access_wall"
    assert "lexical_similarity" not in data["verified_candidates"][0]


def test_doc_without_significant_fragments_does_not_claim_online_check(tmp_path):
    path = tmp_path / "short.txt"
    path.write_text("Tiny fixture.")
    result = CliRunner().invoke(
        cli.app, ["doc", str(path), "--online", "-N", "-f", "json"]
    )
    assert result.exit_code == 3
    data = json.loads(result.stdout)["data"]
    assert data["queries_disclosed"] == 0 and data["errors"]


@pytest.mark.parametrize(
    "text,state,exit_code",
    [
        ("Unrelated content.", "no_significant_lexical_overlap", 0),
        ("", "insufficient_text", 3),
    ],
)
def test_retrieved_unrelated_candidate_is_not_a_document_match(
    tmp_path, monkeypatch, text, state, exit_code
):
    path = tmp_path / "public.md"
    path.write_text(TEXT)

    async def found(*args, **kwargs):
        return {"results": [{"url": "https://example.org/unrelated"}], "partial": False}

    monkeypatch.setattr(cli, "search_web", found)
    page = {
        "access_state": "ok",
        "mime": "text/html",
        "text": text,
        "sha256": "different",
    }
    monkeypatch.setattr(
        cli,
        "Session",
        lambda url: SimpleNamespace(fetch=lambda url: (page, b"unrelated")),
    )
    result = CliRunner().invoke(
        cli.app, ["doc", str(path), "--online", "-N", "-f", "json"]
    )
    assert result.exit_code == exit_code, result.output
    data = json.loads(result.stdout)["data"]
    assert not data["matching_candidates"]
    assert data["verified_candidates"][0]["verification"] == state


def test_image_text_discovery_failure_preserves_metadata(tmp_path, monkeypatch):
    path = tmp_path / "logo.png"
    Image.new("RGB", (50, 50), "white").save(path)

    class Network:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

    class Provider:
        def __init__(self, **kwargs):
            pass

        async def search(self, file):
            return SimpleNamespace(raw=[])

    async def failed(*args, **kwargs):
        raise WebError("fixture providers unavailable")

    monkeypatch.setattr(images, "Network", Network)
    monkeypatch.setattr(images, "Yandex", Provider)
    monkeypatch.setattr(images.shutil, "which", lambda command: command)
    monkeypatch.setattr(
        images.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout="Public fixture logo"),
    )
    monkeypatch.setattr(research, "search", failed)
    result = asyncio.run(images.inspect(path, online=True, text_search=True))
    assert result["metadata"]["width"] == 50 and result["partial"]
    assert any(item["engine"] == "ocr-text-search" for item in result["errors"])


def test_text_search_requires_explicit_disclosure_flag():
    result = CliRunner().invoke(
        cli.app, ["image", "not-opened.png", "--text-search", "-N"]
    )
    assert result.exit_code == 2 and "explicitly add --online" in result.output
