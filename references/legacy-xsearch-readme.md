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

## Audio recognition and generic maps (1.4)

These extensions identify music, not speech. They do not transcribe recordings.
`audio`, `map search`, `map query`, `map route`, and `map request` write a
timestamped JSON envelope to `/tmp/xsearch-results/` by default. Use `-S/--save-dir`
to choose another location or `-N/--no-save` to disable saving. New autosave files
are owner-readable/writable only (0600); notices go to stderr, leaving JSON stdout
usable by other programs. Their `table` format is a Rich structured JSON view,
preserving nested provider fields rather than hiding them in fixed columns.

### Dependencies and installation

| Component | Required for | Installation / notes |
| --- | --- | --- |
| uv with `uv_build` | Python package and wheel | `uv sync`, `make check`, `make build`, `make uv-link` |
| Python dependencies | HTTP, configuration, CLI | Managed by `uv add` and `uv.lock`; includes `python-dotenv`, `requests[socks]`, Typer and Rich |
| FFmpeg | Normalize excerpts and capture microphone/system audio | Ubuntu `ffmpeg`; capture uses its PulseAudio input, compatible with PipeWire's Pulse server |
| SongRec | Keyless Shazam recording identification | `cargo install songrec --no-default-features --features ffmpeg` |
| Rust/C toolchain | Build SongRec from source | Cargo/rustc, C compiler, pkg-config, Clang and libclang development headers |
| Native development libraries | SongRec build, platform-dependent | On this workstation: `libsoup-3.0-dev`; ALSA/PipeWire development libraries may also be required by upstream |
| ACRCloud AVR project | Hummed melody or optional recorded-audio identification | Project host, access key and access secret; no Google Workspace credentials involved |
| Nominatim / Overpass / BRouter | Map operations | Remote HTTP services; no local routing server or API keys required for the configured public endpoints |

SongRec is a Rust executable, not a Python dependency: uv installs xsearch,
not SongRec. Its unofficial Shazam service can change without notice.
Ubuntu source-build prerequisites verified on this workstation are
`build-essential`, `pkg-config`, `clang`, `libclang-dev`, `libsoup-3.0-dev`,
`libpipewire-0.3-dev`, and `libasound2-dev`. `pulseaudio-utils` is optional for
listing/creating test audio sources; FFmpeg is required for capture itself.
`pactl list short sources` lists microphone and monitor source names when pactl
is installed. An alternative source name goes in `audio --source VALUE`.
Do not put the machine-specific name in the source code.

`make uv-link` also runs `xsearch setup`. A plain `uv tool install` does not
execute post-install hooks; run `xsearch setup` explicitly in that case.
Setup creates, without overwriting:

* `~/.config/xsearch/config.py`: plain Python `SETTINGS` for map endpoints, timeout,
  user agent and default route profile. This file is trusted executable local code.
* `~/.config/xsearch/.env`: copied from the packaged `.env.example`, initially empty.

Both files are created with mode 0600 in a 0700 directory. Set
`XSEARCH_CONFIG_DIR` to use a different configuration directory. Never paste real
keys in CLI arguments, logs, reports or tracked files. Environment variables take
precedence over the credentials file; xsearch never prints credential values.

### Original excerpt vs hummed melody

```bash
xsearch audio excerpt.mp3
xsearch audio excerpt.mp3 -O 30 -d 12 -f json
xsearch audio --record 12
xsearch audio --record 12 --source YOUR_MONITOR_SOURCE
xsearch audio melody.wav --mode hum
xsearch audio --record 12 --mode hum --provider acrcloud
```

Default `--provider auto` chooses SongRec for `--mode recording` and ACRCloud
for `--mode hum`. There is no silent fallback between providers. SongRec sends
an acoustic fingerprint to Shazam, not the raw recording. ACRCloud's current
adapter uploads a normalized mono 16 kHz WAV excerpt; it does not keep the
temporary WAV after completion. Duration defaults to 12 seconds; offset defaults
to zero. Record mode captures exactly `--record` seconds. HTTP/subprocess timeout
defaults to 30 seconds and is adjustable with `-T`. Recognition is catalogue-based:
neither service searches every sound on the Internet. A matched song is not proof
that a personal recording has been published anywhere.

### Create ACRCloud credentials

