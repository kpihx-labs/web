"""Consistent output envelopes and escaped offline HTML/PDF reports."""

import csv
import html
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from rich.console import Console
from rich.json import JSON
from rich.table import Table
from rich.text import Text

from .http import WebError, save_bytes
from .user_config import results_dir


def csv_cell(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def terminal_text(value):
    return Text(
        "".join(
            c
            for c in str(value)
            if c in "\n\t" or (ord(c) >= 32 and not 127 <= ord(c) <= 159)
        )
    )


def render(record):
    console = Console()
    data = record["data"]
    console.print(
        terminal_text(
            f"web {record['action']}: {record['status']} | {record['timestamp']}"
        )
    )
    rows = data.get("results", data.get("pages", data.get("engines")))
    if record["action"] == "image":
        console.print(JSON.from_data(data.get("metadata", {})))
        console.print(
            terminal_text(
                f"Sanitized pixels uploaded: {data.get('uploaded_sanitized_pixels')}; OCR query disclosed: {data.get('ocr_query_disclosed')}"
            )
        )
        if not data.get("uploaded_sanitized_pixels"):
            console.print(
                "Local inspection only: no reverse search was requested. Use --online explicitly to upload sanitized pixels."
            )
            return
    if isinstance(rows, list):
        table = Table()
        catalog = record["action"] == "engines"
        for heading in (
            ("Engine", "Categories", "Default enabled")
            if catalog
            else ("#", "Title / state", "URL", "Source")
        ):
            table.add_column(heading)
        for index, row in enumerate(rows, 1):
            if catalog:
                enabled = row.get(
                    "enabled", not row["disabled"] if "disabled" in row else "unknown"
                )
                cells = (
                    row.get("name", ""),
                    ", ".join(row.get("categories", [])),
                    enabled,
                )
            else:
                cells = (
                    index,
                    str(row.get("title", row.get("access_state", "")))[:160],
                    row.get("url", ""),
                    row.get("engine", row.get("network", "")),
                )
            table.add_row(*(terminal_text(cell) for cell in cells))
        console.print(table)
        console.print(
            terminal_text(
                f"Returned {len(rows)}; limit={data.get('limit', 'n/a')}; page budget={data.get('page_budget', 'n/a')}. Coverage is not exhaustive."
            )
        )
        for name in ("upstream_issues", "backend_failures", "errors"):
            if data.get(name):
                console.print(
                    terminal_text(
                        f"{name}: {json.dumps(data[name], ensure_ascii=False)}"
                    )
                )
    elif "text" in data:
        for name in (
            "url",
            "path",
            "title",
            "access_state",
            "mime",
            "characters",
            "sha256",
            "metadata",
            "entities",
            "comparisons",
        ):
            if name in data:
                console.print(terminal_text(f"{name}: {data[name]}"))
        console.print(
            terminal_text(
                data.get("selected_text", data.get("matches", data["text"][:2000]))
            )
        )
    elif record["action"] == "audio":
        track = data.get("result", {}).get("track", {})
        console.print(
            terminal_text(
                f"Matched: {data['matched']} | {track.get('title', '')} | {track.get('subtitle', '')}"
            )
        )
        console.print(terminal_text(data["capability"]))
    else:
        console.print(JSON.from_data(data))
    console.print("Terminal preview; use -f json for complete structured data.")


def emit(action, data, *, fmt="table", save_dir=None, no_save=False, report=None):
    record = {
        "action": action,
        "timestamp": datetime.now(UTC).isoformat(),
        "status": "partial" if data.get("partial") else "ok",
        "data": data,
    }
    text = json.dumps(record, ensure_ascii=False, indent=2)
    if not no_save:
        directory = Path(save_dir) if save_dir else results_dir()
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = (
            directory
            / f"{action}_{datetime.now(UTC):%Y%m%d_%H%M%S_%f}_{uuid4().hex[:8]}.json"
        )
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write(text)
        Console(stderr=True).print(f"Saved: {path}", markup=False)
    if report:
        path = Path(report)
        if path.exists():
            raise WebError("Report already exists; choose another path (no overwrite)")
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix.lower() == ".html":
            document = (
                '<!doctype html><html lang="en"><meta charset="utf-8">'
                "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; style-src 'unsafe-inline'\">"
                "<title>web evidence report</title><style>body{max-width:1000px;margin:3em auto;font:16px sans-serif;background:#111827;color:#eee}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style>"
                f"<h1>web evidence report</h1><pre>{html.escape(text)}</pre></html>"
            )
            save_bytes(path, document.encode())
        elif path.suffix.lower() == ".pdf":
            from fpdf import FPDF
            from fpdf.enums import WrapMode

            font = subprocess.run(
                ["fc-match", "-f", "%{file}", "DejaVu Sans"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout
            if not Path(font).is_file():
                raise WebError(
                    "PDF requires a Unicode font; install fonts-dejavu-core or use HTML"
                )
            pdf = FPDF()
            pdf.add_font("Evidence", fname=font)
            pdf.add_page()
            pdf.set_font("Evidence", size=8)
            for line in text.splitlines():
                pdf.multi_cell(
                    0, 4, line, new_x="LMARGIN", new_y="NEXT", wrapmode=WrapMode.CHAR
                )
            save_bytes(path, pdf.output())
        else:
            raise WebError(
                "Reports support .html or .pdf, not an HTML file disguised as PDF"
            )
        path.chmod(0o600)
        Console(stderr=True).print(f"Report: {path}", markup=False)
    if fmt == "json":
        print(text)
    elif fmt == "md":
        print(f"# web {action}\n\n```json\n{text}\n```")
    elif fmt == "table":
        render(record)
    elif fmt == "jsonl":
        print(json.dumps(record, ensure_ascii=False))
    elif fmt == "csv":
        rows = data.get("results", data.get("pages", [data]))
        if rows:
            keys = list(dict.fromkeys(key for row in rows for key in row))
            writer = csv.DictWriter(sys.stdout, fieldnames=keys)
            writer.writeheader()
            writer.writerows(
                {key: csv_cell(value) for key, value in row.items()} for row in rows
            )
    else:
        raise WebError("Format must be table, json, jsonl, csv or md")
    return 3 if record["status"] == "partial" else 0
