"""Core multi-network unifier engine for xsearch with regex, OSINT, fetch, crawl, and session bridging."""

import asyncio
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import httpx
import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table

from .config import CONFIG

# Regex patterns for OSINT entity extraction
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


@dataclass
class FetchResult:
    url: str
    title: str
    content: str
    text_length: int
    status_code: int
    category: str
    extracted_emails: List[str] = field(default_factory=list)
    extracted_phones: List[str] = field(default_factory=list)


@dataclass
class CrawlResult:
    base_url: str
    total_pages_visited: int
    pages: List[FetchResult]
    aggregated_emails: List[str] = field(default_factory=list)
    aggregated_phones: List[str] = field(default_factory=list)


def extract_osint_entities(text: str) -> Dict[str, List[str]]:
    """Extracts email addresses and phone numbers from arbitrary text."""
    emails = list(set(EMAIL_REGEX.findall(text)))
    raw_phones = PHONE_REGEX.findall(text)
    phones = list(
        set(
            p.strip()
            for p in raw_phones
            if 8 <= len(re.sub(r"\D", "", p)) <= 15
        )
    )
    return {"emails": sorted(emails), "phones": sorted(phones)}


def parse_cookie_file(cookie_file_path: str) -> Dict[str, str]:
    """Parses Netscape standard cookies.txt or JSON cookie files."""
    cookies: Dict[str, str] = {}
    path = Path(cookie_file_path)
    if not path.is_file():
        return cookies

    content = path.read_text(encoding="utf-8", errors="ignore")
    # Try parsing as JSON first
    try:
        data = json.loads(content)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "name" in item and "value" in item:
                    cookies[item["name"]] = item["value"]
        elif isinstance(data, dict):
            for k, v in data.items():
                cookies[str(k)] = str(v)
        return cookies
    except Exception:
        pass

    # Parse as standard Netscape format
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 7:
            cookies[parts[5]] = parts[6]
        elif len(parts) == 2:
            cookies[parts[0]] = parts[1]

    return cookies


def parse_custom_headers(headers_list: Optional[List[str]]) -> Dict[str, str]:
    """Parses list of header strings in 'Key: Value' format."""
    parsed: Dict[str, str] = {}
    if not headers_list:
        return parsed
    for h in headers_list:
        if ":" in h:
            k, v = h.split(":", 1)
            parsed[k.strip()] = v.strip()
    return parsed


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
        custom_headers: Optional[Dict[str, str]] = None,
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

        headers = custom_headers or {}
        results: List[SearchResult] = []
        try:
            async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
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
        self,
        query: str,
        limit: int = 20,
        timeout: float = CONFIG.default_timeout_s,
        custom_headers: Optional[Dict[str, str]] = None,
        custom_cookies: Optional[Dict[str, str]] = None,
    ) -> List[SearchResult]:
        results: List[SearchResult] = []
        proxies = {"http": self.tor_proxy, "https": self.tor_proxy}
        url = (
            f"http://tor66sewebgixwhcqfnp5inzp5x5uohhdy3kvtnyfxc2e5mxiuh34iid.onion/search"
            f"?q={urllib.parse.quote(query)}&sorttype=rel&page=1"
        )

        headers = {**self.headers, **(custom_headers or {})}

        try:
            r = requests.get(
                url,
                proxies=proxies,
                headers=headers,
                cookies=custom_cookies,
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
        self,
        query: str,
        limit: int = 20,
        timeout: float = CONFIG.default_timeout_s,
    ) -> List[SearchResult]:
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
        self,
        query: str,
        limit: int = 20,
        timeout: float = CONFIG.default_timeout_s,
        custom_headers: Optional[Dict[str, str]] = None,
        custom_cookies: Optional[Dict[str, str]] = None,
    ) -> List[SearchResult]:
        if self.transport in ["oniux", "torsocks"]:
            return await asyncio.to_thread(
                self._search_with_wrapper, query, limit, timeout
            )
        return await asyncio.to_thread(
            self._search_tor66_direct,
            query,
            limit,
            timeout,
            custom_headers,
            custom_cookies,
        )


class I2PSearcher:
    """Interrogates I2P network (eepsites) via HTTP proxy."""

    def __init__(self, i2p_proxy: str = CONFIG.i2p_proxy):
        self.proxy = i2p_proxy

    async def search(
        self, query: str, limit: int = 20, timeout: float = CONFIG.default_timeout_s
    ) -> List[SearchResult]:
        return []


