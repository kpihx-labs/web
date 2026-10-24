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
from .http import Session, WebError, save_bytes
from .images import inspect
from .maps import Maps, json_input, json_object, json_vertices
from .output import emit
from .research import crawl as crawl_site
from .research import search as search_web
from .user_config import config_dir, initialize, results_dir, settings

app = typer.Typer(
    no_args_is_help=True,
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
maps = typer.Typer(
    help="Provider-native JSON/QL operations, not a fixed list of vehicles/tags."
)
app.add_typer(maps, name="map")


@app.callback()
def global_options(
    version: bool = typer.Option(False, "--version", "-v", is_eager=True),
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


@app.command()
def search(
    query: str,
    engines: str | None = typer.Option(None, "--engines", "-e"),
    network: str | None = typer.Option(
        None,
        "--network",
        "-z",
        help="Comma-separated configured backends; surface/onion, or custom search_backends names",
    ),
    rank: str = typer.Option("provider", "--rank", "-k"),
    pages: int = typer.Option(1, "--pages", "-P"),
    page: int = typer.Option(1, "--page", "-p"),
    limit: int = typer.Option(20, "--limit", "-n"),
    site: str | None = typer.Option(None, "--site", "-d"),
    regex: str | None = typer.Option(None, "--regex", "-r"),
    category: str | None = typer.Option(None, "--category", "-c"),
    language: str = typer.Option("all", "--language", "-l"),
    safe: int = typer.Option(0, "--safe-search", "-m"),
    timeout: float = typer.Option(30, "--timeout", "-T"),
    params: str | None = typer.Option(
        None,
        "--params",
        "-X",
        help="Extra SearXNG JSON parameters or @file; raw query operators pass through unchanged",
    ),
    fmt: str = typer.Option("table", "--format", "-f"),
    save_dir: Path | None = typer.Option(None, "--save-dir", "-S"),
    no_save: bool = typer.Option(False, "--no-save", "-N"),
    report: Path | None = typer.Option(None, "--report", "-R"),
):
    """Search explicit index pages. -n is not depth; -P controls the page budget."""
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
                params=json_object(params),
            )
        ),
        fmt,
        save_dir,
        no_save,
        report,
    )


