# web (kpihx-web)

Local-first research CLI: discover indexed sources, retrieve content, verify
evidence and preserve provenance. Python distribution: kpihx-web; executable: web.
The previous implementation and documentation remain under references/ for audit.

## Installation

Use `make install` from a clone, or `uv tool install kpihx-web` then `web setup`.
Run `make help` for dependency installation guidance, backend health/recovery,
testing and uninstall/purge targets. uv manages Python dependencies and uv_build
builds the package. No Hatch backend, paid recognition provider or transcription.

Clone either SSH remote, keeping the projects directly under your project root:

```sh
git clone git@github.com:kpihx-labs/web.git
# Alternative: git clone git@gitlab.com:kpihx-labs/web.git
make -C web install
make -C web backend-clone HOST=github  # or HOST=gitlab; retains an existing sibling
make -C web backend-up
web doctor --live
```

## Discover the CLI without guessing (2.2)

Every command level has a purpose/limits explanation, at least three varied
examples, and descriptions with examples for every argument and long/short flag.
The help is offline: it does not query providers, record audio, inspect files or
purge state. Explore the whole tree, including map's distinct API operations:

```sh
web --help
web search --help
web doc --help
web map --help
web map search --help
web map query --help
web map route --help
web map request --help
```

The recursive help contract and example parser tests fail if a new command ships
an undocumented option, missing short/long alias, or fewer than three examples.
Generated help remains English, like the code. Detailed shared descriptions live
in help_text.py, with explicit references at each Typer declaration.

## Search precision, budgets and provenance

```sh
web search '"Lado Saha" site:lig-membres.imag.fr -annuaire' -e 'google cse' -P 2 -n 30
web search '("memory scheduling" OR "unified memory") filetype:pdf after:2023' -P 3 -n 0 -f json
web search @query.txt -X '{"time_range":"year"}' -c science -l en -m 1
web search 'python logo' -c images -f json
web engines -r 'google|bing|duck'
```

Quotes, Boolean operators, exclusions, site:, filetype:, intitle:, inurl: and date
operators pass through unchanged. Support depends on the selected engine; there
is no universal Google syntax translator. `-X/--params` accepts arbitrary
SearXNG JSON or @file, while preserving the query/JSON response contract.
Unknown engine names fail rather than silently querying defaults. `provider_fields`
retains raw result metadata, including image URLs and provider-specific fields.

`-n 30` is a best-effort collection target: fetch further pages until 30 unique
filtered candidates, source exhaustion/failure or the page-request budget. Both
`-p` and legacy `-P` now mean --max-pages (default 3); --start-page/-s is separate.
This corrects 2.0's confusing -p=start/-P=count distinction. `-n 0` collects within
the full explicit budget. Output reports actual requests, counts and stop_reason;
it never pads or invents results when the target cannot be reached.
Default relevance ranking orders term coverage then SearXNG's numeric aggregate
score. `-k provider` sorts by that score alone (not API array/arrival order);
`-k lexical` uses term coverage only. None establishes identity or semantic truth.
Regex/domain filtering
precedes the display limit. Regular expressions use a configurable regex_timeout
budget rather than unbounded backtracking. URL dedup preserves meaningful query/path case.
SafeSearch `-m 0/1/2` is requested upstream; off does not remove upstream censorship.

Search and geocoding results are NEVER saved/read under the persistent cache
directory. Search is live on every invocation, including failures; --fresh/-F is
retained as a redundant compatibility flag. Old cache TTL settings cannot restore
disk caching. Automatic evidence is separate: /tmp/web-results by default, with
--save-dir override or --no-save to disable it. To compare table/JSON without
another provider request, use web show on the SAME selected /tmp result file.
Geocoding deduplicates only within a Maps instance in RAM. Cross-process pacing
keeps a timestamp-only lock under XDG_RUNTIME_DIR (fallback /tmp), never a JSON
response, query or coordinate. Repeated commands can therefore contact providers
again: respect limits, do not retry in a loop. Max pages, page delay and
fallback_engines remain plain configurable SETTINGS.
If defaults stall and a page-request budget remains, keyless Yahoo/Yep/MWMBL are
queried once as an explicit alternative batch. No IP/account switching, CAPTCHA
bypass or rate-limit evasion occurs. Explicit -e choices are not silently replaced.

The table shows **Sources**, a full contributor list, and folds complete URLs
without ellipses. Engine coverage distinguishes contributions, CAPTCHA, rate
limits and no-results-reported; the latter is not proof an engine was queried or
is healthy. Provider refusal does not recommend restarting Docker/VPN. Search
reads index snippets; use fetch separately to inspect actual page content.

