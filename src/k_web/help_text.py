"""User-facing contracts. Explicit help is shared, not guessed from parameter names."""

OPTIONS = {
    "version": "Print the installed package version from Python metadata and exit; no network. Example: web --version.",
    "format": "Output view: table is a human preview; json is the complete envelope; jsonl is one envelope per line; csv is spreadsheet-safe; md is Markdown. Example: -f json | jq '.data'. Notices/errors stay on stderr.",
    "save": 'Directory for private timestamped JSON evidence (not raw downloads). Default: /tmp/web-results or WEB_RESULTS_DIR. Example: -S "$HOME/Research/evidence". Each save has a unique name; existing evidence is retained.',
    "no_save": "Disable automatic evidence saves. Search and doc/image text discovery also avoid query-cache reads/writes. Example: -N for ephemeral inspection. Explicit --report/--download outputs are still written.",
    "report": "Write a NEW standalone .html or real .pdf containing the full envelope. Example: -R /tmp/investigation.html or -R /tmp/investigation.pdf. Existing paths are refused; Unicode PDF needs fontconfig/DejaVu. No screenshot or plagiarism verdict is invented.",
    "engines": "Comma-separated exact engine names from 'web engines'; quote names containing spaces. Example: -e 'bing,google cse'. An explicit choice is not silently replaced by fallback engines; support for operators/pagination varies upstream.",
    "network": "Search backend(s), not a VPN region. Examples: -z surface, -z onion, -z surface,onion. Onion engines can be inferred from -e ahmia; enable their isolated worker with make backend-onion-up. Custom SearXNG-compatible backends go in search_backends settings.",
    "engine_network": "ONE configured backend whose catalogue to inspect. Examples: -z surface or -z onion. The optional onion worker must be running; catalogue entries do not prove current availability.",
    "rank": "Ranking method: relevance (default) orders term coverage then numeric provider score; provider uses score alone; lexical uses term coverage alone. Example: -k provider. These are ranking hints, never proof of identity or semantic equivalence.",
    "search_pages": "Maximum index-page REQUESTS while collecting the target; default search_max_pages=3. -p and -P are aliases, NOT a starting page. Example: -n 30 -p 5. Fallback batches consume this same budget; collection stops early at the target.",
    "start_page": "Advanced starting index page; default 1. Example: --start-page 3 -p 2 attempts pages starting at 3. Use -p for a page-count budget. Many engines do not support deep pages; fallback is not used to silently reset an explicit start.",
    "search_limit": "Best-effort number of unique FILTERED candidates to collect. Example: -n 30 -p 5; -n 0 collects within the whole page budget. Exhaustion/blocks may prevent reaching it: count, shortfall and stop reason are reported, never padded.",
    "site": "Restrict to a hostname/subdomains: forwards site: upstream and checks actual URL hosts locally. Example: -d github.com. It is not a URL-substring filter; example.org in another site's query string does not match.",
    "regex": "Client-side regex over title, snippet and URL, before the result limit. Example: -r '(?i)memory|scheduler'. regex_timeout bounds matching; invalid/expensive patterns fail explicitly. It does not search unfetched page bodies.",
    "engine_regex": "Filter catalogue names locally with a case-insensitive regex. Example: -r 'google|bing|ahmia'. No individual engine query is sent; matching a name does not prove that engine responds.",
    "category": "SearXNG category string, passed to the selected backend. Examples: -c science, -c images, -c onions. Names/support depend on its catalogue; this is not a universal content-type guarantee.",
    "language": "Upstream search language preference, not document translation or OCR language. Examples: -l fr, -l en, -l all. Engines can ignore or interpret locale preferences differently.",
    "safe": "Requested upstream SafeSearch: 0=off, 1=moderate, 2=strict. Example: -m 1. Off does not bypass legal restrictions, permissions, CAPTCHA or provider filtering.",
    "timeout": "Network/request time budget in seconds. Example: -T 15. Search retries share its request deadline; multiple pages/backends take separate budgets. This is not a guarantee the entire command finishes in that many seconds.",
    "search_params": 'Additional SearXNG parameters as a JSON object or @file. Example: -X \'{"time_range":"year"}\'. q/format/pageno are controlled by the CLI; conflicting engines are rejected. Native provider support still applies.',
    "fresh": "Force live collection; do not reuse a query snapshot or return stale-on-error evidence. Example: --fresh -e bing. Repeating this can trigger provider limits; table/JSON normally share a labelled cache snapshot.",
    "cookies": "Authorized session file: browser JSON/storage cookies, flat JSON or Netscape cookies.txt. Example: -C /private/cookies.json. Domain/path/secure/expiry are honored; protect bearer credentials with mode 0600 and never paste values into chat. Browser-bound challenges may still fail.",
    "header": "Repeat 'Name: Value' headers or load @JSON. Example: -H 'Accept: application/json' -H @/private/headers.json. Custom headers stay on the seed origin and are stripped across origins. Keep real Authorization values out of shell history.",
    "proxy": "Explicit HTTP/SOCKS proxy URL. Example: -p socks5h://127.0.0.1:19050 for managed Tor. Environment proxies are ignored; hidden-network routing never silently falls back to direct. I2P requires its own HTTP proxy/router.",
    "bytes": "Maximum response bytes; default response_max_bytes from config (10 MB). Example: -b 2000000. Oversized downloads fail rather than pretending to be complete; increase only for trusted, intentional large files.",
    "private": "Explicitly allow local/private destinations for YOUR services. Example: -a with http://127.0.0.1:8000. Default DNS checks reject them; these checks are not a hardened hostile-DNS sandbox.",
    "download": "Save exact response bytes to a NEW path, independently of cleaned text and evidence JSON. Example: -d /tmp/paper.pdf. MIME/byte count/SHA256 are reported; no overwrite and no automatic execution of downloaded content.",
    "selector": "Inspect CSS-matching nodes in the same downloaded HTML. Example: -s 'article h2, main a[href]'. Returns selected text without another request; no JavaScript runs and selectors do not bypass access walls.",
    "fetch_regex": "Find regex spans in retrieved text and report offsets. Example: -r '(?i)unified memory|GPU'. This inspects the fetched body, not search snippets; regex_timeout applies.",
    "depth": "Maximum link depth from seed: 0=seed only, 1=direct links, 3=up to three edges. Example: -D 3 -n 12. Next links are prioritized but still obey depth/page/robots/scope limits.",
    "crawl_pages": "Maximum distinct document URLs attempted, not a promise of successful pages. Example: -n 25. robots.txt is a separate policy request; failures/exclusions and remaining frontier are recorded.",
    "delay": "Seconds between crawl page attempts; default 0.5. Example: -w 1.5. Respect site terms/limits; zero is for controlled fixtures, not a general permission to hammer public servers.",
    "robots": "Check and respect robots.txt by default. --no-robots explicitly disables this check after YOU review permission/policy. Example: --robots on a public documentation crawl. Neither setting bypasses authentication or site terms.",
    "download_dir": "Directory for exact downloaded page/binary bytes, with URL-derived collision-resistant names. Example: -d /tmp/docs-crawl. Use a new directory for reruns; these explicit downloads are not deleted by app purge.",
    "crawl_match": "Regex deciding which retrieved bodies to SAVE, not which links to traverse. Example: -r '(?i)privacy|scheduler' with -d /tmp/evidence. Keep the frontier broad while retaining only useful pages.",
    "exclude": "Regex excluding URLs from the crawl frontier before retrieval. Default guards common logout/delete/checkout GET paths. Example: -x '/calendar/|/logout'. An explicit empty string disables it after review; GET is not inherently side-effect-free.",
    "compare": "Repeat for local comparison documents. Example: -c draft.pdf -c published.docx. Extracts text and reports exact-byte equality/lexical spans; does not upload these files or declare plagiarism.",
    "ocr": "For image-only PDFs, rasterize selected pages then run local Tesseract. Example: -O -p 2. Requires pdftoppm/tesseract; no cloud transcription. Native parser/OCR failures are explicit.",
    "doc_pages": "PDF pages to inspect from the beginning; default 10, 0=all. Example: -p 3 -O for a scanned excerpt. This option means PDF pages HERE, not search pagination; all-page OCR can be expensive.",
    "online_doc": "Explicitly disclose sampled document words to search engines, then retrieve bounded candidates for checking. Example: -o -s 3 -n 5 on a PUBLIC report. Default is offline; never use casually on confidential material.",
    "query_mode": "Online discovery mode: exact quotes the sampled words; keywords sends them unquoted for broader candidates. Example: -q keywords. Broader discovery increases noise and does not add semantic plagiarism detection.",
    "samples": "Maximum sampled significant text fragments to disclose with --online; default 3. Example: -s 5. Sampling is distributed across qualifying lines, not every paragraph; each search has its own page/provider budgets.",
    "doc_limit": "Maximum online discovery results per sampled query AND maximum unique candidates to retrieve/check; default 5. Example: -n 8. It is not the number of PDF pages or a guarantee eight readable sources exist.",
    "online_image": "Explicitly upload a temporary pixel copy to requested reverse-image providers. Example: -o -e yandex,bing. Original EXIF/GPS/ICC metadata is removed from the submitted copy; the provider still sees pixels and network metadata.",
    "text_search": "With --online, run local OCR and disclose up to 15 OCR words as an additional TEXT query. Example: -o -t on a public logo. Those URLs are text candidates, not verified visual matches; useful when visual adapters are blocked.",
    "image_engines": "Comma-separated visual adapters: yandex, google, bing. Example: -e yandex,bing. They are unofficial/free interfaces; layout changes, empty responses and challenges are reported, not proof no copies exist.",
    "image_limit": "Maximum visual candidates PER requested engine; 0=all fetched by that adapter. Example: -n 5. This does not expand the provider's catalogue, and the OCR text complement has its own bounded search.",
    "record": "Capture this many seconds from the chosen Pulse/PipeWire source, instead of a file. Example: -r 12 -s default. Exactly one of FILE or --record is required; make sure recording is authorized.",
    "audio_mode": "recording identifies an original excerpt; hum only tries that same fingerprint engine on a melody. Example: -m hum. Hum always carries partial/best-effort qualification: there is no reliable free melody API here.",
    "duration": "Seconds extracted from a FILE for identification; default 12. Example: -d 15 -O 30. Live capture duration comes from --record instead. Durations must be positive/finite.",
    "source": "PulseAudio/PipeWire input or monitor source name. Example: -s default or -s YOUR_MONITOR_SOURCE to capture system output. List sources with pactl list short sources; no microphone is opened by help.",
    "offset": "Start offset in a FILE, in seconds; default 0. Example: -O 45 -d 12. Not accepted with live --record, so capture is not silently delayed.",
    "similar_limit": "Best-effort number of alternative-site candidates to discover. Example: -n 12 -e bing. Uses normal search target/cache/provider rules; no semantic-nearest-neighbor guarantee.",
    "live": "Also send a known public search canary to upstream engines. Example: web doctor -l -f json. Without this flag only local backend/frontend readiness is inspected; repeated live probes consume provider tolerance.",
    "confirm_purge": "Actually trash owned config/cache/state/default-result paths; otherwise preview only. Example: web purge -y AFTER make backend-down. Active IPC, symlinks and foreign-owned dirs are refused; source/shared tools/custom evidence remain.",
    "map_params": 'Provider-native JSON object or @file, without an artificial tag whitelist. Example: -P \'{"limit":3,"addressdetails":1}\'. Parameters/quotas belong to that provider; do not put credentials in URL queries.',
    "profile": "Provider-defined route-profile VALUE, not a vehicle flag. Example: -p trekking or -p fastbike if supported by your BRouter. New server profiles need no CLI flag; incompatible API protocols still need an adapter.",
    "method": "Explicit HTTP method for your chosen JSON API. Example: -X GET; -X POST only when documented/authorized. Unlike fetch/crawl this can invoke write semantics, so do not experiment on sensitive production endpoints.",
    "body": "JSON request body or @file for a documented API. Example: -b @request.json. It is not Overpass form encoding: use map query for Overpass QL. Keep private values out of history and review returned content before sharing.",
    "show_format": "Re-render the original saved envelope as table or json ONLY. Example: -f json to inspect all metadata. No fresh timestamp, index request, cache refresh or re-ranking is introduced.",
    "archive_params": 'Wayback availability API parameters as JSON or @file. Example: -P \'{"timestamp":"20240101"}\'. Closest capture only, not a full CDX history or proof of byte-identical content.',
}

