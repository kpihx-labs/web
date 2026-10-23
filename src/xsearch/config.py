"""Centralized immutable configuration for xsearch (KπX sovereign standard)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    searxng_url: str = "http://127.0.0.1:8081"
    tor_proxy: str = "socks5h://127.0.0.1:9050"
    i2p_proxy: str = "http://127.0.0.1:4444"
    default_timeout_s: float = 30.0
    debug: bool = False


CONFIG = Config()
