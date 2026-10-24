"""Budgeted search and polite bounded crawl. Neither is exhaustive."""

import asyncio
import hashlib
import math
import mimetypes
import time
from collections import deque
from dataclasses import asdict
from pathlib import Path
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import regex as re

from .backend import SurfaceSearcher
from .http import Session, WebError, canonical, host_matches, save_bytes
from .user_config import settings


async def _search(
    query,
    *,
    engines=None,
    pages=1,
    page=1,
    limit=20,
    site=None,
    regex=None,
    categories=None,
    language="all",
    safe=0,
    timeout=30.0,
    params=None,
    rank="provider",
    source=None,
):
    if pages < 1 or page < 1 or limit < 0:
        raise WebError(
            "Pages/page must be positive; limit=0 means all results in the fetched page budget"
        )
    pattern = re.compile(regex, re.I) if regex else None
    source = source or SurfaceSearcher()
    if engines:
        names = {row["name"] for row in (await source.get_engines())["engines"]}
        unknown = set(engines.split(",")) - names
        if unknown:
            raise WebError(
                f"Unknown engines: {sorted(unknown)}. Run web engines; no default-engine fallback was used"
            )
    effective = f"{query} site:{site}" if site else query
    found, failures, upstream, seen = [], [], [], set()
    tokens = re.findall(
        r"\w+",
        re.sub(
            r"\b(?:site|filetype|intitle|inurl|before|after):\S+|\b(?:OR|AND|NOT)\b|-\w+",
            "",
            query,
        ).casefold(),
    )
    if rank not in {"provider", "lexical"}:
        raise WebError(
            "rank must be provider or lexical (a heuristic, not identity attribution)"
        )
    attempted_pages = []
    for current in range(page, page + pages):
        attempted_pages.append(current)
        try:
            rows = await source.search(
                effective,
                engines=engines,
                categories=categories,
                language=language,
                page=current,
                limit=0,
                safe_search=safe,
                timeout=timeout,
                extra=params,
            )
            upstream.extend(source.unresponsive_engines)
        except Exception as error:
            failures.append({"page": current, "error": str(error)})
            continue
        if not rows:
            break
        for row in rows:
            item = asdict(row)
            key = canonical(item["url"])
            if key in seen or (site and not host_matches(key, site)):
                continue
            if pattern and not pattern.search(
                " ".join((item["title"], item["snippet"], key)),
                timeout=settings()["regex_timeout"],
            ):
                continue
            seen.add(key)
            text = f"{item['title']} {item['snippet']} {key}".casefold()
            item["lexical_relevance"] = sum(token in text for token in tokens) / max(
                1, len(tokens)
            )
            found.append(item)
        await asyncio.sleep(0.2)
    if rank == "lexical":
        found.sort(key=lambda row: row["lexical_relevance"], reverse=True)
    if failures and not found:
        raise WebError("Search failed: " + "; ".join(row["error"] for row in failures))
    return {
        "query": query,
        "effective_query": effective,
        "non_exhaustive": True,
        "page_budget": pages,
        "attempted_pages": attempted_pages,
        "rank": rank,
        "limit": limit,
        "unique_candidates": len(found),
        "results": found[:limit] if limit else found,
        "failures": failures,
        "upstream_issues": upstream,
        "partial": bool(failures or upstream),
    }


