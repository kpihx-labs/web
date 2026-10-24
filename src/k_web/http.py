"""Single bounded HTTP/session pipeline for fetch, crawl and downloads."""

import hashlib
import http.cookiejar
import ipaddress
import json
import math
import os
import socket
import time
import urllib.request
from pathlib import Path
from urllib.parse import unquote_plus, urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup
from requests.cookies import create_cookie

from .models import extract_osint_entities
from .user_config import settings


def canonical(url):
    parts = urlsplit(url)
    query = [
        segment
        for segment in parts.query.split("&")
        if not unquote_plus(segment.partition("=")[0]).lower().startswith("utm_")
        and unquote_plus(segment.partition("=")[0]).lower() not in {"fbclid", "gclid"}
    ]
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path or "/",
            "&".join(query),
            "",
        )
    )


def host_matches(url, domain):
    host = (urlsplit(url).hostname or "").lower()
    domain = domain.lower().lstrip(".")
    return host == domain or host.endswith("." + domain)


class WebError(RuntimeError):
    pass


class Session:
    def __init__(
        self,
        seed,
        *,
        cookies=None,
        headers=(),
        proxy=None,
        timeout=30.0,
        max_bytes=None,
        allow_private=False,
    ):
        self.seed = urlsplit(seed).hostname
        if urlsplit(seed).username is not None:
            raise WebError(
                "Credential-bearing URLs are refused; use scoped cookie/header files instead"
            )
        initial = urlsplit(seed)
        self.origin = (
            initial.scheme,
            initial.hostname,
            initial.port or (443 if initial.scheme == "https" else 80),
        )
        self.allowed_host: str | None = None
        self.client = requests.Session()
        self.client.trust_env = False
        self.client.cookies.set_policy(
            http.cookiejar.DefaultCookiePolicy(
                strict_ns_domain=http.cookiejar.DefaultCookiePolicy.DomainStrictNonDomain
            )
        )
        self.client.headers["User-Agent"] = settings()["user_agent"]
        self.timeout, self.max_bytes, self.proxy, self.allow_private = (
            timeout,
            max_bytes if max_bytes is not None else settings()["response_max_bytes"],
            proxy,
            allow_private,
        )
        self.headers = {}
        for item in headers:
            if item.startswith("@"):
                self.headers.update(json.loads(Path(item[1:]).read_text()))
                continue
            if ":" not in item:
                raise WebError(
                    "Headers must be 'Name: Value'; never put credentials in shell history"
                )
            key, value = item.split(":", 1)
            self.headers[key.strip()] = value.strip()
        if cookies:
            path = Path(cookies)
            try:
                data = json.loads(path.read_text())
            except json.JSONDecodeError:
                jar = http.cookiejar.MozillaCookieJar(str(path))
                jar.load(ignore_discard=True)
                self.client.cookies.update(jar)
            else:
                records = data.get("cookies", data) if isinstance(data, dict) else data
                if isinstance(records, dict):
                    records = [
                        {"name": k, "value": v, "domain": self.seed}
                        for k, v in records.items()
                    ]
                for row in records:
                    cookie = create_cookie(
                        row["name"],
                        row["value"],
                        domain=row.get("domain") or self.seed,
                        path=row.get("path", "/"),
                        secure=row.get("secure", False),
                        expires=int(row["expires"])
                        if row.get("expires", -1) > 0
                        else None,
                    )
                    cookie.domain_specified = not row.get(
                        "hostOnly", not cookie.domain.startswith(".")
                    )
                    self.client.cookies.set_cookie(cookie)

    def validate(self, url, via_proxy=False):
        parts = urlsplit(url)
        if (
            parts.scheme not in {"http", "https"}
            or not parts.hostname
            or parts.username is not None
        ):
            raise WebError("Only credential-free HTTP(S) URLs are accepted")
        hidden = parts.hostname.endswith((".onion", ".i2p"))
        if not hidden and not self.allow_private and not via_proxy:
            try:
                addresses = socket.getaddrinfo(
                    parts.hostname, parts.port or 443, type=socket.SOCK_STREAM
                )
            except OSError:
                raise WebError(
                    "DNS lookup failed; check network/VPN and hostname"
                ) from None
            if any(
                not ipaddress.ip_address(address[4][0]).is_global
                for address in addresses
            ):
                raise WebError(
                    "Private/local destination refused; explicitly use --allow-private for your own services"
                )
        return parts

    def get(self, url):
        if not math.isfinite(self.timeout) or self.timeout <= 0 or self.max_bytes <= 0:
            raise WebError("Timeout and max-bytes must be positive")
        deadline = time.monotonic() + self.timeout
        proxy = self.proxy
        for _ in range(settings()["max_redirects"]):
            destination = urlsplit(url).hostname or ""
            if destination.endswith(".onion"):
                proxy = proxy or settings()["tor_proxy"]
            if destination.endswith(".i2p"):
                proxy = proxy or settings().get("i2p_proxy", "http://127.0.0.1:4444")
            parts = self.validate(url, via_proxy=bool(proxy))
            if self.allowed_host is not None and self.allowed_host != parts.hostname:
                raise WebError(
                    "Cross-host redirect refused by crawl scope before retrieval"
                )
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise WebError("HTTP redirect/transfer deadline exceeded")
            origin = (
                parts.scheme,
                parts.hostname,
                parts.port or (443 if parts.scheme == "https" else 80),
            )
            headers = dict(self.headers) if origin == self.origin else {}
            cookie_request = urllib.request.Request(url)
            self.client.cookies.add_cookie_header(cookie_request)
            # Prevent requests from merging a second, less-strict cookie jar.
            headers.setdefault("Cookie", cookie_request.get_header("Cookie", ""))
            response = None
            try:
                response = self.client.get(
                    url,
                    headers=headers,
                    proxies={"http": proxy, "https": proxy} if proxy else {},
                    timeout=remaining,
                    stream=True,
                    allow_redirects=False,
                )
                if response.is_redirect:
                    target = urljoin(url, response.headers["Location"])
                    response.close()
                    url = target
                    continue
                if response.status_code >= 400:
                    code = response.status_code
                    response.close()
                    raise WebError(
                        f"HTTP {code}; retry later or use an authorized browser session. No TLS/access-control bypass was attempted"
                    )
                body = bytearray()
                for chunk in response.iter_content(65536):
                    body.extend(chunk)
                    if time.monotonic() > deadline:
                        raise WebError("Transfer deadline exceeded")
                    if len(body) > self.max_bytes:
                        raise WebError(
                            "Response exceeds --max-bytes; increase the explicit resource budget"
                        )
                mime = response.headers.get(
                    "Content-Type", "application/octet-stream"
                ).split(";")[0]
                response.close()
                return url, mime, bytes(body)
            except requests.RequestException as error:
                raise WebError(
                    f"{type(error).__name__}: check DNS, proxy/Tor/I2P and connectivity; no direct fallback was used"
                ) from None
            finally:
                if response is not None:
                    response.close()
        raise WebError(
            f"Too many redirects (configured maximum {settings()['max_redirects']})"
        )

    def fetch(self, url):
        final, mime, body = self.get(url)
        result = {
            "requested_url": url,
            "url": final,
            "mime": mime,
            "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
            "access_state": "binary",
            "title": "",
            "text": "",
            "links": [],
            "entities": {},
        }
        if "html" in mime:
            soup = BeautifulSoup(body, "html.parser")
            result["title"] = soup.title.get_text(" ", strip=True) if soup.title else ""
            links = []
            for node in soup.select("a[href]"):
                target = urljoin(final, str(node["href"]))
                if (
                    urlsplit(target).scheme in {"http", "https"}
                    and urlsplit(target).username is None
                ):
                    next_page = "next" in str(node.get("rel") or "") or node.get_text(
                        strip=True
                    ).casefold().startswith(("next", "suivant", "older", "»", "›"))
                    links.append((next_page, target.split("#", 1)[0]))
            result["links"] = list(
                dict.fromkeys(
                    target
                    for _, target in sorted(links, key=lambda row: row[0], reverse=True)
                )
            )
            result["pagination_links"] = list(
                dict.fromkeys(target for is_next, target in links if is_next)
            )
            password = bool(soup.select('input[type="password"]'))
            scripted = bool(soup.select("script"))
            title = result["title"].lower()
            wall = any(
                word in title
                for word in (
                    "sign up",
                    "signup",
                    "sign in",
                    "login",
                    "just a moment",
                    "access denied",
                    "captcha",
                )
            )
            for node in soup.select("script,style,noscript,template"):
                node.decompose()
            main = soup.select_one("article, main") or soup
            text = main.get_text("\n", strip=True)
            result.update(
                text=text,
                access_state="auth_required"
                if wall or (password and len(text) < 200)
                else "javascript_required"
                if scripted and len(text) < 80
                else "ok",
            )
        elif mime.startswith("text/") or mime.endswith("json"):
            result.update(
                text=body.decode("utf-8", errors="replace"), access_state="ok"
            )
        result["entities"] = extract_osint_entities(result["text"])
        result["access_classification"] = (
            "heuristic; inspect content before treating a page as verified evidence"
        )
        return result, body


def save_bytes(path, body):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(body)
    path.chmod(0o600)
    return str(path)
