# Changelog: web (formerly xsearch)

## [2.1.0] - 2026-10-25
- Correct everyday search UX: -n is a target; -p/-P are page-request-budget aliases;
  --start-page is explicit. Stop at target and report exact shortfall/reason.
- Rank by term coverage plus provider score by default; provider mode uses the
  numeric score instead of the unsorted API array. Merge all duplicate provenance.
- Sources column lists every contributor; complete URLs fold instead of ellipsizing.
- Expose per-engine snapshot coverage and separate upstream refusal from local
  backend failure. No irrelevant Docker/VPN restart remedy for CAPTCHA/429.
- Add private labelled query snapshots, explicit fresh mode, stale-on-error
  qualification and bounded keyless fallback (Yahoo/Yep/MWMBL), respecting -e.
- Add offline show for comparison of the exact same table/JSON data; no new search.
- Live original failing case collected 30 candidates in three page requests;
  a repeated table request reused the snapshot without contacting providers.

## [2.0.0] - 2026-10-24
- Breaking executable/package migration: web / k-web / k_web, repository web;
  configuration/cache moved without destroying existing evidence. Historical
  implementation/docs/tests remain in references, not active runtime modules.
- Replaced the monolithic mixed engine with separate HTTP, research, documents,
  images, audio, models and reporting boundaries. Unified envelopes/exit codes.
- Search preserves operators, raw JSON parameters, meaningful URL query/case,
  provider fields/provenance and explicit page budgets. Provider ranking is default;
  lexical ranking is opt-in. Unknown engines/regex errors fail, not silently default.
- Fetch/crawl share a scoped cookie/session pipeline, classify access walls,
  preserve exact downloads, honor robots and pacing, and prioritize next-page links.
  Private destinations are opt-in; Tor/I2P redirects never downgrade to direct.
- Doc is offline by default, includes real raster PDF OCR and local byte/lexical
  comparison; optional online candidates are checked separately. No unsupported
  plagiarism/semantic or hash-search leak verdict is emitted.
- Image upload is explicit and EXIF-free, with optional local OCR text candidates;
  actual provider blocking is partial coverage, not a successful no-match verdict.
- Removed ACRCloud and paid credential loading. Free SongRec recording recognition
  remains; hum is explicitly qualified best effort, not a reliable melody engine.
- Added escaped offline HTML/real PDF reports, private collision-resistant results,
  lifecycle Make targets, backed-up backend purge, SSH remotes and offline CI.

## [1.5.0] - 2026-10-24
- Prefer private Unix-domain IPC to local SearXNG when available, avoiding host TCP
  policy routing and environment HTTP proxies. Explicit remote endpoints stay explicit.
- Add bounded backend retries under a total deadline, validated JSON/catalogue
  responses and actionable exceptions instead of swallowed errors and empty tables.
- Add read-only `doctor` with optional live canary. Exit 2 means failure; exit 3
  means partial/degraded coverage. Diagnostics and autosave notices use stderr.
- Do not save failed searches as successful empty results; partial autosaves retain
  upstream/source failures. Missing requested isolation wrappers never silently fall back.
- Mark unimplemented I2P explicitly; propagate document-search failures rather than
  presenting absent evidence as a successful audit.
- Add network-reset/503/deadline/catalogue/CLI/Unix IPC regressions and an explicit
  live backend-stop/network-detach recovery test. Live DE Psiphon and Japan k-vpn
  checks returned engine inventories and real search results over Unix IPC and TCP.

## [1.4.0] - 2026-10-24
- Added audio recognition through SongRec/Shazam and signed ACRCloud AVR requests;
  hummed melodies use a separately configured cover/humming project, never STT.
- Added FFmpeg excerpt normalization and microphone/monitor capture, explicit mode,
  provider, source, offset, duration, timeout, and no implicit provider fallback.
- Added user config setup with exclusive creation of config.py and an empty .env
  from the packaged template, mode 0600, no overwrites and no credential logging.