async def search(query, *, engines=None, network=None, limit=20, **kwargs):
    """Merge independent SearXNG backends without coupling their availability."""
    if limit < 0:
        raise WebError("Limit must be nonnegative (0 means all fetched candidates)")
    hidden = set(settings().get("onion_engines", ["ahmia", "torch"]))
    wanted = engines.split(",") if engines else []
    channels = (
        network.split(",")
        if network
        else (
            ["surface"]
            if not wanted
            else list(
                dict.fromkeys(
                    "onion" if name in hidden else "surface" for name in wanted
                )
            )
        )
    )
    merged, failures, metadata, seen = [], [], [], set()
    resolved_engines = set()
    for channel in channels:
        selected = (
            wanted
            if network
            else [name for name in wanted if (name in hidden) == (channel == "onion")]
        )
        try:
            source = (
                SurfaceSearcher()
                if channel == "surface"
                else SurfaceSearcher(service=channel)
            )
            if network and len(channels) > 1 and wanted:
                names = {row["name"] for row in (await source.get_engines())["engines"]}
                selected = [name for name in wanted if name in names]
                resolved_engines.update(selected)
                if not selected:
                    continue
            options = dict(kwargs)
            if channel == "onion" and not options.get("categories"):
                options["categories"] = "onions"
            result = await _search(
                query,
                engines=",".join(selected) or None,
                limit=0,
                source=source,
                **options,
            )
            metadata.append(
                {key: value for key, value in result.items() if key != "results"}
            )
            for row in result["results"]:
                key = canonical(row["url"])
                if key not in seen:
                    seen.add(key)
                    merged.append({**row, "network": channel})
        except Exception as error:
            failures.append(
                {
                    "network": channel,
                    "error": str(error),
                    "action": "Simplify regex or adjust regex_timeout"
                    if isinstance(error, TimeoutError)
                    else "Run make onion-up in searxng; surface remains independent"
                    if channel == "onion"
                    else "Run web doctor and inspect query/engine/regex configuration",
                }
            )
    if network and len(channels) > 1 and set(wanted) - resolved_engines:
        failures.append(
            {
                "network": "selection",
                "error": f"Unknown or unresolved requested engines: {sorted(set(wanted) - resolved_engines)}",
                "action": "Inspect each backend with web engines --network NAME; no fallback was used",
            }
        )
    if failures and not merged:
        raise WebError(json_errors(failures))
    if kwargs.get("rank") == "lexical":
        merged.sort(key=lambda row: row["lexical_relevance"], reverse=True)
    base = metadata[0] if metadata else {"query": query, "non_exhaustive": True}
    return {
        **base,
        "limit": limit,
        "results": merged[:limit] if limit else merged,
        "unique_candidates": len(merged),
        "backends": metadata,
        "backend_failures": failures,
        "partial": bool(failures) or any(row["partial"] for row in metadata),
    }


def json_errors(failures):
    return "; ".join(
        f"{row['network']}: {row['error']}; {row['action']}" for row in failures
    )


def crawl(
    url,
    session: Session,
    *,
    depth=1,
    max_pages=20,
    delay=0.5,
    robots=True,
    directory=None,
    include=None,
    exclude=None,
):
    if depth < 0 or max_pages < 1 or delay < 0 or not math.isfinite(delay):
        raise WebError("depth/delay must be nonnegative and max-pages positive")
    host = urlsplit(url).hostname
    session.allowed_host = host
    matcher = re.compile(include) if include else None
    exclusion = settings()["crawl_exclude_regex"] if exclude is None else exclude
    denied = re.compile(exclusion) if exclusion else None
    policy = RobotFileParser()
    if robots:
        root = f"{urlsplit(url).scheme}://{urlsplit(url).netloc}/robots.txt"
        try:
            _, _, body = session.get(root)
            policy.parse(body.decode(errors="replace").splitlines())
        except WebError as error:
            if "HTTP 404" not in str(error):
                raise WebError(
                    f"robots.txt could not be checked: {error}. Review policy or explicitly use --no-robots"
                ) from None
            policy.parse([])
    queue, visited, results, errors = deque([(url, 0)]), set(), [], []
    while queue and len(visited) < max_pages:
        current, level = queue.popleft()
        identity = canonical(current)
        if identity in visited:
            continue
        visited.add(identity)
        if denied and denied.search(current, timeout=settings()["regex_timeout"]):
            errors.append({"url": current, "reason": "url_policy_excluded"})
            continue
        if robots and not policy.can_fetch("k-web", current):
            errors.append({"url": current, "reason": "robots_disallowed"})
            continue
        try:
            record, body = session.fetch(current)
            if urlsplit(record["url"]).hostname != host:
                errors.append(
                    {"url": current, "reason": "cross_host_redirect_not_traversed"}
                )
                continue
            if directory and (
                not matcher
                or matcher.search(record["text"], timeout=settings()["regex_timeout"])
            ):
                record["download"] = save_bytes(
                    Path(directory)
                    / (
                        hashlib.sha256(current.encode()).hexdigest()[:24]
                        + (mimetypes.guess_extension(record["mime"]) or ".bin")
                    ),
                    body,
                )
            results.append(record)
            if level < depth and record["access_state"] == "ok":
                for link in record["links"]:
                    if urlsplit(link).hostname != host:
                        continue
                    if link in record.get("pagination_links", []):
                        queue.appendleft((link, level + 1))
                    else:
                        queue.append((link, level + 1))
        except (WebError, OSError) as error:
            errors.append({"url": current, "reason": str(error)})
        time.sleep(delay)
    return {
        "seed": url,
        "attempted": len(visited),
        "pages": results,
        "errors": errors,
        "remaining_frontier": len(queue),
        "partial": bool(errors)
        or any(p["access_state"] not in {"ok", "binary"} for p in results),
    }
