# AGENTS.md — xsearch

> Project context for all AI agents working in this repository.
> Loaded automatically by all KπX agents when present at project root.

## KπX Mantras

**Exploration:** Problem First → Why before How → Visualization
**Architecture:** 0 Trust · 100% Control | 0 Magic · 100% Transparency | 0 Hardcoding · 100% Flexibility

## Project Overview

| Field | Value |
|-------|-------|
| Purpose | Sovereign ultra-flexible multi-network search CLI (Surface, Tor .onion, I2P) |
| Stack | Python 3.12+, uv, Typer, Rich, httpx, requests[socks], BeautifulSoup4, lxml |
| Local Port | Talks to local SearXNG (`127.0.0.1:8081`) and Tor daemon (`127.0.0.1:9050`) |
| Status | 🟢 Production ready |

## Architecture Rules

- **No version constraint pinning**: All package additions must use bare `uv add <pkg>`.
- **Pure config.py**: Runtime defaults live in `src/xsearch/config.py` (no YAML, no config loader).
- **Graceful network degradation**: Tor latency or SOCKS5 timeouts must never block Surface web results.
- **English-only code**: All comments, variable names, docstrings and error models must be in English.