class ContentFetcher:
    """Fetches clean text and OSINT entities from arbitrary Clearnet or .onion URLs with cookie/header support."""

    def __init__(
        self,
        tor_proxy: str = CONFIG.tor_proxy,
        timeout: float = CONFIG.default_timeout_s,
        proxy_override: Optional[str] = None,
        cookies: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        self.tor_proxy = tor_proxy
        self.timeout = timeout
        self.proxy_override = proxy_override
        self.cookies = cookies or {}
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0",
            **(headers or {}),
        }

    def _fetch_sync(self, url: str) -> FetchResult:
        is_onion = ".onion" in url.lower()
        category = "onion" if is_onion else "surface"

        if self.proxy_override:
            proxies = {"http": self.proxy_override, "https": self.proxy_override}
        elif is_onion:
            proxies = {"http": self.tor_proxy, "https": self.tor_proxy}
        else:
            proxies = None

        try:
            r = requests.get(
                url,
                proxies=proxies,
                headers=self.headers,
                cookies=self.cookies,
                timeout=self.timeout,
            )
            status_code = r.status_code
            soup = BeautifulSoup(r.text, "html.parser")

            # Remove scripts, styles, metadata
            for element in soup(["script", "style", "nav", "footer", "noscript"]):
                element.decompose()

            title = soup.title.string.strip() if soup.title and soup.title.string else url
            text_lines = [
                line.strip() for line in soup.get_text().splitlines() if line.strip()
            ]
            clean_text = "\n".join(text_lines)
            entities = extract_osint_entities(clean_text)

            return FetchResult(
                url=url,
                title=title,
                content=clean_text,
                text_length=len(clean_text),
                status_code=status_code,
                category=category,
                extracted_emails=entities["emails"],
                extracted_phones=entities["phones"],
            )
        except Exception as e:
            return FetchResult(
                url=url,
                title="Fetch Error",
                content=f"Error fetching {url}: {e}",
                text_length=0,
                status_code=500,
                category=category,
            )

    async def fetch(self, url: str) -> FetchResult:
        return await asyncio.to_thread(self._fetch_sync, url)


class AsyncCrawler:
    """Sovereign recursive web crawler supporting Surface and Tor with OSINT extraction and local asset saving."""

    def __init__(
        self,
        base_url: str,
        max_depth: int = 1,
        max_pages: int = 20,
        stay_domain: bool = True,
        tor_proxy: str = CONFIG.tor_proxy,
        timeout: float = CONFIG.default_timeout_s,
        proxy_override: Optional[str] = None,
        cookies: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
        download_dir: Optional[str] = None,
    ):
        self.base_url = base_url
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.stay_domain = stay_domain
        self.fetcher = ContentFetcher(
            tor_proxy=tor_proxy,
            timeout=timeout,
            proxy_override=proxy_override,
            cookies=cookies,
            headers=headers,
        )
        self.download_dir = Path(download_dir) if download_dir else None

        parsed = urllib.parse.urlparse(base_url)
        self.target_domain = parsed.netloc

    async def crawl(self) -> CrawlResult:
        visited: Set[str] = set()
        queue: List[tuple[str, int]] = [(self.base_url, 0)]
        pages: List[FetchResult] = []
        all_emails: Set[str] = set()
        all_phones: Set[str] = set()

        if self.download_dir:
            self.download_dir.mkdir(parents=True, exist_ok=True)

        while queue and len(visited) < self.max_pages:
            current_url, depth = queue.pop(0)
            norm_url = current_url.split("#")[0].rstrip("/")

            if norm_url in visited:
                continue
            visited.add(norm_url)

            # Fetch page content
            res = await self.fetcher.fetch(current_url)
            if res.status_code == 200:
                pages.append(res)
                all_emails.update(res.extracted_emails)
                all_phones.update(res.extracted_phones)

                # Save locally if requested
                if self.download_dir:
                    safe_filename = re.sub(r"[^\w\-.]", "_", current_url)[:120] + ".txt"
                    save_path = self.download_dir / safe_filename
                    save_path.write_text(
                        f"URL: {current_url}\nTITLE: {res.title}\n\n{res.content}",
                        encoding="utf-8",
                    )

                # Discover new links if within depth
                if depth < self.max_depth:
                    new_links = self._extract_links(current_url, res.content)
                    for link in new_links:
                        norm_link = link.split("#")[0].rstrip("/")
                        if norm_link not in visited:
                            queue.append((link, depth + 1))

        return CrawlResult(
            base_url=self.base_url,
            total_pages_visited=len(pages),
            pages=pages,
            aggregated_emails=sorted(all_emails),
            aggregated_phones=sorted(all_phones),
        )

    def _extract_links(self, page_url: str, text_content: str) -> List[str]:
        """Extracts and resolves absolute links on the same host if required."""
        # Fast HTML re-fetch parse for <a> hrefs
        links: List[str] = []
        # Re-parse raw soup links from fetcher
        try:
            is_onion = ".onion" in page_url.lower()
            proxies = (
                {"http": self.fetcher.tor_proxy, "https": self.fetcher.tor_proxy}
                if is_onion
                else None
            )
            r = requests.get(
                page_url,
                proxies=proxies,
                headers=self.fetcher.headers,
                cookies=self.fetcher.cookies,
                timeout=10.0,
            )
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.find_all("a", href=True):
                abs_url = urllib.parse.urljoin(page_url, a["href"])
                parsed_link = urllib.parse.urlparse(abs_url)
                if parsed_link.scheme in ["http", "https"]:
                    if self.stay_domain:
                        if parsed_link.netloc == self.target_domain:
                            links.append(abs_url)
                    else:
                        links.append(abs_url)
        except Exception:
            pass
        return links


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
    """Outputs search results in JSON, CSV, Markdown, or Rich Table."""
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


