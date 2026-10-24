# CONTRACT

This document is the non-negotiable source of truth for the `xsearch` project contract.

If implementation, wrappers, or docs conflict with this contract, this contract wins.

---

## 1) Metadata

- `schema_version`: `xsearch.contract.v1`
- `contract_version`: `1.3.0`

---

## 2) Conventions

- Multi-network search, crawl, reverse visual OSINT, and document forensics: Surface web (SearXNG API), Dark web (Tor .onion live), and Deep/Encrypted darknet (I2P eepsites).
- Deterministic deduplication based on normalized URL (strips URL fragments, query parameters, scheme/www variances).
- Subcommands: `search`, `fetch`, `crawl`, `image`, `doc`, `similar`, and `engines`.
- Auto-save convention: All command executions automatically serialize their JSON payload with ISO timestamp to `/tmp/xsearch-results/` (mimicking Exa CLI design), with override via `--save-dir` or `--no-save`.
- Autonomous reporting: Full standalone HTML reports exportable via `--report <path.html>`.
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

### `ExifMetadata`

| Field | Type | Description |
|---|---|---|
| `camera_make` | `str` | Hardware camera manufacturer (e.g. Apple, Canon) |
| `camera_model` | `str` | Camera/phone model name |
| `date_taken` | `str` | Original EXIF capture timestamp |
| `latitude` | `Optional[float]` | Decimal GPS latitude |
| `longitude` | `Optional[float]` | Decimal GPS longitude |
| `altitude` | `Optional[float]` | GPS elevation above sea level in meters |
| `software` | `str` | Firmware or image editing software |
| `has_gps` | `bool` | True if valid GPS coordinates were extracted |

### `ImageAuditResult`

| Field | Type | Description |
|---|---|---|
| `file_path` | `str` | Absolute path to analyzed image |
| `file_name` | `str` | Image basename |
| `sha256` | `str` | Cryptographic SHA256 image checksum |
| `exif` | `ExifMetadata` | Extracted camera, date, and GPS geolocation |
| `matches` | `List[ImageSearchResult]` | Discovered web matches across vision engines |

### `WaybackArchiveResult`

| Field | Type | Description |
|---|---|---|
| `url` | `str` | Audited web resource URL |
| `is_archived` | `bool` | True if archived snapshot exists on Wayback Machine |
| `archive_url` | `str` | Direct link to historical snapshot |
| `snapshot_timestamp` | `str` | Timestamp of closest historical capture |

### `DocumentAuditResult`

| Field | Type | Description |
|---|---|---|
| `file_path` | `str` | Canonical local file path |
| `file_name` | `str` | Basename of audited document |
| `file_size_bytes` | `int` | Document size in bytes |
| `file_type` | `str` | Detected format (`PDF`, `DOCX`, `MD`, `TXT`, `CSV`) |
| `sha256` | `str` | Cryptographic SHA256 file checksum |
| `char_count` | `int` | Extracted textual character count |
| `extracted_text_preview` | `str` | Clean excerpt preview |
| `extracted_emails` | `List[str]` | Discovered email addresses |
| `extracted_phones` | `List[str]` | Discovered phone numbers |
| `hash_leak_matches` | `List[SearchResult]` | Search results matching the exact SHA256 hash |
| `similarity_leak_matches`| `List[SearchResult]` | Search results matching verbatim sentence fragments |
| `wayback_archives` | `List[WaybackArchiveResult]`| Historical snapshots for embedded links |

---

## 4) Error model

- `UPSTREAM_TIMEOUT`: Engine, page, or SOCKS5 relay timed out after `--timeout` parameter.
- `UPSTREAM_UNREACHABLE`: SOCKS5 handshake failure or hidden service descriptor absent.
- `PARSE_ERROR`: HTML structure divergence in scraping targets.
- `IMAGE_LOOKUP_FAILED`: Reverse visual search engine changed DOM structure or triggered Cloudflare/Turnstile.
- `AUTH_BLOCKED`: HTTP 401/403 requiring cookie injection or session handover via `browser-proxy`.

---

## 5) Compliance rules

- No secret or tracking cookie may ever be sent or recorded without explicit operator input.
- Tor connections must support direct SOCKS5 proxy (`socks5h://127.0.0.1:9050`), `torsocks`, or kernel-isolated `oniux`.
- No version constraints may be pinned in dependencies; uv owns dependency resolution.

## 6) Audio and map extension contract (1.4.0)

This section governs the new extension commands and overrides incompatible older
coverage/privacy claims above. It does not retroactively certify legacy adapters.

- `audio [FILE]` or `audio --record SECONDS`: exactly one input; modes `recording`
  and `hum`; providers `auto`, `songrec`, `acrcloud`. Auto selects by mode, never
  silently falls back. CLI returns error exit 1 for invalid input/provider/network
  failure; a processed recording with no match is a successful no_match result.
- ACRCloud credentials and project mode are operator-owned. Hum mode requires a
  project whose engine supports cover/humming identification. No transcription.
- User setup exclusively creates config.py and .env from an empty packaged
  template; never overwrites either. Environment credentials take precedence.
- Map operations accept provider-native query/JSON data rather than enumerating
  real-world tags or vehicles in CLI flags. `route` uses BRouter protocol and an
  ordered list of place strings or [longitude, latitude] vertices. `request`
  exposes arbitrary JSON HTTP APIs without claiming cross-protocol equivalence.
- Output envelope: operation, timestamp (UTC ISO8601), data; map output includes
  attribution. Audio data includes provider/mode/status, normalized matches and
  unmodified provider result. Map data preserves native provider fields.
- Extensions autosave by default, allow a custom directory/opt-out, create unique
  0600 files and send notices to stderr. They do not save credentials or raw audio.
- Public services require compliant manual use. No anonymity, complete web
  coverage, Google reviews, guaranteed route safety or live humming validation
  without credentials is promised.

## 7) Backend resilience amendment (1.5.0)

- Unix IPC is preferred only for a configured local endpoint and a private socket
  directory; explicit endpoints/custom test transports are not silently replaced.
- Validate engine catalogue/search JSON. Failed transport never means zero engines
  or no matching documents. Bound retries by a total deadline, with fresh connections.
- CLI failure exit 2 has actionable stderr and no false successful empty autosave.
  Exit 3 preserves partial results while reporting missing source/upstream coverage.
- Doctor is read-only; its live flag explicitly invokes upstream search. Query-time
  code never changes routes, restarts Docker, starts a VPN or disables a kill switch.
- Missing requested onion isolation wrappers fail, rather than using direct transport.
- External service filtering/rate limits and arbitrary administrator/VPN firewall
  changes remain outside any availability guarantee.