```sh
web search 'KAMDEM Ivann' -n 30 -p 5
web show /tmp/web-results/SEARCH_SNAPSHOT.json -f table
web show /tmp/web-results/SEARCH_SNAPSHOT.json -f json
```
`show` renders exactly the saved snapshot without any network request, allowing
an honest table/JSON comparison. Different live requests may receive different
provider responses, even when their query text is identical.

## Fetch, inspection, sessions and exact downloads

```sh
web fetch https://example.org -s 'article h2' -r 'privacy|research' -f json
web fetch https://example.org/document.pdf -d /tmp/document.pdf
web fetch https://authorized.example/private -C /private/cookies.txt -H @/private/headers.json
web crawl https://quotes.toscrape.com -D 3 -n 4 -d /tmp/quotes-pages
```

Fetch downloads once, records MIME/byte SHA256 and extracts links from those same
bytes. Binary responses are not parsed as HTML. `--download` preserves exact
response bytes; existing files are refused. CSS and regex inspection use the
retrieved body, without extra requests. HTTP 200 login/registration/challenge
pages are classified as partial access, not useful source reads. These heuristics
can miss unusual walls; inspect access_state and content, not status alone.

Cookies accept Netscape including HttpOnly comments, browser JSON records or a
flat dictionary scoped to the seed host. Domain/path/secure/expiry restrictions
are honored. Custom headers are limited to the original origin across redirects;
header files avoid leaking tokens in shell history. Never send actual session
values to agents or paste them into reports. Requests ignore environment proxies;
`--proxy` explicitly selects HTTP/SOCKS. No TLS verification bypass is provided.

Crawl is same-host, paced (`--delay`), depth/page bounded and robots-aware by
default. `--no-robots` is explicit, not a bypass of authorization or terms.
Next/rel=next links are prioritized; JS scroll/click/API pagination is not executed.
`--match` restricts downloads, not traversal. Errors and remaining frontier are
retained in the manifest. New output directories avoid collisions on reruns.
Private/local destinations need `--allow-private` for your own services.
`--exclude` is a URL-frontier regex; its configurable default guards common
logout/delete/checkout GET links. An explicit empty expression disables it after
review. This heuristic is not proof GET is side-effect-free: use a dedicated
authorized session and inspect the frontier before crawling sensitive accounts.
DNS checks are best effort, not a security sandbox against hostile DNS rebinding.

For JS, authenticated DOM or browser challenges, use browser-proxy independently
with your authorization. A cookie handoff can help ordinary sessions but cannot
reproduce every browser/TLS fingerprint. This CLI never promises to bypass all
CAPTCHAs, paywalls, permissions or account login.

## Documents, images and audio

```sh
web doc report.pdf --compare other.pdf --ocr --pages 10 --report /tmp/evidence.pdf
web doc public-report.md --online --samples 3 --limit 5
web image photo.jpg                       # local metadata only
web image https://public.example/logo.png # remote input, still no reverse upload
web image public-logo.png --online -e yandex,google,bing --text-search
web audio excerpt.mp3
web audio --record 12 --mode hum
web archive https://public.example/report.pdf -P '{"timestamp":"20240101"}'
```

Doc is offline by default: --online discloses sampled quotes to search engines.
PDF/DOCX tables/ODT/PPTX and UTF-8 TXT/MD/CSV/JSON/HTML/XML/RST/TeX are supported;
unknown binary must be exported, not decoded as garbage. Scanned PDFs require
explicit OCR and are rendered to temporary images before Tesseract.
These parsers are not a malware sandbox; use OS isolation for hostile files.
Page limit 0 selects all pages and can be expensive. Comparisons provide exact byte equality
and lexical matching spans, NOT semantic equivalence or a plagiarism verdict.
Online links are candidates; downloaded content is checked separately. A hash
search result alone is not proof a file leaked. Archive uses Wayback's closest
snapshot API only; no Archive.today API or exhaustive historical search is claimed.

Image uploads require --online and omit original EXIF/GPS. Providers are fragile
unofficial adapters: failures or empty responses are not proof of absent copies.
--text-search explicitly discloses local OCR words as a complementary text search;
those results are not verified visual matches. GPS/device/time are local metadata.

