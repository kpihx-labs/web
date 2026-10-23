# xsearch — Sovereign Multi-Network Search, Crawl & Multimodal Audit CLI

**xsearch** is KπX's sovereign, ultra-flexible command-line search, recursive crawling, reverse visual intelligence, and deep document audit engine orchestrating operations across:
1. **Surface Web**: Local SearXNG instance (`127.0.0.1:8081`) aggregating 261+ engines (Brave, Bing, Google, Wikipedia, GitHub, GitLab, etc.).
2. **Dark Web (.onion)**: Live hidden services query and deep crawling via local Tor SOCKS5 daemon (`127.0.0.1:9050`) with optional `oniux` / `torsocks` isolation wrappers.
3. **Deep Web (I2P)**: Encrypted eepsites routing via local I2P HTTP proxy (`127.0.0.1:4444`).
4. **Visual Reverse Intelligence**: Asynchronous reverse visual matching across Yandex Visual and Google Lens.
5. **Document Audit & Leak Detection**: Universal text parsing (PDF, DOCX, TXT, MD, CSV) via native `pdftotext`, `pypdf`, `tesseract` OCR, SHA256 checksum tracking, OSINT scanning, and verbatim plagiarism exposure.

## Features

- **100% Uncensored**: SafeSearch defaults to 0 (Uncensored / Off).
- **Subcommands Parity**:
  - `xsearch search` : Multi-network search with engine selection, regex, domain filters, and OSINT detection.
  - `xsearch fetch`  : Content extractor for clearnet or `.onion` with cookie injection and OSINT scanning.
  - `xsearch crawl`  : Asynchronous recursive crawler with depth limit, domain boundaries, and local text dumps.
  - `xsearch image`  : Reverse visual image search for local image files (PNG, JPG, WEBP) returning matched URLs.
  - `xsearch doc`    : Deep document auditor extracting text, calculating SHA256, extracting contacts, and scanning for leaks/plagiarism.
  - `xsearch similar`: Discovery of alternative platforms and related services for any domain.
  - `xsearch engines`: Live discovery of active upstream engines in SearXNG.
- **browser-proxy Bridging**: Inject session cookies (`-C/--cookie-file`) and custom headers (`-H/--header`) to bypass CAPTCHAs, Cloudflare walls, or cookie consent banners after validation in `k-browser`.
- **System Dependencies**:
  - `poppler-utils` (`pdftotext` binary): Recommended for ultra-fast C-native PDF text extraction.
  - `tesseract-ocr` (`tesseract` binary): Fallback OCR for image-only or scanned PDFs.
  - `tor`: Local SOCKS5 daemon on port 9050 for all `.onion` routing.

## Installation

```bash
make uv-link    # Installs globally as ~/.local/bin/xsearch via uv tool
```

## Usage Examples

```bash
# 1. Reverse Image Search on a local file (avatar, photo, logo)
xsearch image ~/Pictures/mon_avatar.png -n 5 -f table

# 2. Document Audit (PDF, DOCX, Markdown) for leaks, plagiarism, and contact extraction
xsearch doc ~/Downloads/contrat_confidentiel.pdf --leak --similarity --onion -f table

# 3. Surface Web search with Rich table output
xsearch search "privacy tools" -s -f table -n 5

# 4. Dark Web (.onion) pure query
xsearch search "bitcoin" --no-surface -o -f table -n 5

# 5. Hybrid search (Surface + Dark Web) with OSINT phone/email extraction
xsearch search "contact security" -s -o -f table --intel -n 10

# 6. Surgical domain and regex filtering
xsearch search "cryptography" -e github,brave -d github.com -r "bitcoin" -f json

# 7. Fetch a page with cookie injection (passed from browser-proxy)
xsearch fetch "https://private-forum.org/thread/123" -C /tmp/browser_cookies.json -f md

# 8. Recursive crawling with local disk save
xsearch crawl "https://example.com" -D 2 -n 25 --download-dir "/tmp/site_dump" -f table

# 9. Discover platforms similar to a target site
xsearch similar "github.com" -n 5 -f table
```
