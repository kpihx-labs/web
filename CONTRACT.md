# web contract v2

Executable: web. Distribution/import: k-web / k_web. Historical xsearch behavior
is archived under references and is not the active contract.

## Common boundary

All result commands emit action, UTC timestamp, status and data. Formats: JSON,
JSONL, CSV, Markdown and Rich terminal tables/previews. Autosaves are unique, owner-only
JSON files under /tmp/web-results, overridable per command or disabled with -N.
Request credential fields are not added to logs/metadata. Retrieved content can
itself contain sensitive data: review private exports before sharing them.
Existing downloads/reports are
never overwritten. HTML is escaped and offline; PDF is a real Unicode-font PDF.

Exit 0: completed. Exit 2: invalid input/failed operation, actionable stderr.
Exit 3: usable partial results, access wall or best-effort humming. Success of
HTTP transport is not proof that requested content was read. Backend failures
must not become successful empty search results.

## Discovery

### 2.1 collection/presentation amendment

- -n is a best-effort unique-candidate target. -p/-P cap page requests;
  --start-page alone selects the starting index page. Stop reasons and shortfalls
  are explicit. Sources and complete folded URLs are presentation invariants.
- Format never chooses engines or changes a snapshot's candidate list. show
  replays saved data without network; regular repeat requests can use a labelled
  private TTL snapshot. Fresh forbids cache fallback; no-save disables persistence.
- Default relevance combines term coverage and numeric provider score. Explicit
  provider ranking uses that score, not unsorted API arrival order.
- Upstream refusal is not a local Docker failure. No Docker/VPN restart advice
  for CAPTCHA/429; optional bounded alternative indexes respect explicit -e.

Queries pass through unchanged, including quotes, site:, filetype:, intitle:,
OR and exclusions, subject to each upstream engine's actual syntax. Extra JSON
parameters are explicit. Unknown engines fail. Pages, output limit, relevance
heuristics and upstream failures are reported; coverage is never exhaustive.
Changing output limit alone does not fetch further pages.

## Retrieval

Only HTTP(S), TLS verified, scoped cookie jar and origin-scoped custom headers.
Private destinations require explicit opt-in; proxy-based DNS/redirect routing
never silently downgrades Tor/I2P to direct. DNS validation is a best-effort
guard, not a hardened hostile-network SSRF sandbox. Response budgets apply.
Fetch/crawl use the same transport and parse links from the same fetched body.
Crawl is paced, robots-aware, bounded, same-host and static HTML, not browser JS.

## Evidence and media

Documents are inspected offline unless online quote disclosure is explicit.
Supported parsing: PDF with optional raster OCR, DOCX tables, ODT/PPTX XML,
UTF-8 text/Markdown/CSV/JSON/HTML/XML/RST/TeX. Unsupported binary formats fail.
Exact-file evidence requires a byte hash match. Lexical similarity/excerpts are
not semantic equivalence, attribution, identity confirmation or plagiarism proof.
Image uploads are opt-in and original EXIF is removed from submitted pixels.
SongRec handles recordings; hum is a qualified fingerprint attempt, not a
melody engine. ACRCloud and paid API configuration are removed.

## Lifecycle

Setup never overwrites user configuration. Uninstall retains evidence. Purge
previews/trashes owned runtime paths only, retaining source/shared native tools.
Backend stop retains volumes; backend-purge requires confirmation and a backup.
No query silently changes a VPN, firewall, browser session or service state.
