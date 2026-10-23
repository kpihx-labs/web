# CHANGELOG — xsearch

## [1.1.0] - 2026-10-23
- Implemented recursive asynchronous web crawler subcommand: `xsearch crawl <url> [-D/--depth] [-n/--max-pages] [--stay-domain/--cross-domain] [--download-dir]`.
- Implemented `browser-proxy` session bridge: support for `--cookie-file / -C` (JSON and standard Netscape formats) and custom repeatable `--header / -H` across `search`, `fetch`, and `crawl`.
- Added `--proxy` override parameter allowing custom HTTP/SOCKS upstream routing per command.
- Added local asset and page dump saving via `--download-dir` with sanitized filename encoding.
- Verified live recursive crawling on both Clearnet (`quotes.toscrape.com`) and live Tor Dark Web (`tor66.onion/fresh`).
- Updated `CONTRACT.md` to schema version `xsearch.contract.v1` v1.1.0.

## [1.0.0] - 2026-10-23
- Renamed `search-unifier` to `xsearch` under `~/Labs/KpihX-Labs/xsearch`.
- Complete overhaul of the CLI interface with **Typer** and **Rich** (support for short flags `-s`, `-o`, `-i`, `-e`, `-c`, `-d`, `-r`, `-n`, `-p`, `-m`, `-l`, `-t`, `-f`).
- Implemented OSINT intelligence extraction: automatic regex scraping of phone numbers and email addresses (`--intel`, `--has-phone`, `--has-email`).
- Added client-side surgical filtering for domain names (`-d/--site`) and regular expressions (`-r/--regex`).
- Added engine discovery command `xsearch engines` listing active upstream engines from SearXNG.
- Added support for `--transport` (`direct`, `torsocks`, `oniux`).
- Centralized version reading via `importlib.metadata.version("xsearch")`.
- Linked globally in `~/.local/bin/xsearch` via `make uv-link`.
