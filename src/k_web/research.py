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

from . import __version__, search_cache
from .backend import BackendError, SurfaceSearcher
from .http import Session, WebError, canonical, host_matches, save_bytes
from .user_config import settings


def contributors(row):
    return list(
        dict.fromkeys(
            [
                *(row.get("sources") or []),
                *(row.get("engines") or []),
                *([row["engine"]] if row.get("engine") else []),
            ]
        )
    )


def merge_provenance(existing, incoming):
    existing["sources"] = list(
        dict.fromkeys(contributors(existing) + contributors(incoming))
    )
    existing["engines"] = existing["sources"]
    existing["score"] = max(existing.get("score", 0), incoming.get("score", 0))


def issue_state(issues):
    text = " ".join(str(item).lower() for item in issues)
    for needle, label in (
        ("too many", "rate_limited"),
        ("captcha", "captcha"),
        ("access denied", "access_denied"),
        ("timeout", "timeout"),
        ("suspended", "suspended"),
    ):
        if needle in text:
            return label
    return "error" if issues else "no_results_reported"


async def _search(
    query,
    *,
    engines=None,
    pages=None,
    page=1,
    limit=20,
    site=None,
    regex=None,
    categories=None,
    language="all",
    safe=0,
    timeout=30.0,
    params=None,
    rank="relevance",
    source=None,
):
    pages = settings()["search_max_pages"] if pages is None else pages
    if pages < 1 or page < 1 or limit < 0:
        raise WebError(
            "Pages/page must be positive; limit=0 means all results in the fetched page budget"
        )
    pattern = re.compile(regex, re.I) if regex else None
    source = source or SurfaceSearcher()
    params = dict(params or {})
    if "engines" in params:
        value = params.pop("engines")
        native_engines = ",".join(value) if isinstance(value, list) else value
        if engines and native_engines != engines:
            raise WebError("Conflicting engine lists in --engines and --params")
        engines = native_engines
    categories = params.get("categories", categories)
    catalogue = {row["name"]: row for row in (await source.get_engines())["engines"]}
    if engines:
        unknown = set(engines.split(",")) - catalogue.keys()
        if unknown:
            raise WebError(
                f"Unknown engines: {sorted(unknown)}. Run web engines; no default-engine fallback was used"
            )
    effective = f"{query} site:{site}" if site else query
    found, failures, upstream, seen = [], [], [], set()
    expected = (
        engines.split(",")
        if engines
        else [
            name
            for name, row in catalogue.items()
            if row.get("enabled", not row.get("disabled", False))
            and (categories or "general") in row.get("categories", ["general"])
        ]
    )
    sightings = {}
    issues_by_engine = {}
    by_url = {}
    batches = []
    tokens = re.findall(
        r"\w+",
        re.sub(
            r"\b(?:site|filetype|intitle|inurl|before|after):\S+|\b(?:OR|AND|NOT)\b|-\w+",
            "",
            query,
        ).casefold(),
    )
    if rank not in {"provider", "lexical", "relevance"}:
        raise WebError(
            "rank must be relevance, provider or lexical (heuristics, not identity attribution)"
        )
    attempted_pages = []
    stop_reason = "page_budget_reached"
    fallback = None
    fallback_used = []
    current = page
    while len(attempted_pages) < pages:
        stop_reason = "page_budget_reached"
        attempted_pages.append(current)
        batches.append(
            {"page": current, "engines": fallback or engines or "backend defaults"}
        )
        try:
            source.unresponsive_engines = []
            rows = await source.search(
                effective,
                engines=fallback or engines,
                categories=categories,
                language=language,
                page=current,
                limit=0,
                safe_search=safe,
                timeout=timeout,
                extra=params,
            )
        except Exception as error:
            failures.append(
                {
                    "page": current,
                    "code": getattr(error, "code", "SEARCH_FAILED"),
                    "error": str(error),
                }
            )
            rows = []
            stop_reason = (
                "providers_unavailable"
                if isinstance(error, BackendError)
                and error.code.startswith("UPSTREAM_")
                else "backend_failed"
            )
        page_issues = list(getattr(source, "unresponsive_engines", []))
        upstream.extend(page_issues)
        for entry in page_issues:
            if len(entry) >= 2:
                issues_by_engine.setdefault(entry[0], []).append(str(entry[1]))
        new_candidates = 0
        for row in rows:
            item = asdict(row)
            item["sources"] = contributors(item)
            key = canonical(item["url"])
            for name in item["sources"]:
                sightings.setdefault(name, set()).add(key)
            if key in by_url:
                merge_provenance(by_url[key], item)
                continue
            new_candidates += 1
            if site and not host_matches(key, site):
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
            by_url[key] = item
        if limit and len(found) >= limit:
            stop_reason = "target_reached"
            break
        stalled = not rows or not new_candidates
        if stalled and stop_reason != "backend_failed":
            fallback_names = [
                name
                for name in settings()["fallback_engines"]
                if name in catalogue and name not in expected
            ]
            if (
                not engines
                and page == 1
                and categories in (None, "general", "web")
                and not fallback_used
                and fallback_names
                and len(attempted_pages) < pages
            ):
                fallback_used = fallback_names
                expected.extend(fallback_names)
                fallback = ",".join(fallback_names)
                current = 1
                await asyncio.sleep(settings()["search_page_delay"])
                continue
            stop_reason = (
                "providers_unavailable"
                if page_issues
                else "empty_page"
                if not rows
                else "no_new_candidates"
            )
            break
        if stop_reason == "backend_failed":
            break
        current += 1
        await asyncio.sleep(settings()["search_page_delay"])
    if rank == "lexical":
        found.sort(key=lambda row: row["lexical_relevance"], reverse=True)
    elif rank == "relevance":
        found.sort(
            key=lambda row: (row["lexical_relevance"], row.get("score", 0)),
            reverse=True,
        )
    else:
        found.sort(key=lambda row: row.get("score", 0), reverse=True)
    if failures and not found:
        raise WebError("Search failed: " + "; ".join(row["error"] for row in failures))
    coverage = [
        {
            "engine": name,
            "selected": True,
            "selection_basis": "explicit"
            if engines or name in fallback_used
            else "catalogue_default_candidate; actual invocation not exposed by backend",
            "paging": catalogue.get(name, {}).get("paging", "unknown"),
            "contributed_urls": len(sightings.get(name, set())),
            "state": "contributed_with_issues"
            if sightings.get(name) and issues_by_engine.get(name)
            else "contributed"
            if sightings.get(name)
            else issue_state(issues_by_engine.get(name, [])),
            "issues": list(dict.fromkeys(issues_by_engine.get(name, []))),
        }
        for name in dict.fromkeys(expected)
    ]
    shortfall = bool(limit and len(found) < limit)
    return {
        "query": query,
        "effective_query": effective,
        "non_exhaustive": True,
        "page_budget": pages,
        "attempted_pages": attempted_pages,
        "page_requests": batches,
        "stop_reason": stop_reason,
        "target": limit,
        "target_reached": not shortfall,
        "engine_coverage": coverage,
        "fallback_engines_used": fallback_used,
        "rank": rank,
        "limit": limit,
        "unique_candidates": len(found),
        "results": found,
        "failures": failures,
        "upstream_issues": upstream,
        "partial": bool(failures or upstream or shortfall),
    }


