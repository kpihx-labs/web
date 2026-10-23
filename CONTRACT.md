# CONTRACT

This document is the non-negotiable source of truth for the `xsearch` project contract.

If implementation, wrappers, or docs conflict with this contract, this contract wins.

---

## 1) Metadata

- `schema_version`: `xsearch.contract.v1`
- `contract_version`: `1.1.0`

---

## 2) Conventions

- Multi-network search and crawl abstraction: Surface web (SearXNG API), Dark web (Tor .onion live), and Deep/Encrypted darknet (I2P eepsites).
- Deterministic deduplication based on normalized URL (strips URL fragments, query parameters, scheme/www variances).
- Subcommands: `search`, `fetch`, `crawl`, `similar`, and `engines`.
- Output channels: stdout format selection via `-f/--format` (`table`, `json`, `csv`, `md`, `text`).
- Telemetry & error handling: errors in one network or page must never crash entire workflows (graceful degradation via `asyncio.gather` and exception boundary isolation).
- Zero censorship & zero hardcoded bounds: arbitrary page limits, recursive depths (`-D/--depth`), custom cookies (`-C/--cookie-file`), custom headers (`-H/--header`), and proxy overrides (`--proxy`).

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
| `extracted_emails` | `List[str]` | Discovered email addresses via OSINT regex |
| `extracted_phones` | `List[str]` | Discovered phone numbers via OSINT regex |

### `FetchResult`

| Field | Type | Description |
|---|---|---|
| `url` | `str` | Target URL fetched |
| `title` | `str` | Extracted page title |
| `content` | `str` | Clean textual content (scripts and styles stripped) |
| `text_length` | `int` | Character count of clean text |
| `status_code` | `int` | HTTP response status code |
| `category` | `str` | Network category (`surface`, `onion`, `i2p`) |
| `extracted_emails` | `List[str]` | Email addresses extracted from body |
| `extracted_phones` | `List[str]` | Phone numbers extracted from body |

### `CrawlResult`

| Field | Type | Description |
|---|---|---|
| `base_url` | `str` | Seed entry URL for recursive crawling |
| `total_pages_visited` | `int` | Count of successfully processed pages |
| `pages` | `List[FetchResult]`| Detailed results per visited page |
| `aggregated_emails` | `List[str]` | Unique sorted emails across all crawled pages |
| `aggregated_phones` | `List[str]` | Unique sorted phones across all crawled pages |

---

## 4) Error model

- `UPSTREAM_TIMEOUT`: Engine, page, or SOCKS5 relay timed out after `--timeout` parameter.
- `UPSTREAM_UNREACHABLE`: SOCKS5 handshake failure or hidden service descriptor absent.
- `PARSE_ERROR`: HTML structure divergence in scraping targets.
- `AUTH_BLOCKED`: HTTP 401/403 requiring cookie injection or session handover via `browser-proxy`.

---

## 5) Compliance rules

- No secret or tracking cookie may ever be sent or recorded without explicit operator input.
- Tor connections must support direct SOCKS5 proxy (`socks5h://127.0.0.1:9050`), `torsocks`, or kernel-isolated `oniux`.
- No version constraints may be pinned in dependencies; uv owns dependency resolution.