Audio uses free SongRec/Shazam; FFmpeg normalizes/records an excerpt. `hum` is a
qualified best-effort fingerprint attempt and returns partial status: SongRec is
not a melody recognizer and reliable free humming is not established. ACRCloud,
paid API logic and credential loading are removed. No transcription is performed.

## Hidden networks and limits

Tor fetch uses SOCKS5h (managed optional profile: 127.0.0.1:19050; override
tor_proxy for an existing external daemon, commonly 9050); once selected, redirects do not
downgrade to direct or resolve through local DNS. I2P fetch requires an actual
HTTP proxy (default 127.0.0.1:4444). There is no fake I2P search adapter. For
indexed onion discovery use `web search QUERY -e ahmia -c onions`; coverage and
uptime depend on the index and Tor. Private/unindexed content has no universal
search engine. No tool can enumerate your complete digital footprint or prove
absence of a leak from absent results. No arbitrary third-party kill switch
compatibility or perfect anonymity is promised.

Surface SearXNG startup is independent of Tor. `make -C ../searxng onion-up`
explicitly starts an isolated optional onion worker; a failed Tor check does not
crash the surface worker. `web engines -z onion` inspects it. `web search QUERY
-e bing,ahmia` partitions those engines between backends and reports missing
coverage rather than losing working surface results. `-z surface,onion` explicitly
selects both, or use custom `SETTINGS['search_backends']` entries with url/socket
fields for another SearXNG-compatible backend. Budgets apply per backend, so total
requests grow with the number of selected backends. Protocols other than SearXNG
still need an adapter; arbitrary services are not interchangeable by naming them.

## Configuration, dependencies and lifecycle

`web setup` creates ~/.config/web/config.py only if absent. SETTINGS is plain
trusted Python, not a loader framework. WEB_CONFIG_DIR and standard XDG roots
control configuration where supported. Existing xsearch configuration/cache were
moved, not destroyed; dormant old .env credentials are never loaded. Defaults in
config.py include response_max_bytes, local_max_bytes, xml_max_bytes and
max_redirects; put overrides in SETTINGS.
Set phone_region (for example FR) to validate national-format numbers; without
a region hint, international numbers are preferred rather than guessing dates.
Local SearXNG prefers its owner-only
Unix socket to avoid host VPN TCP routing; remote endpoints remain explicit.

Python libraries are resolved with bare uv add and uv.lock, never pip or manual
dependency arrays. System dependencies are deliberately separate/shared:

| Feature | Native dependency / installation guidance |
| --- | --- |
| Audio | ffmpeg; SongRec via Cargo: cargo install songrec --no-default-features --features ffmpeg |
| SongRec source build | Rust/Cargo, pkg-config, Clang/libclang, libsoup-3.0-dev, ALSA/PipeWire development headers as required upstream |
| PDF OCR | poppler-utils (pdftoppm), tesseract-ocr and desired language data |
| Unicode PDF report | fontconfig (fc-match), fonts-dejavu-core; fpdf2 is managed by uv |
| Backend | Docker Engine and Compose plugin; sibling searxng repository documents images/ports/volumes |
| Tor/I2P | Your own reachable Tor SOCKS5h/I2P HTTP proxy; never silently started |

Use upstream package instructions for your OS; dependency install commands evolve.
`make deps` reports installed native capabilities and guidance rather than a rigid
root installer. Cold builds need network or cached packages/images. Docker logs
are bounded by the backend; web has no background daemon or persistent log file.
JSON evidence is not silently rotated/deleted; /tmp is volatile. Explicit
download/report destinations are user evidence and not automatically purged.

`make uninstall` removes the uv tool only. `make purge` stops the sibling backend,
trashes owned runtime paths, uninstalls the tool, and retains source/shared native
tools. `make backend-purge CONFIRM=searxng` backs up named volumes under a private
/tmp directory (.bak files), then removes only that stack's volumes. Review its
Make recipe first. Never run global Docker prune. A clone is retained so reinstall
works from either GitHub or GitLab. `make purge-all CONFIRM=searxng` sequences
the confirmed backend backup/removal and app purge. Install from PyPI using
uv tool install kpihx-web.

All commands use an action/timestamp/status/data envelope. Formats: table, json,
jsonl, csv, md; --report creates escaped offline HTML or a real PDF. Autosaves are
unique 0600 JSON in /tmp/web-results; -S overrides and -N disables. Exit 2 is
failure, exit 3 is partial/access-wall coverage, exit 0 is completion. Inspect
non_exhaustive, budgets and source errors before drawing conclusions. Source
quality, identity attribution and correctness require human corroboration.
