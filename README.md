# xsearch — Sovereign Multi-Network Search, Crawl & Multimodal Audit CLI

**xsearch** is KπX's sovereign, ultra-flexible command-line search, recursive crawling, reverse visual intelligence, and deep document audit engine orchestrating operations across:
1. **Surface Web**: Local SearXNG instance (`127.0.0.1:8081`) aggregating 261+ engines (Brave, Bing, Google, Wikipedia, GitHub, GitLab, etc.).
2. **Dark Web (.onion)**: Live hidden services query and deep crawling via local Tor SOCKS5 daemon (`127.0.0.1:9050`) with optional `oniux` / `torsocks` isolation wrappers.
3. **Deep Web (I2P)**: Encrypted eepsites routing via local I2P HTTP proxy (`127.0.0.1:4444`).
4. **Visual Reverse Intelligence**: Asynchronous reverse visual matching across Yandex Visual and Google Lens with automatic **EXIF GPS geolocation** parsing.
5. **Document Audit & Leak Detection**: Universal text parsing (PDF, DOCX, TXT, MD, CSV) via native `pdftotext`, `pypdf`, `tesseract` OCR, SHA256 checksum tracking, OSINT scanning, verbatim plagiarism exposure, and **Wayback Machine historical snapshot verification**.
6. **Autonomous Reporting & Auto-Save**: Automatic JSON serialization with timestamps into `/tmp/xsearch-results/` (mimicking Exa CLI design) and standalone HTML report exports (`--report`).

## Features

- **100% Uncensored**: SafeSearch defaults to 0 (Uncensored / Off).
- **Subcommands Parity**:
  - `xsearch search` : Multi-network search with engine selection, regex, domain filters, and OSINT detection.
  - `xsearch fetch`  : Content extractor for clearnet or `.onion` with cookie injection and OSINT scanning.
  - `xsearch crawl`  : Asynchronous recursive crawler with depth limit, domain boundaries, and local text dumps.
  - `xsearch image`  : Reverse visual image search for local images with EXIF GPS parsing and camera model extraction.
  - `xsearch doc`    : Deep document auditor extracting text, calculating SHA256, extracting contacts, scanning for leaks/plagiarism, and checking Wayback Machine snapshots.
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
# 1. Reverse Image Search with EXIF GPS extraction & HTML report
xsearch image ~/Pictures/mon_avatar.png -n 5 --report /tmp/image_report.html -f table

# 2. Document Audit (PDF, DOCX, Markdown) for leaks, plagiarism, contacts, and Wayback archives
xsearch doc ~/Downloads/contrat.pdf --leak --similarity --onion --report /tmp/doc_report.html -f table

# 3. Recursive crawling with local disk save
xsearch crawl "https://quotes.toscrape.com" -D 2 -n 25 --download-dir "/tmp/site_dump" -f table

# 4. Surface Web search with Rich table output and OSINT detection
xsearch search "contact security" -s -o -f table --intel -n 10

# 5. Fetch a page with cookie injection (passed from browser-proxy)
xsearch fetch "https://private-forum.org/thread/123" -C /tmp/browser_cookies.json -f md

# 6. Discover platforms similar to a target site
xsearch similar "github.com" -n 5 -f table
```
