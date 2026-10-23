"""CLI entrypoint using Typer and Rich with comprehensive options."""

import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .unifier import (
    I2PSearcher,
    OnionSearcher,
    SurfaceSearcher,
    deduplicate,
    filter_results,
    output_results,
)

app = typer.Typer(
    name="xsearch",
    help="⚡ Sovereign ultra-flexible multi-network search CLI (Surface, Tor .onion, I2P).",
    add_completion=False,
)
console = Console()


@app.command()
def search(
    query: Optional[str] = typer.Argument(None, help="Search query string"),
    # Network Selection
    surface: bool = typer.Option(
        True,
        "-s",
        "--surface/--no-surface",
        help="Query Surface Web via SearXNG",
    ),
    onion: bool = typer.Option(
        False,
        "-o",
        "--onion/--no-onion",
        help="Query Dark Web (.onion) via Tor",
    ),
    i2p: bool = typer.Option(
        False,
        "-i",
        "--i2p/--no-i2p",
        help="Query I2P Network (eepsites)",
    ),
    # Surgical Filters
    engines: Optional[str] = typer.Option(
        None,
        "-e",
        "--engines",
        help="Comma-separated engine list (e.g. brave,bing,wikipedia,github,ahmia)",
    ),
    categories: Optional[str] = typer.Option(
        None,
        "-c",
        "--categories",
        help="Category filter (e.g. general, it, science, files)",
    ),
    site: Optional[str] = typer.Option(
        None,
        "-d",
        "--site",
        help="Domain filter (e.g. github.com, reddit.com, .onion)",
    ),
    regex: Optional[str] = typer.Option(
        None,
        "-r",
        "--regex",
        help="Regex filter on title/snippet/url",
    ),
    has_email: bool = typer.Option(
        False,
        "--has-email",
        help="Filter only results that contain email addresses",
    ),
    has_phone: bool = typer.Option(
        False,
        "--has-phone",
        help="Filter only results that contain phone numbers",
    ),
    show_intel: bool = typer.Option(
        False,
        "--intel",
        help="Display extracted emails and phone numbers in dedicated column",
    ),
    # Pagination & Limits
    limit: int = typer.Option(
        20,
        "-n",
        "--limit",
        help="Maximum results per network category",
    ),
    page: int = typer.Option(
        1,
        "-p",
        "--page",
        help="Result page number",
    ),
    # Moderation & Locales
    safe_search: int = typer.Option(
        0,
        "-m",
        "--safe-search",
        help="SafeSearch level: 0 (Off / Uncensored), 1 (Moderate), 2 (Strict)",
    ),
    lang: str = typer.Option(
        "all",
        "-l",
        "--lang",
        help="Language filter (e.g. fr, en, all)",
    ),
    time_range: Optional[str] = typer.Option(
        None,
        "-t",
        "--time-range",
        help="Time filter: day, week, month, year",
    ),
    # Transport & Isolation
    transport: str = typer.Option(
        "direct",
        "--transport",
        help="Tor transport isolation: direct (SOCKS5), torsocks, or oniux (kernel namespaces)",
    ),
    timeout: float = typer.Option(
        30.0,
        "--timeout",
        help="Network timeout in seconds",
    ),
    # Output formatting
    format_type: str = typer.Option(
        "table",
        "-f",
        "--format",
        help="Output format: table, json, csv, md",
    ),
    dedup: bool = typer.Option(
        True,
        "--dedup/--no-dedup",
        help="Deterministic URL deduplication",
    ),
    # Engine discovery
    list_engines: bool = typer.Option(
        False,
        "--list-engines",
        help="List all active SearXNG engines and exit",
    ),
):
    """Executes multi-network search queries."""
    if list_engines:
        asyncio.run(show_engines())
        return

    if not query:
        console.print("[bold red]Error:[/bold red] Missing search query. Use 'xsearch --help' for options.")
        raise typer.Exit(1)

    asyncio.run(
        run_search(
            query=query,
            surface=surface,
            onion=onion,
            i2p=i2p,
            engines=engines,
            categories=categories,
            site=site,
            regex=regex,
            has_email=has_email,
            has_phone=has_phone,
            show_intel=show_intel,
            limit=limit,
            page=page,
            safe_search=safe_search,
            lang=lang,
            time_range=time_range,
            transport=transport,
            timeout=timeout,
            format_type=format_type,
            dedup=dedup,
        )
    )


async def show_engines():
    """Lists available engines directly from SearXNG."""
    surface = SurfaceSearcher()
    config = await surface.get_engines()
    engines_data = config.get("engines", [])

    table = Table(
        title="🌐 [bold cyan]xsearch[/bold cyan] — Available Upstream Engines",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Engine", style="bold green")
    table.add_column("Categories", style="yellow")
    table.add_column("Enabled", style="cyan")

    for eng in engines_data:
        name = eng.get("name", "")
        cats = ", ".join(eng.get("categories", []))
        enabled = "✓ Yes" if eng.get("enabled", True) else "✗ No"
        table.add_row(name, cats, enabled)

    console.print(table)


async def run_search(
    query: str,
    surface: bool,
    onion: bool,
    i2p: bool,
    engines: Optional[str],
    categories: Optional[str],
    site: Optional[str],
    regex: Optional[str],
    has_email: bool,
    has_phone: bool,
    show_intel: bool,
    limit: int,
    page: int,
    safe_search: int,
    lang: str,
    time_range: Optional[str],
    transport: str,
    timeout: float,
    format_type: str,
    dedup: bool,
):
    tasks = []

    if surface:
        s_searcher = SurfaceSearcher()
        tasks.append(
            s_searcher.search(
                query=query,
                engines=engines,
                categories=categories,
                language=lang,
                page=page,
                safe_search=safe_search,
                time_range=time_range,
                limit=limit,
                timeout=timeout,
            )
        )

    if onion:
        o_searcher = OnionSearcher(transport=transport)
        tasks.append(o_searcher.search(query=query, limit=limit, timeout=timeout))

    if i2p:
        i_searcher = I2PSearcher()
        tasks.append(i_searcher.search(query=query, limit=limit, timeout=timeout))

    gathered = await asyncio.gather(*tasks, return_exceptions=True)
    all_results = []
    for res in gathered:
        if isinstance(res, list):
            all_results.extend(res)
        elif isinstance(res, Exception):
            if format_type == "table":
                console.print(f"[bold yellow]Warning:[/bold yellow] Sub-searcher error: {res}")

    if dedup:
        all_results = deduplicate(all_results)

    # Client-side surgical filtering
    all_results = filter_results(
        all_results,
        site=site,
        regex_pattern=regex,
        must_have_email=has_email,
        must_have_phone=has_phone,
    )

    output_results(all_results, format_type, query=query, show_intel=show_intel)


def main():
    app()


if __name__ == "__main__":
    main()
