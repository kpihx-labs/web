"""CLI entrypoint using Typer and Rich with subcommands (search, fetch, similar, crawl, engines)."""

import asyncio
import urllib.parse
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table

from .unifier import (
    AsyncCrawler,
    ContentFetcher,
    I2PSearcher,
    OnionSearcher,
    SurfaceSearcher,
    deduplicate,
    filter_results,
    output_crawl_result,
    output_fetch_result,
    output_results,
    parse_cookie_file,
    parse_custom_headers,
)

app = typer.Typer(
    name="xsearch",
    help="⚡ Sovereign ultra-flexible multi-network search & crawl CLI (Surface, Tor .onion, I2P).",
    add_completion=False,
)
console = Console()


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query string"),
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
    # Transport & Isolation & Bridge
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
    cookie_file: Optional[str] = typer.Option(
        None,
        "-C",
        "--cookie-file",
        help="Path to cookies file (JSON or Netscape format from browser-proxy)",
    ),
    header: Optional[List[str]] = typer.Option(
        None,
        "-H",
        "--header",
        help="Custom header in 'Key: Value' format (can be specified multiple times)",
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
):
    """Executes multi-network search queries across Surface, Tor, and I2P."""
    cookies_map = parse_cookie_file(cookie_file) if cookie_file else None
    headers_map = parse_custom_headers(header)

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
            custom_cookies=cookies_map,
            custom_headers=headers_map,
        )
    )


@app.command()
def fetch(
    url: str = typer.Argument(..., help="Clearnet or .onion URL to fetch"),
    format_type: str = typer.Option(
        "text",
        "-f",
        "--format",
        help="Output format: text, json, md",
    ),
    timeout: float = typer.Option(
        30.0,
        "--timeout",
        help="Network timeout in seconds",
    ),
    cookie_file: Optional[str] = typer.Option(
        None,
        "-C",
        "--cookie-file",
        help="Path to cookies file (JSON or Netscape format from browser-proxy)",
    ),
    header: Optional[List[str]] = typer.Option(
        None,
        "-H",
        "--header",
        help="Custom header in 'Key: Value' format (repeatable)",
    ),
    proxy: Optional[str] = typer.Option(
        None,
        "--proxy",
        help="Override proxy URL (e.g. http://127.0.0.1:8080 or socks5h://...)",
    ),
):
    """Fetches clean text and extracts OSINT intelligence (emails/phones) from any URL or .onion."""
    cookies_map = parse_cookie_file(cookie_file) if cookie_file else None
    headers_map = parse_custom_headers(header)

    fetcher = ContentFetcher(
        timeout=timeout,
        proxy_override=proxy,
        cookies=cookies_map,
        headers=headers_map,
    )
    result = asyncio.run(fetcher.fetch(url))
    output_fetch_result(result, format_type)


@app.command()
def crawl(
    url: str = typer.Argument(..., help="Base URL or hidden service (.onion) to crawl recursively"),
    depth: int = typer.Option(
        1,
        "-D",
        "--depth",
        help="Max recursive crawling depth (0 = single page, 1 = direct links, 2 = nested)",
    ),
    max_pages: int = typer.Option(
        20,
        "-n",
        "--max-pages",
        help="Maximum pages to visit and process",
    ),
    stay_domain: bool = typer.Option(
        True,
        "--stay-domain/--cross-domain",
        help="Stay strictly on the same root hostname (default: stay on domain)",
    ),
    download_dir: Optional[str] = typer.Option(
        None,
        "--download-dir",
        help="Local directory path to save clean page dumps and assets",
    ),
    cookie_file: Optional[str] = typer.Option(
        None,
        "-C",
        "--cookie-file",
        help="Path to cookies file from browser-proxy",
    ),
    header: Optional[List[str]] = typer.Option(
        None,
        "-H",
        "--header",
        help="Custom header in 'Key: Value' format (repeatable)",
    ),
    proxy: Optional[str] = typer.Option(
        None,
        "--proxy",
        help="Override proxy URL",
    ),
    timeout: float = typer.Option(
        20.0,
        "--timeout",
        help="Per-page request timeout in seconds",
    ),
    format_type: str = typer.Option(
        "table",
        "-f",
        "--format",
        help="Output format: table, json, md",
    ),
):
    """Recursively crawls websites or hidden services with link queueing, OSINT scraping, and optional downloads."""
    cookies_map = parse_cookie_file(cookie_file) if cookie_file else None
    headers_map = parse_custom_headers(header)

    crawler = AsyncCrawler(
        base_url=url,
        max_depth=depth,
        max_pages=max_pages,
        stay_domain=stay_domain,
        timeout=timeout,
        proxy_override=proxy,
        cookies=cookies_map,
        headers=headers_map,
        download_dir=download_dir,
    )

    console.print(f"[dim]Initiating recursive crawl on '{url}' (depth={depth}, max_pages={max_pages})...[/dim]")
    result = asyncio.run(crawler.crawl())
    output_crawl_result(result, format_type)


@app.command()
def similar(
    url: str = typer.Argument(..., help="Target URL to find similar websites/services for"),
    limit: int = typer.Option(
        10,
        "-n",
        "--limit",
        help="Maximum similar results to return",
    ),
    format_type: str = typer.Option(
        "table",
        "-f",
        "--format",
        help="Output format: table, json, csv, md",
    ),
):
    """Finds alternative and related platforms for a target website or URL."""
    parsed = urllib.parse.urlparse(url)
    target_host = parsed.netloc or parsed.path.split("/")[0]

    domain_clean = target_host.replace("www.", "").rstrip("/")
    service_name = domain_clean.split(".")[0]

    query = f"alternative to {service_name} OR related {domain_clean}"

    console.print(f"[dim]Discovering platforms similar and related to '{domain_clean}'...[/dim]")
    asyncio.run(
        run_search(
            query=query,
            surface=True,
            onion=False,
            i2p=False,
            engines="brave,bing,duckduckgo",
            categories=None,
            site=None,
            regex=None,
            has_email=False,
            has_phone=False,
            show_intel=False,
            limit=limit,
            page=1,
            safe_search=0,
            lang="all",
            time_range=None,
            transport="direct",
            timeout=20.0,
            format_type=format_type,
            dedup=True,
        )
    )


@app.command(name="engines")
def list_engines():
    """Lists all configured and available engines from SearXNG."""
    asyncio.run(show_engines())


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
    custom_cookies: Optional[dict] = None,
    custom_headers: Optional[dict] = None,
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
                custom_headers=custom_headers,
            )
        )

    if onion:
        o_searcher = OnionSearcher(transport=transport)
        tasks.append(
            o_searcher.search(
                query=query,
                limit=limit,
                timeout=timeout,
                custom_headers=custom_headers,
                custom_cookies=custom_cookies,
            )
        )

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
