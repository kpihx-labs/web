"""Small command surfaces, one envelope and explicit provider/resource boundaries."""

import asyncio
import json
import os
import shutil
import socket
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

import regex as re
import typer

from . import __version__
from .audio import identify
from .backend import BackendError, SurfaceSearcher
from .diagnostics import diagnose
from .documents import compare, extract
from .help_text import ARGUMENTS as A
from .help_text import OPTIONS as H
from .help_text import command
from .http import Session, WebError, save_bytes
from .images import inspect
from .maps import Maps, json_input, json_object, json_vertices
from .output import emit, render
from .research import crawl as crawl_site
from .research import search as search_web
from .user_config import config_dir, initialize, results_dir, settings

app = typer.Typer(
    no_args_is_help=True,
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
    help=command("root"),
    rich_markup_mode="markdown",
    pretty_exceptions_show_locals=False,
    add_completion=False,
)
maps = typer.Typer(
    help=command("map"),
    no_args_is_help=True,
    rich_markup_mode="markdown",
    context_settings={"help_option_names": ["-h", "--help"]},
)
app.add_typer(maps, name="map")


@app.callback()
def global_options(
    version: bool = typer.Option(
        False, "--version", "-v", is_eager=True, help=H["version"]
    ),
):
    if version:
        typer.echo(__version__)
        raise typer.Exit()


def execute(action, function, fmt="table", save_dir=None, no_save=False, report=None):
    try:
        if fmt not in {"table", "json", "jsonl", "csv", "md"}:
            raise WebError("Format must be table, json, jsonl, csv or md")
        if report and (
            Path(report).exists()
            or Path(report).suffix.lower() not in {".html", ".pdf"}
        ):
            raise WebError(
                "Choose a new .html/.pdf report path; existing files are never overwritten"
            )
        data = function()
        code = emit(
            action, data, fmt=fmt, save_dir=save_dir, no_save=no_save, report=report
        )
    except TimeoutError:
        typer.echo(
            "ERROR: operation/regex time budget exceeded; simplify the pattern or adjust regex_timeout in config.py. No successful result was claimed.",
            err=True,
        )
        raise typer.Exit(2) from None
    except (
        WebError,
        BackendError,
        OSError,
        ValueError,
        subprocess.SubprocessError,
        re.error,
        TypeError,
        SyntaxError,
    ) as error:
        typer.echo(f"ERROR: {error}", err=True)
        raise typer.Exit(2) from None
    except Exception as error:
        typer.echo(
            f"ERROR: {action} parser/provider failed ({type(error).__name__}). Check web capabilities, file integrity and current provider availability; report a redacted reproducer. No successful result was claimed.",
            err=True,
        )
        raise typer.Exit(2) from None
    raise typer.Exit(code)


@app.command(help=command("search"))
def search(
    query: str = typer.Argument(..., help=A["query"]),
    engines: str | None = typer.Option(None, "--engines", "-e", help=H["engines"]),
    network: str | None = typer.Option(
        None,
        "--network",
        "-z",
        help=H["network"],
    ),
    rank: str = typer.Option(
        "relevance",
        "--rank",
        "-k",
        help=H["rank"],
    ),
    pages: int | None = typer.Option(
        None,
        "--max-pages",
        "-p",
        "--pages",
        "-P",
        help=H["search_pages"],
    ),
    page: int = typer.Option(1, "--start-page", "-s", help=H["start_page"]),
    limit: int = typer.Option(20, "--limit", "-n", help=H["search_limit"]),
    site: str | None = typer.Option(None, "--site", "-d", help=H["site"]),
    regex: str | None = typer.Option(None, "--regex", "-r", help=H["regex"]),
    category: str | None = typer.Option(None, "--category", "-c", help=H["category"]),
    language: str = typer.Option("all", "--language", "-l", help=H["language"]),
    safe: int = typer.Option(0, "--safe-search", "-m", help=H["safe"]),
    timeout: float = typer.Option(30, "--timeout", "-T", help=H["timeout"]),
    params: str | None = typer.Option(
        None,
        "--params",
        "-X",
        help=H["search_params"],
    ),
    fmt: str = typer.Option("table", "--format", "-f", help=H["format"]),
    save_dir: Path | None = typer.Option(None, "--save-dir", "-S", help=H["save"]),
    no_save: bool = typer.Option(False, "--no-save", "-N", help=H["no_save"]),
    report: Path | None = typer.Option(None, "--report", "-R", help=H["report"]),
    fresh: bool = typer.Option(
        False,
        "--fresh",
        "-F",
        help=H["fresh"],
    ),
):
    """Collect up to -n unique results, stopping at target, source exhaustion or page budget."""
    execute(
        "search",
        lambda: asyncio.run(
            search_web(
                Path(query[1:]).read_text() if query.startswith("@") else query,
                engines=engines,
                network=network,
                rank=rank,
                pages=pages,
                page=page,
                limit=limit,
                site=site,
                regex=regex,
                categories=category,
                language=language,
                safe=safe,
                timeout=timeout,
                fresh=fresh,
                persist=not no_save,
                params=json_object(params),
            )
        ),
        fmt,
        save_dir,
        no_save,
        report,
    )


