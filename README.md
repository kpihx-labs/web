# xsearch — Sovereign Multi-Network Search & Crawl CLI

**xsearch** is KπX's sovereign, ultra-flexible command-line search and recursive crawling engine orchestrating queries and extractions across:
1. **Surface Web**: Local SearXNG instance (`127.0.0.1:8081`) aggregating 261+ engines (Brave, Bing, Google, Wikipedia, GitHub, GitLab, etc.).
2. **Dark Web (.onion)**: Live hidden services query and deep crawling via local Tor SOCKS5 daemon (`127.0.0.1:9050`) with optional `oniux` / `torsocks` isolation wrappers.
3. **Deep Web (I2P)**: Encrypted eepsites routing via local I2P HTTP proxy (`127.0.0.1:4444`).

## Features

- **100% Uncensored**: SafeSearch defaults to 0 (Uncensored / Off).
- **Subcommands Parity**:
  - `xsearch search` : Multi-network search with engine selection, regex, domain filters, and OSINT detection.
  - `xsearch fetch`  : Content extractor for clearnet or `.onion` with cookie injection and OSINT scanning.
  - `xsearch crawl`  : Asynchronous recursive crawler with depth limit, domain boundaries, and local text dumps.
  - `xsearch similar`: Discovery of alternative platforms and related services for any domain.
  - `xsearch engines`: Live discovery of active upstream engines in SearXNG.
- **browser-proxy Bridging**: Inject session cookies (`-C/--cookie-file`) and custom headers (`-H/--header`) to bypass CAPTCHAs, Cloudflare walls, or cookie consent banners after validation in `k-browser`.
- **Zero Hardcoded Limits**: Arbitrary page limits (`-n/--limit`), pagination (`-p/--page`), crawling depth (`-D/--depth`), and timeouts (`--timeout`).
- **OSINT Intel Extraction**: Built-in phone number and email address extraction (`--intel`, `--has-phone`, `--has-email`).
- **Multi-Format Output**: Rich terminal table (`-f table`), structured JSON (`-f json`), CSV (`-f csv`), or Markdown (`-f md`).
- **Deterministic Deduplication**: URL normalization stripping tracking tags, fragments, and subdomains.

## Installation

```bash
make uv-link    # Installs globally as ~/.local/bin/xsearch via uv tool
```

## Usage Examples

```bash
# 1. Surface Web search with Rich table output
xsearch search "privacy tools" -s -f table -n 5

# 2. Dark Web (.onion) pure query
xsearch search "bitcoin" --no-surface -o -f table -n 5

# 3. Hybrid search (Surface + Dark Web) with OSINT phone/email extraction
xsearch search "contact security" -s -o -f table --intel -n 10

# 4. Surgical domain and regex filtering
xsearch search "cryptography" -e github,brave -d github.com -r "bitcoin" -f json

# 5. Fetch a page with cookie injection (passed from browser-proxy)
xsearch fetch "https://private-forum.org/thread/123" -C /tmp/browser_cookies.json -f md

# 6. Recursive crawling with local disk save
xsearch crawl "https://example.com" -D 2 -n 25 --download-dir "/tmp/site_dump" -f table

# 7. Deep crawling on Dark Web (.onion)
xsearch crawl "http://tor66sewebgixwhcqfnp5inzp5x5uohhdy3kvtnyfxc2e5mxiuh34iid.onion/fresh" -D 1 -n 10 -f table

# 8. Discover platforms similar to a target site
xsearch similar "github.com" -n 5 -f table

# 9. List all available upstream search engines
xsearch engines
```
