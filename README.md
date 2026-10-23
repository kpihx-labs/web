# xsearch — Sovereign Multi-Network Search CLI

**xsearch** is KπX's sovereign, ultra-flexible command-line search engine orchestrating simultaneous queries across:
1. **Surface Web**: Local SearXNG instance (`127.0.0.1:8081`) aggregating 261+ engines (Brave, Bing, Google, Wikipedia, GitHub, GitLab, etc.).
2. **Dark Web (.onion)**: Live hidden services query via local Tor SOCKS5 daemon (`127.0.0.1:9050`) with optional `oniux` / `torsocks` isolation wrappers.
3. **Deep Web (I2P)**: Encrypted eepsites routing via local I2P HTTP proxy (`127.0.0.1:4444`).

## Features

- **100% Uncensored**: SafeSearch defaults to 0 (Uncensored / Off).
- **Zero Hardcoded Limits**: Arbitrary page limits (`-n/--limit`), pagination (`-p/--page`), and timeouts (`--timeout`).
- **Engine Granularity**: Specify arbitrary engines (`-e brave,github,wikipedia`) or list them (`--list-engines`).
- **Surgical Filters**: Filter by domain (`-d/--site`), regex pattern (`-r/--regex`), or language (`-l/--lang`).
- **OSINT Intel Extraction**: Built-in phone number and email address extraction (`--intel`, `--has-phone`, `--has-email`).
- **Multi-Format Output**: Beautiful Rich terminal table (`-f table`), structured JSON (`-f json`), CSV (`-f csv`), or Markdown (`-f md`).
- **Deterministic Deduplication**: URL normalization stripping tracking tags, fragments, and subdomains.

## Installation

```bash
make uv-link    # Installs globally as ~/.local/bin/xsearch via uv tool
```

## Usage Examples

```bash
# 1. Surface Web search with Rich table output
xsearch "privacy tools" -s -f table -n 5

# 2. Dark Web (.onion) pure query
xsearch "bitcoin" --no-surface -o -f table -n 5

# 3. Hybrid search (Surface + Dark Web) with OSINT phone/email extraction
xsearch "contact security" -s -o -f table --intel -n 10

# 4. Surgical domain and regex filtering
xsearch "cryptography" -e github,brave -d github.com -r "bitcoin" -f json

# 5. OSINT search filtering strictly for records containing phone numbers
xsearch "support center" --has-phone -f table

# 6. List all available upstream search engines
xsearch --list-engines
```