ARGUMENTS = {
    "query": "Literal search expression, or @UTF-8 query file. Quotes/operators pass through unchanged. Example: '\"unified memory\" filetype:pdf -tutorial'. Different engines interpret syntax differently.",
    "url": "HTTP(S) target to retrieve; Tor/I2P need a reachable configured proxy. Example: https://example.org/report.pdf. Credential-bearing URLs are refused; use scoped session files, never file:// or pasted secrets.",
    "document": "Local PDF/DOCX/ODT/PPTX or supported UTF-8 text document. Example: ./public-report.pdf. Parsing is offline by default; use OS isolation for hostile files.",
    "image": "Local image path OR public HTTP(S) image URL. Examples: ./logo.png or https://httpbin.org/image/png. Metadata-only unless --online; URL input itself requires a download.",
    "audio": "Optional local media file FFmpeg can decode. Example: ./excerpt.mp3 or ./video.mp4 for its audio track. Omit only when using --record; no transcription or raw-recording upload to a paid API.",
    "site_url": "Site/domain whose alternatives to discover. Example: github.com or https://github.com. This generates a transparent text query, not semantic similarity or source ownership verification.",
    "place": "Place/address to geocode using configured Nominatim-compatible API. Example: 'École polytechnique, Palaiseau'. Ambiguous names can resolve elsewhere; inspect coordinates and avoid confidential addresses on public services.",
    "overpass": "Complete Overpass QL string OR @query.overpass file. Example: '[out:json]; nwr(around:500,48.7128,2.2107) [amenity=drinking_water]; out center;'. Bound the region/time; no natural-language-to-QL guessing.",
    "vertices": 'Ordered JSON path OR @file: each vertex is a place name or [LONGITUDE,LATITUDE]. Example: \'["Palaiseau",[2.217,48.755],"Versailles"]\'. At least two vertices; returned resolved coordinates must be verified.',
    "endpoint": "Explicit HTTP(S) API endpoint. Example: https://nominatim.openstreetmap.org/reverse. Use map query for Overpass form requests; credentials in endpoint userinfo are refused.",
    "snapshot": "A saved web JSON ENVELOPE, not a cookie file or old bare result list. Example: /tmp/web-results/search_....json. Replays exactly its candidates/provenance; never contacts providers.",
    "archive_url": "Public resource URL to disclose to Wayback for a closest-snapshot lookup. Example: https://www.python.org/. No automatic document upload; do not send credential-bearing or confidential URLs.",
}