- Added generic map search/query/route/request with arbitrary JSON parameters,
  Overpass QL, ordered place/coordinate vertices and provider-defined profiles.
- Added keyless public API access, geocoder cache/shared rate limiter, attribution,
  and private timestamped autosave envelopes with clean JSON stdout for extensions.
- Live checks: Get Lucky recognized from file and virtual audio capture; silence
  produced no_match; Nominatim resolved Polytechnique; Overpass found four water
  points; BRouter returned a 743 m / 119 s route. ACRCloud uses mocked protocol
  tests until operator credentials are available; no online humming success claimed.
- Added regression tests and documented system/build dependencies and API policies.

## [1.3.0] - 2026-10-23
- Implemented EXIF metadata & GPS geolocation parsing in `xsearch image` using `exifread`: extraction of camera make/model, original date, altitude, and decimal GPS latitude/longitude with direct OpenStreetMap URL mapping.
- Implemented Wayback Machine API verification in `xsearch doc`: checks whether URLs embedded in documents have historical archived snapshots with timestamp and direct link.
- Implemented autonomous dark-themed HTML reporting (`--report <path.html>`) across `search`, `crawl`, `image`, and `doc`.
- Implemented universal auto-save mimicking Exa CLI design: every execution automatically serializes its JSON payload with ISO timestamp to `/tmp/xsearch-results/` (overridable via `--save-dir` or opt-out via `--no-save`).
- Updated `CONTRACT.md` to schema version `xsearch.contract.v1` v1.3.0 and `pyproject.toml` to v1.3.0.

## [1.2.0] - 2026-10-23
- Implemented `xsearch image <file>`: asynchronous reverse image search using `PicImageSearch` across Yandex Visual and Google Lens.
- Implemented `xsearch doc <file>`: universal multimodal document audit for PDF, DOCX, Markdown, TXT, and CSV.
- Integrated multi-engine PDF parsing pipeline: fast C-native `pdftotext`, `pypdf`, and `tesseract` OCR for scanned documents.
- Integrated automated SHA256 file checksum leak detection and verbatim sentence similarity / plagiarism detection across Surface Web and Tor Darknet.
- Documented system dependencies (`poppler-utils`, `tesseract-ocr`, `tor`) in `README.md`.

## [1.1.0] - 2026-10-23
- Implemented recursive asynchronous web crawler subcommand: `xsearch crawl <url> [-D/--depth] [-n/--max-pages] [--stay-domain/--cross-domain] [--download-dir]`.
- Implemented `browser-proxy` session bridge: support for `--cookie-file / -C` (JSON and standard Netscape formats) and custom repeatable `--header / -H` across `search`, `fetch`, and `crawl`.
- Added `--proxy` override parameter allowing custom HTTP/SOCKS upstream routing per command.
- Added local asset and page dump saving via `--download-dir` with sanitized filename encoding.
- Verified live recursive crawling on both Clearnet (`quotes.toscrape.com`) and live Tor Dark Web (`tor66.onion/fresh`).

## [1.0.0] - 2026-10-23
- Renamed `search-unifier` to `xsearch` under `~/Labs/KpihX-Labs/xsearch`.
- Complete overhaul of the CLI interface with **Typer** and **Rich** (support for short flags `-s`, `-o`, `-i`, `-e`, `-c`, `-d`, `-r`, `-n`, `-p`, `-m`, `-l`, `-t`, `-f`).
- Implemented OSINT intelligence extraction: automatic regex scraping of phone numbers and email addresses (`--intel`, `--has-phone`, `--has-email`).
- Added client-side surgical filtering for domain names (`-d/--site`) and regular expressions (`-r/--regex`).
- Added engine discovery command `xsearch engines` listing active upstream engines from SearXNG.
- Added support for `--transport` (`direct`, `torsocks`, `oniux`).
- Centralized version reading via `importlib.metadata.version("xsearch")`.
- Linked globally in `~/.local/bin/xsearch` via `make uv-link`.
