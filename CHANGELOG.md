# CHANGELOG — xsearch

## [1.0.0] - 2026-10-23
- Renamed `search-unifier` to `xsearch` under `~/Labs/KpihX-Labs/xsearch`.
- Complete overhaul of the CLI interface with **Typer** and **Rich** (support for short flags `-s`, `-o`, `-i`, `-e`, `-c`, `-d`, `-r`, `-n`, `-p`, `-m`, `-l`, `-t`, `-f`).
- Implemented OSINT intelligence extraction: automatic regex scraping of phone numbers and email addresses (`--intel`, `--has-phone`, `--has-email`).
- Added client-side surgical filtering for domain names (`-d/--site`) and regular expressions (`-r/--regex`).
- Added engine discovery command `--list-engines` listing active upstream engines from SearXNG.
- Added support for `--transport` (`direct`, `torsocks`, `oniux`).
- Centralized version reading via `importlib.metadata.version("xsearch")`.
- Linked globally in `~/.local/bin/xsearch` via `make uv-link`.
