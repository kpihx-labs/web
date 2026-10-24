# Revision audit: xsearch to web

Source discussion: `ses_e914aaa99ffevsePvfibgAwM2a`, titled
"Lien Google projets recherche argon 6 mois" (title contains a narrow space).
All 28 conversation text parts were read; tool records were inspected separately.
Large fetched page payloads were not confused with independent source confirmation.

## Findings

1. Initial backend outages were masked as empty results; subsequent failures now
   surface, but upstream rate limits and empty indexed responses remain distinct.
2. One-page slicing meant increasing --limit did not traverse an index. The Exa
   comparison used unequal budgets; claimed coverage/latency rankings were invalid.
3. Client-side site filtering happened after slicing; substring domain matching
   accepted unrelated URLs. Regex errors were ignored. URL dedup stripped all query
   parameters and lowercased case-sensitive paths, losing distinct documents.
4. Fetch treated HTTP 200 sign-up pages as useful content, represented connection
   failures as synthetic HTTP 500, ignored MIME types and fetched entire bodies.
5. Cookies lost domain/path/secure/expiry scope. Crawler followed redirects and
   cross-domain links with an unscoped dictionary of credentials.
6. Crawl called each page twice; link extraction ignored proxy overrides, blocked
   the event loop, had no robots policy, retry budget, pacing or safe download model.
7. Phone regex accepted years/identifiers. Extraction is not identity attribution.
8. Doc searched one 80-character fragment and a hash; unrelated returned links were
   labelled leaks/plagiarism. OCR passed PDF directly to Tesseract, which cannot
   read PDF input. No downloaded-byte verification or semantic similarity existed.
9. Image used Yandex only while advertising Google; exceptions became empty lists.
   Uploading original EXIF could disclose GPS. Tor/humming capabilities overstated.
10. ACRCloud humming was a paid API, not a permanent free capability. Removed.
    SongRec can attempt hummed input but fingerprints recordings, not melodies;
    lack of a free reliable humming API must not become an invented capability.
11. I2P search was a stub; similar was an alternatives query, not semantic matching.
12. Reports interpolated untrusted HTML without escaping and .pdf paths contained
    HTML. Result schemas, autosaves, configuration and lifecycle were inconsistent.
13. The legacy unverified prebuilt oniux executable had DAC_OVERRIDE/NET_ADMIN/
    NET_RAW file capabilities. They were revoked without privilege escalation and
    verified absent; the binary was moved out of PATH to a non-executable private
    /tmp/opencode/oniux-unverified-20261024.bak. web does not execute this helper.
    Shared Rust tooling/caches are not a web runtime dependency and are retained.
14. Optional Tor network validation could crash the surface SearXNG worker during
    startup. Surface and optional onion workers now have independent startup,
    configuration and IPC endpoints. User-owned configs mount read-only into a
    non-root image layout instead of becoming container-owned host files.
15. Pillow conversion can retain image metadata. The uploaded copy now explicitly
    clears info/EXIF; a provider-mock regression inspects the actual temporary PNG
    while preserving original metadata locally. No private user image was uploaded
    during live testing; the live fixture was the public Python logo.

## Design boundaries

Use one transport/content pipeline for fetch/crawl/download and candidate checking.
Preserve raw provider provenance and explicit budgets; never claim exhaustive search.
Keep browser-proxy independent for authorized JS/session interaction. Do not bypass
CAPTCHAs, access controls or TLS verification silently. Offline inspection should
not upload confidential documents. Uninstall removes the tool; purge is explicit
and retains source/history and shared dependencies. Provider failures stay visible.
