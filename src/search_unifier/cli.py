"""CLI interface and command-line parser for search-unifier."""

import argparse
import asyncio
import sys

from .unifier import (
    I2PSearcher,
    OnionSearcher,
    SurfaceSearcher,
    deduplicate,
    output_results,
)


async def main_async():
    parser = argparse.ArgumentParser(
        prog="search-unifier",
        description="Unified sovereign search engine across Surface Web + Tor .onion + I2P .i2p",
    )
    parser.add_argument("query", help="Search query string")
    parser.add_argument(
        "--surface",
        dest="surface",
        action="store_true",
        default=True,
        help="Query Surface web through local SearXNG (default: active)",
    )
    parser.add_argument(
        "--no-surface",
        dest="surface",
        action="store_false",
        help="Disable Surface web query",
    )
    parser.add_argument(
        "--onion",
        action="store_true",
        default=False,
        help="Query Dark web (.onion) via live Tor SOCKS5",
    )
    parser.add_argument(
        "--i2p",
        action="store_true",
        default=False,
        help="Query I2P network (eepsites)",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["json", "csv", "md"],
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Max results per network category (default: 10)",
    )
    parser.add_argument(
        "--engines",
        help="Comma-separated surface engines (e.g. brave,bing,wikipedia)",
    )
    parser.add_argument(
        "--no-dedup",
        dest="dedup",
        action="store_false",
        default=True,
        help="Disable deterministic deduplication",
    )

    args = parser.parse_args()
    tasks = []

    if args.surface:
        surface = SurfaceSearcher()
        eng_list = args.engines.split(",") if args.engines else None
        tasks.append(surface.search(args.query, engines=eng_list, limit=args.limit))

    if args.onion:
        onion = OnionSearcher()
        tasks.append(onion.search(args.query, limit=args.limit))

    if args.i2p:
        i2p = I2PSearcher()
        tasks.append(i2p.search(args.query, limit=args.limit))

    gathered = await asyncio.gather(*tasks, return_exceptions=True)
    all_results = []
    for res in gathered:
        if isinstance(res, list):
            all_results.extend(res)
        elif isinstance(res, Exception):
            print(f"[Warning] Sub-searcher error: {res}", file=sys.stderr)

    if args.dedup:
        all_results = deduplicate(all_results)

    output_results(all_results, args.format)


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