@app.command(help=command("engines"))
def engines(
    network: str = typer.Option("surface", "--network", "-z", help=H["engine_network"]),
    regex: str | None = typer.Option(None, "--regex", "-r", help=H["engine_regex"]),
    fmt: str = typer.Option("table", "--format", "-f", help=H["format"]),
):
    """Discover configured engines; configured does not imply responding."""

    def action():
        rows = asyncio.run(SurfaceSearcher(service=network).get_engines())["engines"]
        return {
            "engines": [
                r
                for r in rows
                if not regex
                or re.search(
                    regex, r["name"], re.I, timeout=settings()["regex_timeout"]
                )
            ],
            "availability": "Not individually probed",
        }

    execute("engines", action, fmt, no_save=True)


@app.command(help=command("fetch"))
def fetch(
    url: str = typer.Argument(..., help=A["url"]),
    cookies: Path | None = typer.Option(None, "--cookie-file", "-C", help=H["cookies"]),
    header: list[str] = typer.Option([], "--header", "-H", help=H["header"]),
    proxy: str | None = typer.Option(None, "--proxy", "-p", help=H["proxy"]),
    timeout: float = typer.Option(30, "--timeout", "-T", help=H["timeout"]),
    max_bytes: int | None = typer.Option(None, "--max-bytes", "-b", help=H["bytes"]),
    allow_private: bool = typer.Option(
        False, "--allow-private", "-a", help=H["private"]
    ),
    download: Path | None = typer.Option(None, "--download", "-d", help=H["download"]),
    selector: str | None = typer.Option(None, "--selector", "-s", help=H["selector"]),
    regex: str | None = typer.Option(None, "--regex", "-r", help=H["fetch_regex"]),
    fmt: str = typer.Option("table", "--format", "-f", help=H["format"]),
    save_dir: Path | None = typer.Option(None, "--save-dir", "-S", help=H["save"]),
    no_save: bool = typer.Option(False, "--no-save", "-N", help=H["no_save"]),
    report: Path | None = typer.Option(None, "--report", "-R", help=H["report"]),
):
    """Retrieve once, classify access walls and optionally preserve exact bytes."""

    def action():
        record, body = Session(
            url,
            cookies=cookies,
            headers=header,
            proxy=proxy,
            timeout=timeout,
            max_bytes=max_bytes,
            allow_private=allow_private,
        ).fetch(url)
        if selector and "html" not in record["mime"]:
            raise WebError(
                "CSS inspection requires HTML; use web doc for downloaded documents"
            )
        if regex and record["access_state"] == "binary":
            raise WebError(
                "Regex inspection requires extracted text; download the file then use web doc"
            )
        if selector:
            from bs4 import BeautifulSoup

            record["selected_text"] = [
                node.get_text(" ", strip=True)
                for node in BeautifulSoup(body, "html.parser").select(selector)
            ]
        if regex:
            record["matches"] = [
                {"offset": m.start(), "text": m.group()}
                for m in re.finditer(
                    regex, record["text"], timeout=settings()["regex_timeout"]
                )
            ]
        if download:
            record["download"] = save_bytes(download, body)
        record["partial"] = record["access_state"] not in {"ok", "binary"}
        if record["partial"]:
            record["next_action"] = (
                "Use browser-proxy independently for authorized JS/session access; cookies alone may not suffice"
            )
        return record

    execute("fetch", action, fmt, save_dir, no_save, report)