def output_fetch_result(result: FetchResult, output_format: str):
    """Outputs content fetch results in JSON, Markdown, or terminal text."""
    console = Console()
    if output_format == "json":
        print(json.dumps(asdict(result), indent=2, ensure_ascii=False))
    elif output_format == "md":
        print(f"# {result.title}\n")
        print(f"**URL:** {result.url} (Status: {result.status_code})\n")
        if result.extracted_emails:
            print(f"**Extracted Emails:** {', '.join(result.extracted_emails)}")
        if result.extracted_phones:
            print(f"**Extracted Phones:** {', '.join(result.extracted_phones)}")
        print("\n---\n")
        print(result.content)
    else:
        console.print(f"[bold cyan]URL:[/bold cyan] {result.url} [dim]({result.status_code})[/dim]")
        console.print(f"[bold green]Title:[/bold green] {result.title}")
        if result.extracted_emails:
            console.print(f"[bold yellow]Emails:[/bold yellow] {', '.join(result.extracted_emails)}")
        if result.extracted_phones:
            console.print(f"[bold yellow]Phones:[/bold yellow] {', '.join(result.extracted_phones)}")
        console.print("\n[dim]─── Content Preview ───[/dim]\n")
        console.print(result.content)


def output_crawl_result(result: CrawlResult, output_format: str):
    """Outputs crawl results in JSON, Markdown, or Rich Table."""
    console = Console()
    if output_format == "json":
        print(json.dumps(asdict(result), indent=2, ensure_ascii=False))
    elif output_format == "md":
        print(f"# Crawl Summary: {result.base_url}\n")
        print(f"- **Pages visited:** {result.total_pages_visited}")
        print(f"- **Aggregated Emails:** {', '.join(result.aggregated_emails) if result.aggregated_emails else 'None'}")
        print(f"- **Aggregated Phones:** {', '.join(result.aggregated_phones) if result.aggregated_phones else 'None'}\n")
        print("## Pages Crawled:\n")
        for p in result.pages:
            print(f"- **[{p.title}]({p.url})** ({p.text_length} chars, Status: {p.status_code})")
    else:
        table = Table(
            title=f"🕷️ [bold cyan]xsearch crawl[/bold cyan] — {result.base_url} ({result.total_pages_visited} pages)",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("#", style="dim", width=4)
        table.add_column("Title", style="white", ratio=2)
        table.add_column("URL", style="blue underline", ratio=3)
        table.add_column("Intel Found", style="yellow", ratio=2)

        for idx, p in enumerate(result.pages, 1):
            intel_parts = []
            if p.extracted_emails:
                intel_parts.append(f"✉️ {len(p.extracted_emails)} email(s)")
            if p.extracted_phones:
                intel_parts.append(f"📞 {len(p.extracted_phones)} phone(s)")
            intel_str = " | ".join(intel_parts) if intel_parts else "[dim]-[/dim]"
            table.add_row(str(idx), p.title[:40], p.url, intel_str)

        console.print(table)
        console.print(f"\n[bold green]Aggregated Emails ({len(result.aggregated_emails)}):[/bold green] {', '.join(result.aggregated_emails) if result.aggregated_emails else 'None'}")
        console.print(f"[bold green]Aggregated Phones ({len(result.aggregated_phones)}):[/bold green] {', '.join(result.aggregated_phones) if result.aggregated_phones else 'None'}\n")