1. Register at https://console.acrcloud.com/signup and verify your account.
2. Create an **Audio & Video Recognition (AVR)** project with **ACRCloud Music**.
3. For humming select **Cover Song (humming) Identification**, or the combined
   fingerprinting and cover/humming engine. Select Recorded Audio for microphone
   recordings. This server-side project setting is essential; a CLI flag cannot
   enable a catalogue/engine your project does not have.
4. Copy HOST, ACCESS_KEY and ACCESS_SECRET manually into the corresponding
   `ACRCLOUD_HUM_*` entries in the user `.env`. Optional recording projects use
   `ACRCLOUD_*`. HOST is a hostname, without `https://` or a path.
5. Missing credentials produce an actionable error before recording or uploading.

Official documentation: https://docs.acrcloud.com/get-started/tutorials/recognize-music
and https://docs.acrcloud.com/reference/identification-api/identification-api .
The vendor advertises a 14-day trial; pricing, request allowances and concurrency
depend on the project/account and must be checked in its console. Do not assume
unlimited/free ongoing humming. Identification API documents a sample below 5 MB
and recommends excerpts shorter than 15 seconds. No automatic quota-consuming retries.
Paid online recognition is not verified until you supply your own project credentials.

### Map operations, not one flag per real-world object

```bash
# A place name -> provider JSON, including address and coordinates
xsearch map search "École polytechnique, Palaiseau" -P '{"limit":1,"addressdetails":1}'

# Arbitrary OSM predicates and spatial logic, not a fixed tag whitelist
xsearch map query '[out:json][timeout:20];nwr(around:1000,48.7128,2.2107)["shop"~"bicycle|supermarket"];out center;'
xsearch map query @query.overpass -f json

# An ordered path: any number of place names and/or [longitude, latitude] pairs
xsearch map route '["Palaiseau","Bièvres","Versailles"]' -p trekking
xsearch map route '[[2.2107,48.7128],[2.215,48.715]]' -P '{"alternativeidx":1}' -f json

# Full API escape hatch: future fields do not need new CLI options
xsearch map request https://nominatim.openstreetmap.org/reverse -P '{"lat":48.7128,"lon":2.2107,"format":"jsonv2"}'
xsearch map request https://example.org/map-api -X POST -b @request.json
```

`-P/--params` accepts any JSON object or `@file`; `-b/--body` passes arbitrary JSON.
`map request` is explicit network access, not an interpretation of natural language.
`map route` is a BRouter adapter; `-p/--profile` is a provider-defined string, not
an enum tied to a list of vehicles. A new profile needs no CLI code change, but it
must exist on the chosen server. Other API protocols can be used through `request`;
changing a URL alone cannot make incompatible routing protocols interchangeable.
Use raw provider format parameters for GeoJSON or other supported JSON structures.
Named intermediate vertices are geocoded with a geographic bias around the previous
vertex to reduce homonym errors. The response includes `xsearch_resolved_vertices`
so you can verify every selected coordinate. Names remain ambiguous: use a fully
qualified name or coordinates when exact location matters. The bias is not a routing
boundary; its radius can be adjusted in user settings (`route_geocode_bias_degrees`).

Nominatim policy: https://operations.osmfoundation.org/policies/nominatim/ .
This is an informed, manual personal-use integration: maximum one geocoding request
per second, no autocomplete, no systematic bulk collection, no confidential addresses.
Searches are cached for 24 hours under `~/.cache/xsearch/geocode/`, with a shared
process lock enforcing the geocode interval. The raw `request` escape hatch does
not add geocoder caching/throttling: the caller must observe the target's policy.
Overpass public servers are shared, can return 429/502/timeouts, and have no uptime
guarantee. Query bounded regions, cache your exports, and do not rotate servers to
evade usage policies. BRouter public service is for light interactive use; configure
your own endpoint for sustained workloads. Responses retain provider attribution;
map envelopes also include OpenStreetMap attribution.

OSM provides opening hours/contacts/accessibility only when contributors entered
them. It does not provide Google reviews, guaranteed current closures or a live
traffic feed. Route times are estimates, not safety guarantees. Keyless public
services still receive your requests/IP; self-hosting is a separate choice.

### Scope corrections to older descriptions

The legacy I2P search adapter is a stub, not a working I2P search engine. Legacy
image recognition currently calls Yandex only. Existing document search candidates
are not verified leak/plagiarism evidence, and absence of results proves neither
originality nor confidentiality. HTML reports are not PDF reports. Cookie reuse
does not guarantee bypass of JavaScript/TLS-fingerprint-bound anti-bot challenges.
SafeSearch off does not remove upstream filtering or make coverage exhaustive.