@app.command(help=command("crawl"))
def crawl(
    url: str = typer.Argument(..., help=A["url"]),
    depth: int = typer.Option(1, "--depth", "-D", help=H["depth"]),
    max_pages: int = typer.Option(20, "--max-pages", "-n", help=H["crawl_pages"]),
    delay: float = typer.Option(0.5, "--delay", "-w", help=H["delay"]),
    robots: bool = typer.Option(
        True, "--robots/--no-robots", "-b/-B", help=H["robots"]
    ),
    cookies: Path | None = typer.Option(None, "--cookie-file", "-C", help=H["cookies"]),
    header: list[str] = typer.Option([], "--header", "-H", help=H["header"]),
    proxy: str | None = typer.Option(None, "--proxy", "-p", help=H["proxy"]),
    allow_private: bool = typer.Option(
        False, "--allow-private", "-a", help=H["private"]
    ),
    directory: Path | None = typer.Option(
        None, "--download-dir", "-d", help=H["download_dir"]
    ),
    include: str | None = typer.Option(None, "--match", "-r", help=H["crawl_match"]),
    exclude: str | None = typer.Option(
        None,
        "--exclude",
        "-x",
        help=H["exclude"],
    ),
    fmt: str = typer.Option("table", "--format", "-f", help=H["format"]),
    save_dir: Path | None = typer.Option(None, "--save-dir", "-S", help=H["save"]),
    no_save: bool = typer.Option(False, "--no-save", "-N", help=H["no_save"]),
    report: Path | None = typer.Option(None, "--report", "-R", help=H["report"]),
):
    """Bounded same-host crawl, robots-aware and paced; no browser/JS execution."""
    execute(
        "crawl",
        lambda: crawl_site(
            url,
            Session(
                url,
                cookies=cookies,
                headers=header,
                proxy=proxy,
                allow_private=allow_private,
            ),
            depth=depth,
            max_pages=max_pages,
            delay=delay,
            robots=robots,
            directory=directory,
            include=include,
            exclude=exclude,
        ),
        fmt,
        save_dir,
        no_save,
        report,
    )


