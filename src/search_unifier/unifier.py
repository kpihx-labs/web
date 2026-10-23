"""Core multi-network unifier engine (Surface, Tor .onion, and I2P)."""

import asyncio
import csv
import json
import sys
import urllib.parse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import List, Optional

import httpx
import requests
from bs4 import BeautifulSoup

from .config import CONFIG


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str          # e.g. "searxng:bing", "onion:tor66", "i2p:legwork"
    engine: str          # e.g. "bing", "tor66", "legwork"
    category: str        # "surface", "onion", "i2p"
    timestamp: str
    score: float = 0.0


class SurfaceSearcher:
    """Queries self-hosted SearXNG instance using JSON API."""

    def __init__(self, base_url: str = CONFIG.searxng_url):
        self.base_url = base_url.rstrip("/")

    async def search(
        self,
        query: str,
        engines: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[SearchResult]:
        params = {"q": query, "format": "json", "pageno": 1}
        if engines:
            params["engines"] = ",".join(engines)
        if categories:
            params["categories"] = ",".join(categories)

        results: List[SearchResult] = []
        try:
            async with httpx.AsyncClient(timeout=CONFIG.default_timeout_s) as client:
                resp = await client.get(f"{self.base_url}/search", params=params)
                resp.raise_for_status()
                data = resp.json()

            for r in data.get("results", [])[:limit]:
                results.append(
                    SearchResult(
                        title=r.get("title", ""),
                        url=r.get("url", ""),
                        snippet=r.get("content", ""),
                        source=f"searxng:{r.get('engine', 'unknown')}",
                        engine=r.get("engine", "unknown"),
                        category="surface",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
                )
        except Exception as e:
            if CONFIG.debug:
                print(f"[SurfaceSearcher] Error: {e}", file=sys.stderr)
        return results


class OnionSearcher:
    """Queries live dark web .onion search engines over local Tor SOCKS5."""

    def __init__(self, tor_proxy: str = CONFIG.tor_proxy):
        self.tor_proxy = tor_proxy
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0"
        }

    def _search_tor66(self, query: str, limit: int = 10) -> List[SearchResult]:
        results: List[SearchResult] = []
        proxies = {"http": self.tor_proxy, "https": self.tor_proxy}
        url = f"http://tor66sewebgixwhcqfnp5inzp5x5uohhdy3kvtnyfxc2e5mxiuh34iid.onion/search?q={urllib.parse.quote(query)}&sorttype=rel&page=1"

        try:
            r = requests.get(
                url,
                proxies=proxies,
                headers=self.headers,
                timeout=CONFIG.default_timeout_s,
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
                            results.append(
                                SearchResult(
                                    title=title,
                                    url=href,
                                    snippet="",
                                    source="onion:tor66",
                                    engine="tor66",
                                    category="onion",
                                    timestamp=datetime.now(timezone.utc).isoformat(),
                                )
                            )
                            if len(results) >= limit:
                                break
        except Exception as e:
            if CONFIG.debug:
                print(f"[OnionSearcher:tor66] Error: {e}", file=sys.stderr)

        return results

    async def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        # Offload synchronous SOCKS5 requests call to thread pool
        return await asyncio.to_thread(self._search_tor66, query, limit)


class I2PSearcher:
    """Interroge le réseau I2P via le proxy HTTP local."""

    def __init__(self, i2p_proxy: str = CONFIG.i2p_proxy):
        self.proxy = i2p_proxy

    async def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        # Extension prête pour legwork.i2p / eepsites
        return []


def deduplicate(results: List[SearchResult]) -> List[SearchResult]:
    """Déduplication déterministe basée sur l'URL normalisée."""
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


def output_results(results: List[SearchResult], output_format: str):
    """Sortie formatée (JSON, CSV, Markdown)."""
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
            cat_badge = f"[{r.category.upper()}]"
            print(f"- {cat_badge} **[{r.title}]({r.url})** (`{r.source}`)")
            if r.snippet:
                print(f"  {r.snippet}")
            print()