async def _collect(query, *, engines=None, network=None, limit=20, **kwargs):
    """Merge independent SearXNG backends without coupling their availability."""
    if limit < 0:
        raise WebError("Limit must be nonnegative (0 means all fetched candidates)")
    hidden = set(settings().get("onion_engines", ["ahmia", "torch"]))
    wanted = (
        [name.strip() for name in engines.split(",") if name.strip()] if engines else []
    )
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
                limit=limit,
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
                else:
                    existing = next(
                        item for item in merged if canonical(item["url"]) == key
                    )
                    merge_provenance(existing, row)
        except Exception as error:
            failures.append(
                {
                    "network": channel,
                    "error": str(error),
                    "action": error.action
                    if isinstance(error, BackendError)
                    else "Simplify regex or adjust regex_timeout"
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
    elif kwargs.get("rank", "relevance") == "relevance":
        merged.sort(
            key=lambda row: (row["lexical_relevance"], row.get("score", 0)),
            reverse=True,
        )
    else:
        merged.sort(key=lambda row: row.get("score", 0), reverse=True)
    base = metadata[0] if metadata else {"query": query, "non_exhaustive": True}
    return {
        **base,
        "limit": limit,
        "results": merged[:limit] if limit else merged,
        "unique_candidates": len(merged),
        "stop_reason": "target_reached"
        if limit and len(merged) >= limit
        else base.get("stop_reason", "sources_unavailable"),
        "backends": metadata,
        "backend_failures": failures,
        "partial": bool(failures) or any(row["partial"] for row in metadata),
    }


async def search(
    query, *, engines=None, network=None, limit=20, fresh=False, persist=True, **kwargs
):
    """Collect a target count, with explicitly labelled snapshots, never format-specific retrieval."""
    options = {
        "engines": engines,
        "network": network,
        "limit": limit,
        **kwargs,
        "backends": settings().get("search_backends", {}),
        "endpoint": settings().get("searxng_url"),
        "version": __version__,
        "defaults": {
            name: settings()[name] for name in ("search_max_pages", "fallback_engines")
        },
    }
    path = search_cache.location(query, options)
    if persist and not fresh:
        cached = search_cache.load(path, settings()["search_cache_ttl"])
        if cached:
            data, age = cached
            return {
                **data,
                "cache": {
                    "state": "snapshot",
                    "age_seconds": age,
                    "live_request": False,
                },
            }
    try:
        data = await _collect(
            query, engines=engines, network=network, limit=limit, **kwargs
        )
    except Exception as error:
        cached = (
            search_cache.load(path, settings()["search_stale_ttl"])
            if persist and not fresh
            else None
        )
        if not cached:
            raise
        data, age = cached
        return {
            **data,
            "partial": True,
            "cache": {
                "state": "stale_on_error",
                "age_seconds": age,
                "live_request": False,
                "error": str(error),
            },
        }
    coverage = {}
    for backend in data.get("backends", []):
        for row in backend.get("engine_coverage", []):
            if row["engine"] not in coverage:
                coverage[row["engine"]] = row
    data["engine_coverage"] = list(coverage.values())
    data["target_reached"] = not limit or len(data["results"]) >= limit
    data["partial"] = data["partial"] or not data["target_reached"]
    data["cache"] = {"state": "live", "age_seconds": 0, "live_request": True}
    if persist and data.get("results"):
        search_cache.store(path, data)
    return data


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
    if include and directory is None:
        raise WebError(
            "--match filters saved bodies; add --download-dir or omit --match. It does not filter traversal/display"
        )
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
