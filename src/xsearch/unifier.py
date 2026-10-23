"""Core multi-network unifier engine for xsearch with regex and OSINT extraction."""

import asyncio
import csv
import json
import re
import shutil
import subprocess
import sys
import urllib.parse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table

from .config import CONFIG

# Regex patterns for intelligence extraction
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{2,4}[-.\s]?\d{2,9}")


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str
    engine: str
    category: str
    timestamp: str
    score: float = 0.0
    extracted_emails: List[str] = field(default_factory=list)
    extracted_phones: List[str] = field(default_factory=list)


def extract_osint_entities(text: str) -> Dict[str, List[str]]:
    """Extracts email addresses and phone numbers from arbitrary text."""
    emails = list(set(EMAIL_REGEX.findall(text)))
    # Filter phone numbers to avoid tiny digit sequences
    raw_phones = PHONE_REGEX.findall(text)
    phones = list(
        set(
            p.strip()
            for p in raw_phones
            if len(re.sub(r"\D", "", p)) >= 8 and len(re.sub(r"\D", "", p)) <= 15
        )
    )
    return {"emails": emails, "phones": phones}


class SurfaceSearcher:
    """Queries local SearXNG metasearch instance with unlimited parameters."""

    def __init__(self, base_url: str = CONFIG.searxng_url):
        self.base_url = base_url.rstrip("/")

    async def get_engines(self) -> Dict[str, Any]:
        """Fetch all configured engines from SearXNG."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.base_url}/config")
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        return {}

    async def search(
        self,
        query: str,
        engines: Optional[str] = None,
        categories: Optional[str] = None,
        language: str = "all",
        page: int = 1,
        safe_search: int = 0,
        time_range: Optional[str] = None,
        limit: int = 20,
        timeout: float = CONFIG.default_timeout_s,
    ) -> List[SearchResult]:
        params: Dict[str, Any] = {
            "q": query,
            "format": "json",
            "pageno": page,
            "safesearch": safe_search,
            "language": language,
        }
        if engines:
            params["engines"] = engines
        if categories:
            params["categories"] = categories
        if time_range:
            params["time_range"] = time_range

        results: List[SearchResult] = []
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(f"{self.base_url}/search", params=params)
                resp.raise_for_status()
                data = resp.json()

            raw_results = data.get("results", [])
            for r in raw_results[:limit]:
                title = r.get("title", "")
                snippet = r.get("content", "")
                full_text = f"{title} {snippet}"
                entities = extract_osint_entities(full_text)

                results.append(
                    SearchResult(
                        title=title,
                        url=r.get("url", ""),
                        snippet=snippet,
                        source=f"searxng:{r.get('engine', 'unknown')}",
                        engine=r.get("engine", "unknown"),
                        category="surface",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        extracted_emails=entities["emails"],
                        extracted_phones=entities["phones"],
                    )
                )
        except Exception as e:
            if CONFIG.debug:
                print(f"[SurfaceSearcher] Error: {e}", file=sys.stderr)
        return results


class OnionSearcher:
    """Queries dark web .onion engines through SOCKS5, torsocks, or oniux."""

    def __init__(
        self,
        tor_proxy: str = CONFIG.tor_proxy,
        transport: str = "direct",
    ):
        self.tor_proxy = tor_proxy
        self.transport = transport
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0"
        }

    def _search_tor66_direct(
        self, query: str, limit: int = 20, timeout: float = CONFIG.default_timeout_s
    ) -> List[SearchResult]:
        results: List[SearchResult] = []
        proxies = {"http": self.tor_proxy, "https": self.tor_proxy}
        url = (
            f"http://tor66sewebgixwhcqfnp5inzp5x5uohhdy3kvtnyfxc2e5mxiuh34iid.onion/search"
            f"?q={urllib.parse.quote(query)}&sorttype=rel&page=1"
        )

        try:
            r = requests.get(
                url,
                proxies=proxies,
                headers=self.headers,
                timeout=timeout,
            )
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                for b in soup.find_all("b"):
                    a = b.find("a")
                    if a and a.get("href"):
                        href = a.get("href", "")
                        title = a.get_text(strip=True)
                        if (
                            "tor66sewebgixwhcqfnp5inzp5x5uohhdy3kvtnyfxc2e5mxiuh34iid.onion"
                            not in href
                            and ".onion" in href
                            and len(title) > 1
                        ):
                            entities = extract_osint_entities(title)
                            results.append(
                                SearchResult(
                                    title=title,
                                    url=href,
                                    snippet="",
                                    source="onion:tor66",
                                    engine="tor66",
                                    category="onion",
                                    timestamp=datetime.now(timezone.utc).isoformat(),
                                    extracted_emails=entities["emails"],
                                    extracted_phones=entities["phones"],
                                )
                            )
                            if len(results) >= limit:
                                break
        except Exception as e:
            if CONFIG.debug:
                print(f"[OnionSearcher:tor66] Error: {e}", file=sys.stderr)
        return results

    def _search_with_wrapper(
        self, query: str, limit: int = 20, timeout: float = CONFIG.default_timeout_s
    ) -> List[SearchResult]:
        """Executes search inside oniux or torsocks wrapper if requested."""
        wrapper = shutil.which(self.transport)
        if not wrapper:
            return self._search_tor66_direct(query, limit=limit, timeout=timeout)

        url = (
            f"http://tor66sewebgixwhcqfnp5inzp5x5uohhdy3kvtnyfxc2e5mxiuh34iid.onion/search"
            f"?q={urllib.parse.quote(query)}&sorttype=rel&page=1"
        )

        cmd = [wrapper, "curl", "-s", "-A", self.headers["User-Agent"], url]
        results: List[SearchResult] = []
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
            if proc.returncode == 0:
                soup = BeautifulSoup(proc.stdout, "html.parser")
                for b in soup.find_all("b"):
                    a = b.find("a")
                    if a and a.get("href"):
                        href = a.get("href", "")
                        title = a.get_text(strip=True)
                        if (
                            "tor66sewebgixwhcqfnp5inzp5x5uohhdy3kvtnyfxc2e5mxiuh34iid.onion"
                            not in href
                            and ".onion" in href
                            and len(title) > 1
                        ):
                            entities = extract_osint_entities(title)
                            results.append(
                                SearchResult(
                                    title=title,
                                    url=href,
                                    snippet="",
                                    source=f"onion:tor66[{self.transport}]",
                                    engine="tor66",
                                    category="onion",
                                    timestamp=datetime.now(timezone.utc).isoformat(),
                                    extracted_emails=entities["emails"],
                                    extracted_phones=entities["phones"],
                                )
                            )
                            if len(results) >= limit:
                                break
        except Exception as e:
            if CONFIG.debug:
                print(f"[OnionSearcher:{self.transport}] Error: {e}", file=sys.stderr)
        return results

    async def search(
        self, query: str, limit: int = 20, timeout: float = CONFIG.default_timeout_s
    ) -> List[SearchResult]:
        if self.transport in ["oniux", "torsocks"]:
            return await asyncio.to_thread(
                self._search_with_wrapper, query, limit, timeout
            )
        return await asyncio.to_thread(
            self._search_tor66_direct, query, limit, timeout
        )


class I2PSearcher:
    """Interrogates I2P network (eepsites) via HTTP proxy."""

    def __init__(self, i2p_proxy: str = CONFIG.i2p_proxy):
        self.proxy = i2p_proxy

    async def search(
        self, query: str, limit: int = 20, timeout: float = CONFIG.default_timeout_s
    ) -> List[SearchResult]:
        return []


def filter_results(
    results: List[SearchResult],
    site: Optional[str] = None,
    regex_pattern: Optional[str] = None,
    must_have_email: bool = False,
    must_have_phone: bool = False,
) -> List[SearchResult]:
    """Applies client-side surgical filtering on site domains, regex, emails, and phones."""
    filtered = results

    if site:
        target_site = site.lower().strip()
        filtered = [r for r in filtered if target_site in r.url.lower()]

    if regex_pattern:
        try:
            compiled = re.compile(regex_pattern, re.IGNORECASE)
            filtered = [
                r
                for r in filtered
                if compiled.search(r.title) or compiled.search(r.snippet) or compiled.search(r.url)
            ]
        except re.error as e:
            print(f"[Warning] Invalid regex '{regex_pattern}': {e}", file=sys.stderr)

    if must_have_email:
        filtered = [r for r in filtered if len(r.extracted_emails) > 0]

    if must_have_phone:
        filtered = [r for r in filtered if len(r.extracted_phones) > 0]

    return filtered


def deduplicate(results: List[SearchResult]) -> List[SearchResult]:
    """Deterministic deduplication based on normalized URL."""
    seen = set()
    unique: List[SearchResult] = []
    for r in results:
        norm_url = (
            r.url.split("#")[0].split("?")[0].lower().replace("www.", "").rstrip("/")
        )
        if norm_url not in seen:
            seen.add(norm_url)
            unique.append(r)
    return unique


def render_rich_table(
    results: List[SearchResult],
    title_prefix: str = "Search Results",
    show_intel: bool = False,
):
    """Renders results in a stylish Rich terminal table with optional OSINT data."""
    console = Console()
    table = Table(
        title=f"🔎 [bold cyan]xsearch[/bold cyan] — {title_prefix} ({len(results)} matches)",
        show_header=True,
        header_style="bold magenta",
        expand=True,
    )
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Tier", style="bold", width=9)
    table.add_column("Engine / Source", style="green", width=18)
    table.add_column("Title & Excerpt", style="white", ratio=3)
    table.add_column("URL", style="blue underline", ratio=2)

    if show_intel:
        table.add_column("Intel (Email/Phone)", style="bold yellow", ratio=1)

    for idx, r in enumerate(results, 1):
        tier_color = "cyan" if r.category == "surface" else "yellow"
        tier_badge = f"[{tier_color}]{r.category.upper()}[/{tier_color}]"

        content = f"[bold]{r.title}[/bold]"
        if r.snippet:
            snippet_cleaned = r.snippet.replace("\n", " ").strip()
            content += f"\n[dim]{snippet_cleaned[:180]}...[/dim]"

        if show_intel:
            intel_parts = []
            if r.extracted_emails:
                intel_parts.append(f"✉️ {', '.join(r.extracted_emails)}")
            if r.extracted_phones:
                intel_parts.append(f"📞 {', '.join(r.extracted_phones)}")
            intel_cell = "\n".join(intel_parts) if intel_parts else "[dim]-[/dim]"
            table.add_row(str(idx), tier_badge, r.source, content, r.url, intel_cell)
        else:
            table.add_row(str(idx), tier_badge, r.source, content, r.url)

    console.print(table)


def output_results(
    results: List[SearchResult],
    output_format: str,
    query: str = "",
    show_intel: bool = False,
):
    """Outputs results in JSON, CSV, Markdown, or Rich Table."""
    if output_format == "json":
        print(json.dumps([asdict(r) for r in results], indent=2, ensure_ascii=False))
    elif output_format == "csv":
        if results:
            writer = csv.DictWriter(
                sys.stdout, fieldnames=list(SearchResult.__dataclass_fields__.keys())
            )
            writer.writeheader()
            for r in results:
                writer.writerow(asdict(r))
    elif output_format == "md":
        for r in results:
            badge = f"[{r.category.upper()}]"
            print(f"- {badge} **[{r.title}]({r.url})** (`{r.source}`)")
            if r.snippet:
                print(f"  {r.snippet}")
            if r.extracted_emails:
                print(f"  *Emails:* {', '.join(r.extracted_emails)}")
            if r.extracted_phones:
                print(f"  *Phones:* {', '.join(r.extracted_phones)}")
            print()
    elif output_format == "table":
        render_rich_table(
            results, title_prefix=f"Query: '{query}'", show_intel=show_intel
        )
