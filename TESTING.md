# Verification record, 2026-10-24

No delegated agents were used for this revision. See references/AUDIT.md for the
source-discussion review and the defects behind the design changes.

## Offline gates

### 2.1 search correction verification (2026-10-25)

- Original failing live case `web search "KAMDEM Ivann" -n 30 -p 5` collected
  30 unique candidates in three page requests. Default providers were limited;
  explicit fallback used Yahoo/Yep/MWMBL, with coverage still labelled partial.
- Default `web search "KAMDEM Ivann"` collected 20/20 in two page requests.
  Three immediately repeated JSON commands reused the exact same candidate
  snapshot (live_request=false, no new provider calls).
- Table replay used that snapshot and folded complete URLs. Unit verification
  reconstructs a long URL from table cells and compares it byte-for-byte.
- Tests cover table/JSON snapshot identity, all duplicate contributors, numeric
  score/relevance ranking, early target stop, explicit shortfall, bounded fallback,
  explicit engine preservation, stale-on-error labels and lowercase -p semantics.

`make check`: Ruff lint/format, Pyright, and 48 regressions on this workstation.
Coverage includes HTTP 200 auth walls, binary hashes, scoped cookies/custom headers,
redirects across hosts/ports, Tor proxy preservation/no local DNS, I2P HTTP proxy
protocol, robots, next links, one fetch per page, URL case/query semantics,
regex deadlines, engine selection/paging, optional-backend failures, PDF/DOCX/raster
OCR, escaped HTML/real PDF, download collisions, CSV formulas and purge guards.
Optional native OCR/font tools are installed for these tests; CI provisions them.

`tests/live_lifecycle.py`: built-wheel offline install in isolated HOME/tool paths,
setup, capability inspection, owned-state purge and make uninstall all passed.
The user's actual configuration, evidence and global tool were not removed.

`tests/live_backend_lifecycle.py`: a unique throwaway Docker project with a 32-byte
fixture volume. No-confirm purge refused; confirmed purge created a private .bak,
its contents were verified, and only the throwaway volume was removed. Production
volumes/containers remained running. Backups were retained under /tmp.

## Live observations, not a general benchmark

| Action | Actual observation |
| --- | --- |
| search exact Lado name | Two index pages attempted; 18 candidates with google cse, requested output limit 30 |
| fetch/download | example.com: 577 bytes preserved; SHA256 25ddf2c883e0d1958ea971d279a7e4f0fd446724ee3db7db19dadabd4a62e484; real PDF report generated |
| crawl pagination | quotes.toscrape.com pages 1, 2, 3, 4 retrieved and downloaded once each |
| LIG page | ConnectionError reported, not synthesized HTTP 500 or a successful read |
| Wayback | HTTP 429 reported, not false "not archived" |
| image | Yandex parsing failure; Google empty; Bing failure. These are not evidence of absent copies |
| image OCR complement | Local Python-logo OCR query returned three text candidates with explicit partial visual coverage |
| audio recording | Public iTunes preview recognized as Get Lucky via SongRec |
| synthetic hummed melody | No match; partial qualified fingerprint attempt, no paid API |
| map | Polytechnique geocoding and 743 m BRouter route returned through native JSON adapters |
| optional onion backend | Separate Ahmia/Torch catalogue; privacy query returned three candidates; Ahmia .onion fetch succeeded |
| combined surface/onion | Bing/Ahmia query returned results without backend failures |

Third-party blocking, rate limits, stale indexes and future availability are not
under this client's control. No perfect anonymity, universal access-control
bypass, semantic plagiarism verdict or complete digital-footprint inventory is
claimed. Tests of fake data validate mechanisms, not universal provider quality.