@app.command()
def engines(
    network: str = typer.Option("surface", "--network", "-z"),
    regex: str | None = typer.Option(None, "--regex", "-r"),
    fmt: str = typer.Option("table", "--format", "-f"),
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


@app.command()
def fetch(
    url: str,
    cookies: Path | None = typer.Option(None, "--cookie-file", "-C"),
    header: list[str] = typer.Option([], "--header", "-H"),
    proxy: str | None = typer.Option(None, "--proxy", "-p"),
    timeout: float = typer.Option(30, "--timeout", "-T"),
    max_bytes: int | None = typer.Option(None, "--max-bytes", "-b"),
    allow_private: bool = typer.Option(False, "--allow-private", "-a"),
    download: Path | None = typer.Option(None, "--download", "-d"),
    selector: str | None = typer.Option(None, "--selector", "-s"),
    regex: str | None = typer.Option(None, "--regex", "-r"),
    fmt: str = typer.Option("table", "--format", "-f"),
    save_dir: Path | None = typer.Option(None, "--save-dir", "-S"),
    no_save: bool = typer.Option(False, "--no-save", "-N"),
    report: Path | None = typer.Option(None, "--report", "-R"),
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


@app.command()
def crawl(
    url: str,
    depth: int = typer.Option(1, "--depth", "-D"),
    max_pages: int = typer.Option(20, "--max-pages", "-n"),
    delay: float = typer.Option(0.5, "--delay", "-w"),
    robots: bool = typer.Option(True, "--robots/--no-robots"),
    cookies: Path | None = typer.Option(None, "--cookie-file", "-C"),
    header: list[str] = typer.Option([], "--header", "-H"),
    proxy: str | None = typer.Option(None, "--proxy", "-p"),
    allow_private: bool = typer.Option(False, "--allow-private", "-a"),
    directory: Path | None = typer.Option(None, "--download-dir", "-d"),
    include: str | None = typer.Option(None, "--match", "-r"),
    exclude: str | None = typer.Option(
        None,
        "--exclude",
        "-x",
        help="URL exclusion regex; default guards common state-changing GET links; empty disables after review",
    ),
    fmt: str = typer.Option("table", "--format", "-f"),
    save_dir: Path | None = typer.Option(None, "--save-dir", "-S"),
    no_save: bool = typer.Option(False, "--no-save", "-N"),
    report: Path | None = typer.Option(None, "--report", "-R"),
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


@app.command()
def doc(
    path: Path,
    other: list[Path] = typer.Option([], "--compare", "-c"),
    ocr: bool = typer.Option(False, "--ocr", "-O"),
    pages: int = typer.Option(10, "--pages", "-p"),
    online: bool = typer.Option(False, "--online", "-o"),
    query_mode: str = typer.Option("exact", "--query-mode", "-q"),
    samples: int = typer.Option(3, "--samples", "-s"),
    limit: int = typer.Option(5, "--limit", "-n"),
    fmt: str = typer.Option("table", "--format", "-f"),
    save_dir: Path | None = typer.Option(None, "--save-dir", "-S"),
    no_save: bool = typer.Option(False, "--no-save", "-N"),
    report: Path | None = typer.Option(None, "--report", "-R"),
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
        if online:
            paragraphs = [
                line for line in result["text"].splitlines() if len(line.split()) >= 8
            ]
            selected = paragraphs[:: max(1, len(paragraphs) // max(1, samples))][
                :samples
            ]
            candidates, verified, errors = {}, [], []
            for quote in selected:
                query = " ".join(quote.split()[:15]).replace('"', "")
                found = asyncio.run(
                    search_web(
                        '"' + query + '"' if query_mode == "exact" else query,
                        limit=limit,
                    )
                )
                for row in found["results"]:
                    candidates[row["url"]] = row
            for url in list(candidates)[:limit]:
                try:
                    page, body = Session(url).fetch(url)
                    candidate = {"text": page["text"], "sha256": page["sha256"]}
                    if page["mime"] == "application/pdf":
                        with tempfile.TemporaryDirectory(
                            prefix="web-candidate-"
                        ) as folder:
                            target = Path(folder) / "candidate.pdf"
                            target.write_bytes(body)
                            candidate = extract(target, ocr, pages)
                    verified.append(
                        {
                            "url": url,
                            "access_state": page["access_state"],
                            **compare(result, candidate),
                        }
                    )
                except WebError as error:
                    errors.append({"url": url, "error": str(error)})
            result.update(
                queries_disclosed=len(selected),
                candidates=list(candidates.values()),
                verified_candidates=verified,
                errors=errors,
                partial=bool(errors),
            )
        return result

    execute("doc", action, fmt, save_dir, no_save, report)


@app.command()
def image(
    path: str,
    online: bool = typer.Option(False, "--online", "-o"),
    text_search: bool = typer.Option(
        False,
        "--text-search",
        "-t",
        help="Explicitly search locally OCR-extracted words as text candidates",
    ),
    engines: str = typer.Option("yandex", "--engines", "-e"),
    limit: int = typer.Option(10, "--limit", "-n"),
    fmt: str = typer.Option("table", "--format", "-f"),
    save_dir: Path | None = typer.Option(None, "--save-dir", "-S"),
    no_save: bool = typer.Option(False, "--no-save", "-N"),
    report: Path | None = typer.Option(None, "--report", "-R"),
):
    """Inspect EXIF locally; --online explicitly uploads pixels without original EXIF."""

    def action():
        if urlsplit(path).scheme in {"http", "https"}:
            _, _, body = Session(path).get(path)
            with tempfile.TemporaryDirectory(prefix="web-image-input-") as folder:
                local = Path(folder) / "image.bin"
                local.write_bytes(body)
                return asyncio.run(
                    inspect(local, online, engines.split(","), limit, text_search)
                )
        return asyncio.run(
            inspect(path, online, engines.split(","), limit, text_search)
        )

    execute(
        "image",
        action,
        fmt,
        save_dir,
        no_save,
        report,
    )


@app.command()
def audio(
    path: Path | None = typer.Argument(None),
    record: float | None = typer.Option(None, "--record", "-r"),
    mode: str = typer.Option("recording", "--mode", "-m"),
    duration: float = typer.Option(12, "--duration", "-d"),
    source: str = typer.Option("default", "--source", "-s"),
    offset: float = typer.Option(0, "--offset", "-O"),
    fmt: str = typer.Option("table", "--format", "-f"),
    no_save: bool = typer.Option(False, "--no-save", "-N"),
):
    """Free fingerprint identification; hum attempts have no melody-recognition guarantee."""
    execute(
        "audio",
        lambda: identify(path, record, mode, duration, source, offset),
        fmt,
        no_save=no_save,
    )


@app.command()
def similar(
    url: str,
    engines: str | None = typer.Option(None, "--engines", "-e"),
    limit: int = typer.Option(10, "--limit", "-n"),
    fmt: str = typer.Option("table", "--format", "-f"),
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


@app.command()
def doctor(
    live: bool = typer.Option(False, "--live", "-l"),
    fmt: str = typer.Option("table", "--format", "-f"),
):
    def action():
        result = asyncio.run(
            diagnose(frontend="http://127.0.0.1:8080", live=live, engines="bing")
        )
        if result["state"] == "failed":
            raise WebError(json.dumps(result))
        return {**result, "partial": result["state"] == "degraded"}

    execute("doctor", action, fmt, no_save=True)


@app.command()
def capabilities(fmt: str = typer.Option("table", "--format", "-f")):
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


@app.command()
def setup():
    typer.echo(initialize())


@app.command()
def purge(yes: bool = typer.Option(False, "--yes", "-y")):
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


@maps.command("search")
def map_search(
    query: str,
    params: str | None = typer.Option(None, "--params", "-P"),
    fmt: str = typer.Option("table", "--format", "-f"),
):
    execute(
        "map-search",
        lambda: {
            "result": Maps(settings()).search(query, json_object(params)),
            "attribution": "OpenStreetMap contributors / ODbL",
        },
        fmt,
    )


@maps.command("query")
def map_query(query: str, fmt: str = typer.Option("json", "--format", "-f")):
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


@maps.command("route")
def map_route(
    vertices: str,
    profile: str | None = typer.Option(None, "--profile", "-p"),
    params: str | None = typer.Option(None, "--params", "-P"),
    fmt: str = typer.Option("json", "--format", "-f"),
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


@maps.command("request")
def map_request(
    endpoint: str,
    method: str = typer.Option("GET", "--method", "-X"),
    params: str | None = typer.Option(None, "--params", "-P"),
    body: str | None = typer.Option(None, "--body", "-b"),
    fmt: str = typer.Option("json", "--format", "-f"),
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


@app.command()
def archive(
    url: str,
    params: str | None = typer.Option(None, "--params", "-P"),
    fmt: str = typer.Option("json", "--format", "-f"),
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