### Verification on 2026-10-24

* `make check`: regression tests cover exclusive config creation, missing credentials,
  mode rejection, FFmpeg/SongRec command construction, signed ACRCloud multipart
  requests, generic profiles/vertices, JSON file input, private unique autosaves,
  CLI help, shared geocoder caching and arbitrary Overpass predicates.
* Original recording: a 12-second public iTunes preview was recognized as
  **Get Lucky - Daft Punk, Pharrell Williams & Nile Rodgers** through live Shazam.
* Capture: ten seconds captured from a dedicated virtual monitor returned the same
  song; no private microphone conversation was captured. The virtual sink was removed.
* Silence: three seconds returned `no_match`, not an invented song or network error.
* Nominatim: Polytechnique resolved to latitude 48.7127874 / longitude 2.2107453.
* Overpass: four drinking-water elements returned within 800 m of the campus point.
  POST encountered a 502; the adapter now defaults to GET, with an optional
  `overpass_method` setting for endpoints requiring POST. One alternate public
  instance timed out; this is not treated as an empty successful query.
* Route: Palaiseau -> Bievres -> Versailles, with locality-biased geocoding, returned
  18,965 m, 3,908 s and 165 m ascent. Coordinates are preserved for verification.
* Humming: missing-key failure and request signing tested; a live matched melody
  still requires operator-supplied ACRCloud project credentials.

## Usage Examples

### Pipeline resilience (1.5)

The local CLI prefers `~/.cache/xsearch/searxng/searxng.sock` when the deployed
gateway supplies it. This is HTTP over Unix IPC, not a TCP connection to a Docker
private address, so a VPN's host policy route cannot redirect this local hop.
The host directory is owner-only (0700); the root-created socket inside it is
0666 so the owning user can connect without changing the container UID. Other
users cannot traverse the directory. Unsafe directory ownership/permissions fail
explicitly. The gateway receives only this narrow host-directory bind mount.

User `SETTINGS` can override `searxng_url`, `searxng_socket`, and
`searxng_transport` (`auto`, `unix`, `tcp`). Existing config files are never
overwritten; add these optional keys manually if needed. Auto uses Unix when
present and otherwise local TCP; an explicit remote URL is not replaced by a
local socket. Local requests ignore HTTP_PROXY/HTTPS_PROXY from the environment.
The existing search `--transport` option still selects the separate onion
isolation wrapper, not this backend transport.

```bash
xsearch doctor
xsearch doctor --live -e bing -f json
# Explicitly verify the TCP alternative as well as the Unix IPC path:
xsearch doctor --backend http://127.0.0.1:8081 --live -e bing -f json
```

Backend requests retry transient connection/502/503/504 failures, with fresh
connections and exponential backoff, bounded by the requested total timeout.
`search_attempts` defaults to 3; `search_retry_delay` defaults to 0.3 seconds and
can be changed in `SETTINGS`. Non-JSON responses, missing catalogues, backend
unreachability and upstream engine errors are distinct from a valid empty query.

* Exit 0: requested operation succeeded without reported coverage degradation.
* Exit 2: unavailable/invalid backend or failed requested search. No false empty
  success table/report/autosave is emitted. Read stderr for the recovery action.
* Exit 3: partial coverage. Usable results are still emitted; warnings go to stderr.
  Partial JSON autosaves use a `search_partial` filename and an envelope with
  results, source_failures and upstream_issues instead of claiming complete coverage.

In the sibling SearXNG deployment, `make health` checks real host API access,
`make live` performs an explicit external canary and `make recover` validates
configuration, recreates only this stack's containers/endpoints and waits for
readiness. Named volumes are retained. It does not restart Docker or WiFi.
`make test-recovery` in this project explicitly stops the backend and detaches
its Docker network, restoring both in finally blocks; it is not an offline check.

Verified cases include a strictly unmanaged Docker bridge, blocked NetworkManager
reactivation, backend stop/restart, network loss/reconnect, and live search with
Psiphon DE and OpenVPN/VPN Gate Japan. The Japan test used a five-relay budget;
the first single-relay attempt and strict HTTPS discovery did fail and were not
presented as successful VPN tests. k-vpn source did not need modification.

This is not immunity to every future VPN: a root kill switch can block container
egress/forwarding, DNS or Docker itself. Unix IPC isolates the local host-routing
problem; explicit diagnostics expose the remaining failure. No firewall bypass
or VPN privacy weakening is performed automatically when a query fails.

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
