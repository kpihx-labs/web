"""Read-only end-to-end health checks; never restart services during a query."""

import asyncio
import json

import typer
from rich.console import Console
from rich.table import Table

from .backend import BackendError, SurfaceSearcher
from .user_config import settings


async def diagnose(
    backend=None,
    frontend=None,
    live=False,
    query="Python programming language",
    engines=None,
):
    checks = []
    backend = SurfaceSearcher(backend)
    endpoints = [("backend", backend)]
    if frontend:
        endpoints.append(("frontend", SurfaceSearcher(frontend)))
    for name, searcher in endpoints:
        try:
            config = await searcher.get_engines()
            checks.append(
                {
                    "check": name,
                    "state": "healthy",
                    "endpoint": searcher.base_url,
                    "transport": searcher.channel,
                    "engines": len(config["engines"]),
                }
            )
        except BackendError as error:
            state = (
                "degraded"
                if name == "frontend"
                and backend.socket_path
                and checks[0]["state"] == "healthy"
                else "failed"
            )
            checks.append(
                {
                    "check": name,
                    "state": state,
                    "code": error.code,
                    "detail": str(error),
                }
            )
    if live and checks[0]["state"] == "healthy":
        try:
            results = await backend.search(query, engines=engines, limit=3)
            if not results:
                raise BackendError(
                    "CANARY_EMPTY",
                    backend.base_url,
                    "Expected a known public query to return results",
                )
            checks.append(
                {
                    "check": "live-search",
                    "state": "degraded" if backend.unresponsive_engines else "healthy",
                    "results": len(results),
                    "upstream_issues": backend.unresponsive_engines,
                }
            )
        except BackendError as error:
            checks.append(
                {
                    "check": "live-search",
                    "state": "failed",
                    "code": error.code,
                    "detail": str(error),
                }
            )
    code = (
        2
        if any(c["state"] == "failed" for c in checks)
        else 3
        if any(c["state"] == "degraded" for c in checks)
        else 0
    )
    return {
        "state": {0: "healthy", 2: "failed", 3: "degraded"}[code],
        "exit_code": code,
        "checks": checks,
    }


def doctor(
    live: bool = typer.Option(
        False,
        "--live",
        "-l",
        help="Make an external search canary; otherwise local readiness only.",
    ),
    backend: str | None = typer.Option(None, "--backend", "-b"),
    frontend: str | None = typer.Option(None, "--frontend", "-F"),
    query: str = typer.Option("Python programming language", "--query", "-q"),
    engines: str | None = typer.Option(None, "--engines", "-e"),
    fmt: str = typer.Option("table", "--format", "-f"),
):
    """Verify backend catalogue, frontend and optional live search. Never mutate networking."""
    result = asyncio.run(
        diagnose(
            backend,
            frontend or settings().get("searxng_frontend", "http://127.0.0.1:8080"),
            live,
            query,
            engines,
        )
    )
    if fmt == "json":
        print(json.dumps(result, indent=2))
    else:
        table = Table(title="web pipeline health")
        for heading in ("Check", "State", "Details"):
            table.add_column(heading)
        for check in result["checks"]:
            table.add_row(
                check["check"],
                check["state"],
                json.dumps(
                    {k: v for k, v in check.items() if k not in {"check", "state"}}
                ),
            )
        Console().print(table)
    raise typer.Exit(result["exit_code"])
