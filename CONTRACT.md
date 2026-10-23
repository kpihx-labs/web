# CONTRACT

This document is the non-negotiable source of truth for the `search-unifier` project contract.

If implementation, wrappers, or docs conflict with this contract, this contract wins.

---

## 1) Metadata

- `schema_version`: `search-unifier.contract.v1`
- `contract_version`: `1.0.0`

---

## 2) Conventions

- Multi-network search abstraction: Surface web (SearXNG API), Dark web (Tor .onion live), and Deep/Encrypted darknet (I2P eepsites).
- Deterministic deduplication based on normalized URL (strips URL fragments, query parameters, scheme/www variances).
- Output channels: stdout format selection via `-f/--format` (`json`, `csv`, `md`).
- Telemetry & error handling: errors in one network must never crash queries in other networks (graceful degradation via `asyncio.gather`).

---

## 3) Shared types

### `SearchResult`

| Field | Type | Description |
|---|---|---|
| `title` | `str` | Title of the web document / hidden service |
| `url` | `str` | Normalized target URL (clearnet or `.onion`) |
| `snippet` | `str` | Context excerpt or description |
| `source` | `str` | Network and engine identifier (e.g. `searxng:brave`, `onion:tor66`) |
| `engine` | `str` | Upstream search engine name |
| `category` | `str` | Network tier: `surface`, `onion`, or `i2p` |
| `timestamp` | `str` | ISO 8601 UTC timestamp of execution |
| `score` | `float` | Relevance score |

---

## 4) Error model

- `UPSTREAM_TIMEOUT`: engine or SOCKS5 relay timed out after `CONFIG.default_timeout_s`.
- `UPSTREAM_UNREACHABLE`: SOCKS5 handshake failure or hidden service descriptor absent.
- `PARSE_ERROR`: HTML structure divergence in scraping targets.

---

## 5) Compliance rules

- No secret or tracking cookie may ever be sent or recorded.
- Tor connections must strictly utilize the local SOCKS5 proxy (`socks5h://127.0.0.1:9050`).
- No version constraints may be pinned in dependencies; uv owns dependency resolution.
