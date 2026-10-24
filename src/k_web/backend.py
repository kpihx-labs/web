"""SearXNG boundary: bounded retries, validated responses and actionable failures."""

import asyncio
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from .config import CONFIG
from .user_config import settings


class BackendError(RuntimeError):
    """Backend failure, never interchangeable with a valid empty result set."""

    def __init__(self, code: str, endpoint: str, detail: str):
        self.code = code
        self.endpoint = endpoint
        self.detail = detail
        self.action = (
            "Providers are limited/blocked, not Docker. Respect cooldowns, use an available engine (-e), "
            "or reuse a labelled cached snapshot. Restarting Docker/VPN is not the remedy."
            if code.startswith("UPSTREAM_")
            else "Run web doctor and make health in searxng; use make recover only for a confirmed local service/network failure."
        )
        super().__init__(f"{code}: {endpoint}: {detail}\n{self.action}")


class SurfaceSearcher:
    """Preserve the search API while exposing failures and upstream degradation."""

    def __init__(self, base_url=None, *, transport=None, service="surface"):
        options = settings()
        registry = {
            "surface": {},
            "onion": {
                "url": "http://127.0.0.1:8082",
                "socket": str(Path(CONFIG.searxng_socket).with_name("onion.sock")),
            },
            **options.get("search_backends", {}),
        }
        if service not in registry:
            raise ValueError(
                "Unknown search backend; configure search_backends in web/config.py"
            )
        profile = registry[service]
        if not isinstance(profile, dict):
            raise ValueError(
                "search_backends entries must be dictionaries with url/socket/proxy fields"
            )
        self.proxy = profile.get("proxy")
        self.base_url = (
            base_url
            or profile.get("url")
            or options.get("searxng_url", CONFIG.searxng_url)
        ).rstrip("/")
        parsed = urlsplit(self.base_url)
        if (parsed.hostname or "").endswith((".onion", ".i2p")) and not self.proxy:
            raise ValueError(
                "A hidden-service backend requires an explicit proxy in search_backends; no local DNS request was made"
            )
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "searxng_url must be an HTTP(S) base URL without credentials or query."
            )
        self.transport = transport
        socket_path = profile.get("socket")
        mode = profile.get(
            "transport",
            options.get("searxng_transport", "auto")
            if service == "surface"
            else "auto",
        )
        if service == "surface" and "socket" not in profile:
            socket_path = options.get("searxng_socket", CONFIG.searxng_socket)
            if (
                self.base_url != CONFIG.searxng_url
                and socket_path == CONFIG.searxng_socket
                and mode != "unix"
            ):
                socket_path = None
        if mode not in {"auto", "tcp", "unix"}:
            raise BackendError(
                "BACKEND_CONFIG_ERROR",
                self.base_url,
                "searxng_transport must be auto, unix or tcp",
            )
        self.socket_path = None
        if (
            transport is None
            and base_url is None
            and mode != "tcp"
            and socket_path is not None
            and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
            and (mode == "unix" or Path(socket_path).is_socket())
        ):
            self.socket_path = str(socket_path)
            parent = Path(socket_path).parent.stat()
            if parent.st_uid != os.getuid() or parent.st_mode & 0o077:
                raise BackendError(
                    "IPC_PERMISSIONS",
                    self.base_url,
                    "Socket directory must be owned by you and mode 0700. Run make prepare in your searxng project",
                )
        self.channel = "unix" if self.socket_path else "tcp"
        self.attempts = max(1, int(options.get("search_attempts", 3)))
        self.retry_delay = max(0.0, float(options.get("search_retry_delay", 0.3)))
        self.unresponsive_engines = []

    async def request(self, path, params=None, timeout=30.0, headers=None):
        if timeout <= 0:
            raise ValueError("Search timeout must be positive.")
        endpoint = f"{self.base_url}{path}"
        last = "Backend connection failed"
        try:
            async with asyncio.timeout(timeout):
                for attempt in range(self.attempts):
                    try:
                        async with httpx.AsyncClient(
                            timeout=httpx.Timeout(timeout, connect=min(3.0, timeout)),
                            trust_env=False,
                            proxy=self.proxy if not self.socket_path else None,
                            transport=self.transport
                            or (
                                httpx.AsyncHTTPTransport(uds=self.socket_path)
                                if self.socket_path
                                else None
                            ),
                        ) as client:
                            forwarded = dict(headers or {})
                            if urlsplit(self.base_url).hostname in {
                                "localhost",
                                "127.0.0.1",
                                "::1",
                            }:
                                forwarded.setdefault("X-Real-IP", "127.0.0.1")
                            response = await client.get(
                                endpoint, params=params, headers=forwarded
                            )
                        if response.status_code in {429, 502, 503, 504}:
                            last = f"Backend returned HTTP {response.status_code}"
                        elif response.status_code != 200:
                            raise BackendError(
                                "BACKEND_HTTP_ERROR",
                                endpoint,
                                f"HTTP {response.status_code}",
                            )
                        else:
                            try:
                                data = response.json()
                            except ValueError:
                                raise BackendError(
                                    "BACKEND_INVALID_JSON",
                                    endpoint,
                                    "Expected JSON, not a proxy/login page",
                                ) from None
                            if not isinstance(data, dict):
                                raise BackendError(
                                    "BACKEND_INVALID_RESPONSE",
                                    endpoint,
                                    "Expected a JSON object",
                                )
                            return data
                    except httpx.TransportError as error:
                        # Avoid exception text containing full query strings or custom headers.
                        last = f"{type(error).__name__}; connection refused/reset, DNS or network failure"
                    if attempt + 1 < self.attempts:
                        await asyncio.sleep(self.retry_delay * 2**attempt)
        except TimeoutError:
            raise BackendError(
                "BACKEND_TIMEOUT",
                endpoint,
                f"Request exceeded total deadline of {timeout:g}s",
            ) from None
        raise BackendError("BACKEND_UNREACHABLE", endpoint, last)

    async def get_engines(self):
        data = await self.request("/config", timeout=10)
        if not isinstance(data.get("engines"), list) or not data["engines"]:
            raise BackendError(
                "BACKEND_EMPTY_CATALOG",
                self.base_url,
                "HTTP succeeded but the engine catalogue is missing/empty",
            )
        return data

    async def search(
        self,
        query,
        engines=None,
        categories=None,
        language="all",
        page=1,
        safe_search=0,
        time_range=None,
        limit=20,
        timeout=CONFIG.default_timeout_s,
        custom_headers=None,
        extra=None,
    ):
        from .models import SearchResult, extract_osint_entities

        if page < 1 or limit < 0 or safe_search not in (0, 1, 2):
            raise ValueError(
                "Page and limit must be positive; safe-search must be 0, 1 or 2."
            )
        params = {
            "q": query,
            "format": "json",
            "pageno": page,
            "safesearch": safe_search,
            "language": language,
        }
        for name, value in (
            ("engines", engines),
            ("categories", categories),
            ("time_range", time_range),
        ):
            if value:
                params[name] = value
        if extra:
            if {"q", "format", "pageno"} & extra.keys():
                raise ValueError(
                    "Raw params cannot replace q/format; use the query argument and --format"
                )
            params.update(extra)
        data = await self.request("/search", params, timeout, custom_headers)
        raw = data.get("results")
        if not isinstance(raw, list) or any(not isinstance(item, dict) for item in raw):
            raise BackendError(
                "BACKEND_INVALID_RESULTS",
                self.base_url,
                "Response has no valid results array",
            )
        self.unresponsive_engines = data.get("unresponsive_engines", [])
        if self.unresponsive_engines:
            failed = "; ".join(str(item) for item in self.unresponsive_engines)
            if not raw:
                raise BackendError(
                    "UPSTREAM_SEARCH_FAILED",
                    self.base_url,
                    f"No results and upstream engine failures: {failed}. Try another engine (-e), or retry later; do not infer absence.",
                )
            print(f"Warning: partial upstream coverage: {failed}", file=sys.stderr)
        results = []
        for row in raw[:limit] if limit else raw:
            entities = extract_osint_entities(
                f"{row.get('title', '')} {row.get('content', '')}"
            )
            results.append(
                SearchResult(
                    title=row.get("title", ""),
                    url=row.get("url", ""),
                    snippet=row.get("content", ""),
                    source=f"searxng:{row.get('engine', 'unknown')}",
                    engine=row.get("engine", "unknown"),
                    category="onion"
                    if (urlsplit(row.get("url", "")).hostname or "").endswith(".onion")
                    else "surface",
                    timestamp=datetime.now(UTC).isoformat(),
                    score=float(row.get("score") or 0),
                    engines=row.get("engines", [row.get("engine", "unknown")]),
                    provider_fields=row,
                    extracted_emails=entities["emails"],
                    extracted_phones=entities["phones"],
                )
            )
        return results
