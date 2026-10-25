"""Local transport defaults; user settings override these without source edits."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    searxng_url: str = "http://127.0.0.1:8081"
    # Local IPC avoids host TCP policy routing/proxy interception by VPN clients.
    searxng_socket: str = str(
        Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
        / "web/searxng/searxng.sock"
    )
    tor_proxy: str = "socks5h://127.0.0.1:19050"
    i2p_proxy: str = "http://127.0.0.1:4444"
    default_timeout_s: float = 30.0
    debug: bool = False
    response_max_bytes: int = 10_000_000
    local_max_bytes: int = 50_000_000
    xml_max_bytes: int = 20_000_000
    max_redirects: int = 10
    phone_region: str | None = None
    regex_timeout: float = 0.25
    search_max_pages: int = 3
    search_page_delay: float = 1.0
    geocode_memory_entries: int = 128
    fallback_engines: tuple[str, ...] = ("yahoo", "yep", "mwmbl")
    # Heuristic guard for authenticated crawls; GET is not guaranteed side-effect-free.
    crawl_exclude_regex: str = r"(?i)/(?:logout|signout|delete|remove|unsubscribe|checkout)(?:[/?=]|$)|[?&](?:action|do)=(?:delete|remove|logout)"


CONFIG = Config()