COMMANDS = {
    "root": (
        "Discover indexed sources, inspect real content and retain qualified evidence. Search is not fetch, and a candidate is not a verified identity. JSON/CSV/Markdown are complete structured exports; terminal tables are previews with complete URLs. Exit 2=failure, 3=partial, 0=completed within the explicit budget.",
        [
            "web search '\"unified memory\" filetype:pdf -tutorial' -n 30 -p 5 -l en",
            "web fetch https://example.com --selector 'p' --report /tmp/page.html",
            "web doc public-report.pdf -c draft.docx --ocr -p 3 --report /tmp/comparison.pdf",
        ],
    ),
    "map": (
        "Geospatial operations over provider-native APIs: search resolves place names, query executes Overpass QL, route calculates an ordered path, request is the raw JSON-API escape hatch. No Google Maps token is needed for the default public endpoints. OSM data can lack hours/accessibility and does not contain Google reviews. Observe rate limits and inspect every resolved coordinate.",
        [
            "web map search 'École polytechnique, Palaiseau' -P '{\"limit\":2,\"addressdetails\":1}'",
            "web map query '[out:json][timeout:20];nwr(around:1000,48.7128,2.2107)[shop=bicycle];out center;'",
            'web map route \'["Palaiseau","Bièvres","Versailles"]\' -p trekking -f json',
        ],
    ),
    "search": (
        "Collect a best-effort target of unique indexed candidates with explicit page-request budgets. All contributors are retained in Sources; numeric engine scores/term coverage rank candidates but do not confirm identity. Repeated formats can reuse the same labelled snapshot. Upstream CAPTCHA/rate limits are not local Docker failures; use show to compare identical saved data.",
        [
            'web search \'"KAMDEM Ivann" OR "Ivann Kamdem" site:github.com\' -n 30 -p 5',
            "web search '\"memory scheduling\" filetype:pdf after:2023 -slides' -e 'google cse' -p 3 -f json",
            "web search privacy -z surface,onion -e bing,ahmia -n 20 -p 4 -R /tmp/privacy-sources.html",
        ],
    ),
    "engines": (
        "Inspect the configured backend catalogue and categories without querying each provider. Default-enabled, contributor availability and current cooldown are different concepts. Use search's engine-coverage snapshot for observed contributions; a catalogue name alone does not prove the provider currently works.",
        [
            "web engines -r 'google|brave|yahoo' -f json",
            "web engines -z onion -r 'ahmia|torch'",
            "web engines -f json | jq '.data.engines[] | select(.paging == true) | .name'",
        ],
    ),
    "fetch": (
        "Download one resource once, classify its MIME/access state, extract static content/links and optionally inspect CSS/regex spans or preserve exact bytes. HTTP 200 login pages are not treated as verified source content. JavaScript is not executed; use browser-proxy independently for authorized browser work. Saved output can itself contain sensitive retrieved data.",
        [
            "web fetch https://example.com -s 'p' -r '(?i)example|documentation' -R /tmp/inspection.html",
            "web fetch https://authorized.example/private -C /private/cookies.txt -H @/private/headers.json -f json",
            "web fetch https://public.example/paper.pdf -d /tmp/paper.pdf -b 20000000 -N",
        ],
    ),
    "crawl": (
        "Explore same-host static links with depth/page budgets, robots policy and pacing. Next links are prioritized; scroll/click/SPA loaders are not executed. It shares fetch's scoped transport, so link extraction never silently uses another proxy or downloads the page twice. Authenticated GET can still have side effects: review exclusions and use a dedicated session.",
        [
            "web crawl https://quotes.toscrape.com -D 3 -n 4 -w 1 -d /tmp/quotes-evidence",
            "web crawl https://authorized.example/docs -C /private/cookies.json -x '/logout|/calendar/' -r '(?i)privacy|retention' -d /tmp/relevant-pages",
            "web crawl http://127.0.0.1:8000 -a -D 2 -n 12 --no-robots -R /tmp/local-fixture.html",
        ],
    ),
    "doc": (
        "Inspect local document text, authorship metadata, byte hash and extracted contact candidates. Repeated --compare files produce lexical spans and byte equality, NOT a plagiarism verdict or semantic equivalence. OCR is local. --online explicitly discloses sampled words and separately checks retrieved candidates; blocked searches/pages must remain partial rather than proving originality or absence of leaks.",
        [
            "web doc public-report.pdf -c draft.docx -c other.pdf -O -p 3 -R /tmp/local-comparison.pdf",
            "web doc published-paper.md -o -q exact -s 4 -n 8 -f json",
            "web doc browser-export.html -c source.txt -N -f json",
        ],
    ),
    "image": (
        "Inspect original image metadata locally. --online submits a temporary EXIF-cleared pixel copy to requested visual adapters; provider blocks/empty output do not prove absent copies. Optional OCR-text search is a separate, explicitly disclosed discovery method, not visual equality or facial identity confirmation. A URL input downloads the image even without reverse upload.",
        [
            "web image ./photo.jpg -N -f json",
            "web image ./public-logo.png -o -e yandex,bing -t -n 5 -R /tmp/image-evidence.html",
            "web image https://www.python.org/static/community_logos/python-logo-master-v3-TM.png -o -t -f json",
        ],
    ),
    "audio": (
        "Identify an original recording using free SongRec/Shazam fingerprinting. Local FFmpeg prepares an excerpt; microphone/monitor capture is explicit. hum tries the same engine and always remains qualified best effort, not a melody recognizer. No ACRCloud, paid key or speech transcription is used. Native tools must be installed separately; no audio device opens during help.",
        [
            "web audio ./recording.mp3 -O 45 -d 12 -f json",
            "web audio --record 12 --source default",
            "web audio ./hummed-melody.wav --mode hum -N -f json",
        ],
    ),
    "similar": (
        "Discover alternatives with a transparent text query derived from the site/domain. It reuses ordinary search target/cache/provider handling; it is NOT an embeddings-based similar-page API and does not verify that candidates have equivalent capabilities.",
        [
            "web similar github.com -n 12 -e yahoo -f json",
            "web similar https://www.openstreetmap.org -n 8",
            "web similar wikipedia.org -n 6 -f md",
        ],
    ),
    "doctor": (
        "Read-only readiness checks for the configured local backend and frontend. --live adds an external canary and consumes provider tolerance. A healthy catalogue proves local API readiness, not every engine's quality/availability. This command never restarts Docker, changes VPN/firewall rules or solves CAPTCHA.",
        [
            "web doctor -f json",
            "web doctor --live",
            "web doctor -f json | jq '.data.checks[] | {check,state,transport}'",
        ],
    ),
    "capabilities": (
        "Report installed native-tool presence and honest implemented boundaries without opening media or querying external indexes. Presence is not a functional hardware/provider test. Use this to distinguish missing OCR/audio/font tools from unsupported JS, semantic matching or reliable free humming.",
        [
            "web capabilities -f json",
            "web capabilities -f json | jq '.data.native | to_entries[] | select(.value == false)'",
            "web capabilities -f md",
        ],
    ),
    "setup": (
        "Create an owner-only configuration directory and config.py if absent; never overwrite operator SETTINGS. It does not install native tools, start Docker or activate API billing. Existing legacy credentials are not loaded. Runtime data/backend setup is separately exposed by Make targets.",
        [
            "web setup",
            "WEB_CONFIG_DIR=/tmp/web-lab/web web setup",
            'XDG_CONFIG_HOME="$HOME/Research/config" web setup',
        ],
    ),
    "purge": (
        "Preview owned runtime paths by default. --yes trashes owned state only, refuses an active gateway, symlinks and foreign owners, and keeps source/shared tools/arbitrary downloads. For full removal use the documented Make lifecycle: backend volumes require confirmation and a prior private backup. Preview before deleting any evidence.",
        [
            "web purge",
            "make backend-down && web purge --yes",
            "WEB_RESULTS_DIR=/tmp/web-results web purge",
        ],
    ),
    "map_search": (
        "Geocode a place/address through the configured Nominatim-compatible endpoint. Native JSON parameters refine country/viewbox/address details. Manual public use is cached/throttled; no autocomplete/bulk harvesting. A name match is not proof that the returned location is the intended one; inspect coordinates and provider attribution.",
        [
            "web map search 'École polytechnique, Palaiseau' -P '{\"limit\":2,\"addressdetails\":1}'",
            'web map search Paris -P \'{"countrycodes":"fr","limit":3}\' -f json',
            "web map search 'bicycle repair Palaiseau' -P @geocode-params.json -f json",
        ],
    ),
    "map_query": (
        "Execute raw Overpass QL against OSM features/geometry. Unlike map search it queries tags and spatial relationships, not an address geocoder. Keep regions/time bounded and observe shared-server limits. Tags such as opening_hours may be absent/outdated; this does not provide Google reviews or live traffic.",
        [
            "web map query '[out:json][timeout:20];nwr(around:1000,48.7128,2.2107)[shop=bicycle];out center;'",
            "web map query '[out:json][timeout:20];nwr(around:800,48.7128,2.2107)[amenity=drinking_water];out center;' -f json",
            "web map query @bounded-poi-query.overpass -f json",
        ],
    ),
    "map_route": (
        "Route an ordered path of place names and/or [longitude,latitude] vertices through BRouter. All intermediate vertices are retained; names are locally biased to reduce homonym errors, and resolved coordinates are returned for checking. Profile/options are provider-defined values. Distance/time/ascent are estimates, not current road/safety guarantees.",
        [
            'web map route \'["Palaiseau","Bièvres","Versailles"]\' -p trekking',
            "web map route '[[2.2107,48.7128],[2.217,48.755],[2.13,48.8]]' -P '{\"alternativeidx\":1}'",
            'web map route @waypoints.json -p trekking -P \'{"format":"gpx"}\' -f json',
        ],
    ),
    "map_request": (
        "Call an explicitly chosen map JSON API with native query/body data. This is the escape hatch for provider capabilities not wrapped by search/query/route; changing a URL does not translate incompatible protocols. POST can mutate your API: authorize it first. No Google token is configured automatically, and no credential URL query is logged on failure.",
        [
            'web map request https://nominatim.openstreetmap.org/reverse -P \'{"lat":48.7128,"lon":2.2107,"format":"jsonv2"}\'',
            'web map request https://brouter.de/brouter -P \'{"lonlats":"2.2107,48.7128|2.215,48.715","profile":"trekking","format":"geojson"}\'',
            "web map request https://overpass-api.de/api/interpreter -P @overpass-get-params.json",
        ],
    ),
    "show": (
        "Re-render a saved web envelope without network, new collection or re-ranking. This is the correct way to compare table and JSON: two separate live searches may have different provider responses. Snapshot timestamps/provenance are preserved; it does not prove that an old source remains available.",
        [
            "web show /tmp/web-results/search_SNAPSHOT.json",
            "web show /tmp/web-results/search_SNAPSHOT.json -f json | jq '.data.engine_coverage'",
            "web show /tmp/web-results/doc_SNAPSHOT.json -f table",
        ],
    ),
    "archive": (
        "Disclose an explicit public URL to Wayback's availability API and return the closest archived capture. It does not upload a local document, enumerate full history, query Archive.today or prove a byte-identical file existed. HTTP 429/failure remains unknown, never 'not archived'.",
        [
            "web archive https://www.python.org/",
            'web archive https://www.openstreetmap.org/ -P \'{"timestamp":"20200101"}\'',
            "web archive https://public.example/report.pdf -P @archive-params.json -f table",
        ],
    ),
}


def command(name):
    description, examples = COMMANDS[name]
    return (
        description
        + "\n\n### Examples\n\n"
        + "\n\n".join(f"```sh\n{example}\n```" for example in examples)
    )