@app.command(help=command("doc"))
def doc(
    path: Path = typer.Argument(..., help=A["document"]),
    other: list[Path] = typer.Option([], "--compare", "-c", help=H["compare"]),
    ocr: bool = typer.Option(False, "--ocr", "-O", help=H["ocr"]),
    pages: int = typer.Option(10, "--pages", "-p", help=H["doc_pages"]),
    online: bool = typer.Option(False, "--online", "-o", help=H["online_doc"]),
    query_mode: str = typer.Option("exact", "--query-mode", "-q", help=H["query_mode"]),
    samples: int = typer.Option(3, "--samples", "-s", help=H["samples"]),
    limit: int = typer.Option(5, "--limit", "-n", help=H["doc_limit"]),
    fmt: str = typer.Option("table", "--format", "-f", help=H["format"]),
    save_dir: Path | None = typer.Option(None, "--save-dir", "-S", help=H["save"]),
    no_save: bool = typer.Option(False, "--no-save", "-N", help=H["no_save"]),
    report: Path | None = typer.Option(None, "--report", "-R", help=H["report"]),
):
    """Inspect offline by default; online quotes disclose selected document text."""

    def action():
        result = extract(path, ocr, pages)
        if samples < 1 or limit < 1 or query_mode not in {"exact", "keywords"}:
            raise WebError(
                "Samples/limit must be positive; query-mode is exact or keywords"
            )
        result["comparisons"] = [
            {"other": str(p), **compare(result, extract(p, ocr, pages))} for p in other
        ]
        result["partial"] = bool(result["empty_or_scanned"]) or any(
            item.get("comparison_state") == "insufficient_text"
            for item in result["comparisons"]
        )
        if online:
            paragraphs = [
                line for line in result["text"].splitlines() if len(line.split()) >= 8
            ]
            selected = paragraphs[:: max(1, len(paragraphs) // max(1, samples))][
                :samples
            ]
            candidates, verified, errors, searches = {}, [], [], []
            if not selected:
                errors.append(
                    {
                        "stage": "discovery",
                        "error": "No significant readable fragments; check the page budget or enable local OCR. No online query was made",
                    }
                )
            for quote in selected:
                query = " ".join(quote.split()[:15]).replace('"', "")
                try:
                    found = asyncio.run(
                        search_web(
                            '"' + query + '"' if query_mode == "exact" else query,
                            limit=limit,
                            persist=not no_save,
                        )
                    )
                except (WebError, BackendError) as error:
                    errors.append(
                        {"stage": "discovery", "query": query, "error": str(error)}
                    )
                    continue
                searches.append(
                    {key: value for key, value in found.items() if key != "results"}
                )
                for row in found["results"]:
                    candidates[row["url"]] = row
            for url in list(candidates)[:limit]:
                try:
                    page, body = Session(url).fetch(url)
                    if page["access_state"] not in {"ok", "binary"}:
                        verified.append(
                            {
                                "url": url,
                                "access_state": page["access_state"],
                                "verification": "not_checked_access_wall",
                            }
                        )
                        errors.append(
                            {
                                "stage": "verification",
                                "url": url,
                                "error": "Access wall: page content was not compared. Use an authorized browser independently",
                            }
                        )
                        continue
                    if (
                        page["access_state"] == "binary"
                        and page["mime"] != "application/pdf"
                    ):
                        errors.append(
                            {
                                "stage": "verification",
                                "url": url,
                                "error": "Unsupported binary candidate; download/inspect it explicitly",
                            }
                        )
                        continue
                    candidate = {"text": page["text"], "sha256": page["sha256"]}
                    if page["mime"] == "application/pdf":
                        with tempfile.TemporaryDirectory(
                            prefix="web-candidate-"
                        ) as folder:
                            target = Path(folder) / "candidate.pdf"
                            target.write_bytes(body)
                            candidate = extract(target, ocr, pages)
                    comparison = compare(result, candidate)
                    if comparison["exact_bytes"]:
                        verification = "exact_file"
                    elif comparison.get("comparison_state") == "insufficient_text":
                        verification = "insufficient_text"
                        errors.append(
                            {
                                "stage": "verification",
                                "url": url,
                                "error": "No readable comparison text; inspect the download or enable local OCR for a scanned PDF",
                            }
                        )
                    elif comparison["matching_spans"]:
                        verification = "lexical_overlap"
                    else:
                        verification = "no_significant_lexical_overlap"
                    verified.append(
                        {
                            "url": url,
                            "access_state": page["access_state"],
                            "verification": verification,
                            **comparison,
                        }
                    )
                except WebError as error:
                    errors.append({"url": url, "error": str(error)})
            result.update(
                queries_disclosed=len(selected),
                candidates=list(candidates.values()),
                verified_candidates=verified,
                matching_candidates=[
                    item
                    for item in verified
                    if item.get("verification") in {"exact_file", "lexical_overlap"}
                ],
                errors=errors,
                searches=searches,
                partial=result["partial"]
                or bool(errors)
                or any(item.get("partial", False) for item in searches),
            )
        return result

    execute("doc", action, fmt, save_dir, no_save, report)


@app.command(help=command("image"))
def image(
    path: str = typer.Argument(..., help=A["image"]),
    online: bool = typer.Option(False, "--online", "-o", help=H["online_image"]),
    text_search: bool = typer.Option(
        False,
        "--text-search",
        "-t",
        help=H["text_search"],
    ),
    engines: str = typer.Option("yandex", "--engines", "-e", help=H["image_engines"]),
    limit: int = typer.Option(10, "--limit", "-n", help=H["image_limit"]),
    fmt: str = typer.Option("table", "--format", "-f", help=H["format"]),
    save_dir: Path | None = typer.Option(None, "--save-dir", "-S", help=H["save"]),
    no_save: bool = typer.Option(False, "--no-save", "-N", help=H["no_save"]),
    report: Path | None = typer.Option(None, "--report", "-R", help=H["report"]),
):
    """Inspect EXIF locally; --online explicitly uploads pixels without original EXIF."""

    def action():
        if text_search and not online:
            raise WebError(
                "--text-search discloses OCR words; explicitly add --online or omit --text-search"
            )
        if urlsplit(path).scheme in {"http", "https"}:
            _, _, body = Session(path).get(path)
            with tempfile.TemporaryDirectory(prefix="web-image-input-") as folder:
                local = Path(folder) / "image.bin"
                local.write_bytes(body)
                return asyncio.run(
                    inspect(
                        local,
                        online,
                        engines.split(","),
                        limit,
                        text_search,
                        persist=not no_save,
                    )
                )
        return asyncio.run(
            inspect(
                path,
                online,
                engines.split(","),
                limit,
                text_search,
                persist=not no_save,
            )
        )

    execute(
        "image",
        action,
        fmt,
        save_dir,
        no_save,
        report,
    )


@app.command(help=command("audio"))
def audio(
    path: Path | None = typer.Argument(None, help=A["audio"]),
    record: float | None = typer.Option(None, "--record", "-r", help=H["record"]),
    mode: str = typer.Option("recording", "--mode", "-m", help=H["audio_mode"]),
    duration: float = typer.Option(12, "--duration", "-d", help=H["duration"]),
    source: str = typer.Option("default", "--source", "-s", help=H["source"]),
    offset: float = typer.Option(0, "--offset", "-O", help=H["offset"]),
    fmt: str = typer.Option("table", "--format", "-f", help=H["format"]),
    no_save: bool = typer.Option(False, "--no-save", "-N", help=H["no_save"]),
):
    """Free fingerprint identification; hum attempts have no melody-recognition guarantee."""
    execute(
        "audio",
        lambda: identify(path, record, mode, duration, source, offset),
        fmt,
        no_save=no_save,
    )


@app.command(help=command("similar"))
def similar(
    url: str = typer.Argument(..., help=A["site_url"]),
    engines: str | None = typer.Option(None, "--engines", "-e", help=H["engines"]),
    limit: int = typer.Option(10, "--limit", "-n", help=H["similar_limit"]),
    fmt: str = typer.Option("table", "--format", "-f", help=H["format"]),
):
    """Alternatives discovery query, explicitly NOT a semantic embeddings API."""

    def action():
        host = urlsplit(url if "://" in url else "https://" + url).hostname
        data = asyncio.run(
            search_web(f'"{host}" alternatives', engines=engines, limit=limit)
        )
        data["method"] = "Lexical alternatives discovery, not semantic similarity"
        return data

    execute("similar", action, fmt)


@app.command(help=command("doctor"))
def doctor(
    live: bool = typer.Option(False, "--live", "-l", help=H["live"]),
    fmt: str = typer.Option("table", "--format", "-f", help=H["format"]),
):
    def action():
        result = asyncio.run(
            diagnose(frontend="http://127.0.0.1:8080", live=live, engines="bing")
        )
        if result["state"] == "failed":
            raise WebError(json.dumps(result))
        return {**result, "partial": result["state"] == "degraded"}

    execute("doctor", action, fmt, no_save=True)


@app.command(help=command("capabilities"))
def capabilities(fmt: str = typer.Option("table", "--format", "-f", help=H["format"])):
    execute(
        "capabilities",
        lambda: {
            "version": __version__,
            "native": {
                tool: bool(shutil.which(tool))
                for tool in ("songrec", "ffmpeg", "pdftoppm", "tesseract", "fc-match")
            },
            "js_rendering": False,
            "i2p_search": False,
            "i2p_fetch": "Requires configured HTTP proxy",
            "humming": "SongRec best-effort only; no free reliable melody API configured",
            "semantic_similarity": False,
        },
        fmt,
        no_save=True,
    )


@app.command(help=command("setup"))
def setup():
    typer.echo(initialize())


@app.command(help=command("purge"))
def purge(yes: bool = typer.Option(False, "--yes", "-y", help=H["confirm_purge"])):
    """Preview or trash owned runtime data only; never source/shared dependencies."""
    if yes:
        gateway = Path(settings()["searxng_socket"])
        if gateway.is_socket():
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
                probe.settimeout(0.3)
                try:
                    probe.connect(str(gateway))
                except OSError:
                    pass
                else:
                    raise typer.BadParameter(
                        "Backend IPC is still active. Run make backend-down before purge"
                    )
    paths = [
        config_dir(),
        Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "web",
        Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "web",
        results_dir(),
    ]
    for path in paths:
        if path.name not in {"web", "web-results"} or path.is_symlink():
            raise typer.BadParameter(
                "Refusing to purge a custom/non-owned/symlink configuration path"
            )
        if path.exists() and path.stat().st_uid != os.getuid():
            raise typer.BadParameter(
                "Refusing to purge a runtime directory owned by another user"
            )
        typer.echo(str(path))
        if yes and path.exists():
            subprocess.run(["rm", "-r", str(path)], check=True)
    if not yes:
        typer.echo(
            "Preview only. Stop your backend before purging its IPC cache; use make backend-down."
        )


@maps.command("search", help=command("map_search"))
def map_search(
    query: str = typer.Argument(..., help=A["place"]),
    params: str | None = typer.Option(None, "--params", "-P", help=H["map_params"]),
    fmt: str = typer.Option("table", "--format", "-f", help=H["format"]),
):
    execute(
        "map-search",
        lambda: {
            "result": Maps(settings()).search(query, json_object(params)),
            "attribution": "OpenStreetMap contributors / ODbL",
        },
        fmt,
    )


@maps.command("query", help=command("map_query"))
def map_query(
    query: str = typer.Argument(..., help=A["overpass"]),
    fmt: str = typer.Option("json", "--format", "-f", help=H["format"]),
):
    execute(
        "map-query",
        lambda: {
            "result": Maps(settings()).query(
                Path(query[1:]).read_text() if query.startswith("@") else query, {}
            ),
            "attribution": "OpenStreetMap contributors / ODbL",
        },
        fmt,
    )


@maps.command("route", help=command("map_route"))
def map_route(
    vertices: str = typer.Argument(..., help=A["vertices"]),
    profile: str | None = typer.Option(None, "--profile", "-p", help=H["profile"]),
    params: str | None = typer.Option(None, "--params", "-P", help=H["map_params"]),
    fmt: str = typer.Option("json", "--format", "-f", help=H["format"]),
):
    execute(
        "map-route",
        lambda: {
            "result": Maps(settings()).route(
                json_vertices(vertices), profile, json_object(params)
            ),
            "attribution": "OpenStreetMap contributors / ODbL",
        },
        fmt,
    )


@maps.command("request", help=command("map_request"))
def map_request(
    endpoint: str = typer.Argument(..., help=A["endpoint"]),
    method: str = typer.Option("GET", "--method", "-X", help=H["method"]),
    params: str | None = typer.Option(None, "--params", "-P", help=H["map_params"]),
    body: str | None = typer.Option(None, "--body", "-b", help=H["body"]),
    fmt: str = typer.Option("json", "--format", "-f", help=H["format"]),
):
    execute(
        "map-request",
        lambda: {
            "result": Maps(settings()).request(
                endpoint,
                method,
                json_object(params),
                body=json_input(body) if body else None,
            )
        },
        fmt,
    )


def main():
    app()


@app.command(help=command("show"))
def show(
    path: Path = typer.Argument(..., help=A["snapshot"]),
    fmt: str = typer.Option("table", "--format", "-f", help=H["show_format"]),
):
    """Render the SAME saved snapshot as table or JSON, with no network requests."""
    try:
        record = json.loads(path.read_text())
        if (
            not isinstance(record, dict)
            or not {"action", "timestamp", "data", "status"} <= record.keys()
        ):
            raise ValueError("Expected a web result envelope, not a cookie/header file")
        typer.echo(
            f"Saved snapshot from {record['timestamp']}; no network request.", err=True
        )
        if fmt == "table":
            render(record)
        elif fmt == "json":
            print(json.dumps(record, ensure_ascii=False, indent=2))
        else:
            raise ValueError("show supports table or json")
    except (ValueError, OSError) as error:
        typer.echo(f"ERROR: {error}", err=True)
        raise typer.Exit(2) from None


@app.command(help=command("archive"))
def archive(
    url: str = typer.Argument(..., help=A["archive_url"]),
    params: str | None = typer.Option(None, "--params", "-P", help=H["archive_params"]),
    fmt: str = typer.Option("json", "--format", "-f", help=H["format"]),
):
    """Explicit Wayback closest-snapshot lookup; no automatic document URL disclosure."""

    def action():
        from urllib.parse import urlencode

        if urlsplit(url).username is not None:
            raise WebError("Do not send credential-bearing URLs to an archive provider")
        endpoint = "https://archive.org/wayback/available?" + urlencode(
            {"url": url, **json_object(params)}
        )
        _, _, body = Session(endpoint).get(endpoint)
        data = json.loads(body)
        return {
            "requested_url": url,
            "provider_response": data,
            "qualification": "A closest snapshot is not an exhaustive history or proof of identical document bytes",
        }

    execute("archive", action, fmt)


if __name__ == "__main__":
    main()
