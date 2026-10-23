# CHANGELOG — xsearch

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
