"""Offline document inspection and explicitly opt-in candidate verification."""

import hashlib
import shutil
import subprocess
import tempfile
import zipfile
from difflib import SequenceMatcher
from pathlib import Path

from defusedxml import ElementTree

from .http import WebError
from .models import extract_osint_entities
from .user_config import settings


def extract(path, ocr=False, pages=10):
    if pages < 0:
        raise WebError("Document page budget must be nonnegative (0 selects all)")
    try:
        return _extract(path, ocr, pages)
    except WebError:
        raise
    except Exception as error:
        raise WebError(
            f"Cannot parse document ({type(error).__name__}); check file format/integrity and native OCR dependencies"
        ) from None


def _extract(path, ocr=False, pages=10):
    path = Path(path)
    if not path.is_file() or path.stat().st_size > settings()["local_max_bytes"]:
        raise WebError(
            "Document missing or exceeds configured local_max_bytes inspection budget"
        )
    suffix = path.suffix.lower()
    if suffix in {".docx", ".odt", ".pptx"}:
        with zipfile.ZipFile(path) as archive:
            if (
                sum(item.file_size for item in archive.infolist())
                > settings()["xml_max_bytes"]
            ):
                raise WebError(
                    "Expanded office archive exceeds configured xml_max_bytes budget"
                )
    metadata = {}
    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(path)
        if reader.is_encrypted:
            raise WebError(
                "Encrypted PDF: decrypt your authorized copy before inspection"
            )
        metadata = {str(k): str(v) for k, v in (reader.metadata or {}).items()}
        chosen = list(reader.pages)[:pages] if pages else list(reader.pages)
        text = "\n".join(page.extract_text() or "" for page in chosen)
        if not text.strip() and ocr:
            for command in ("pdftoppm", "tesseract"):
                if not shutil.which(command):
                    raise WebError(f"OCR needs {command}; see make deps")
            with tempfile.TemporaryDirectory(prefix="web-ocr-") as folder:
                subprocess.run(
                    [
                        "pdftoppm",
                        "-f",
                        "1",
                        "-l",
                        str(pages or len(reader.pages)),
                        "-r",
                        "150",
                        "-png",
                        str(path),
                        folder + "/page",
                    ],
                    check=True,
                    capture_output=True,
                    timeout=120,
                )
                text = "\n".join(
                    subprocess.run(
                        ["tesseract", str(image), "stdout"],
                        check=True,
                        capture_output=True,
                        text=True,
                        timeout=60,
                    ).stdout
                    for image in sorted(Path(folder).glob("*.png"))
                )
    elif suffix == ".docx":
        from docx import Document

        doc = Document(str(path))
        metadata = {
            name: str(getattr(doc.core_properties, name) or "")
            for name in (
                "author",
                "last_modified_by",
                "created",
                "modified",
                "title",
                "subject",
                "keywords",
            )
        }
        text = "\n".join(
            [p.text for p in doc.paragraphs]
            + [
                " | ".join(c.text for c in row.cells)
                for table in doc.tables
                for row in table.rows
            ]
        )
    elif suffix in {".odt", ".pptx"}:
        with zipfile.ZipFile(path) as archive:
            names = [
                n
                for n in archive.namelist()
                if n == "content.xml"
                or (n.startswith("ppt/slides/slide") and n.endswith(".xml"))
            ]
            if (
                sum(archive.getinfo(n).file_size for n in names)
                > settings()["xml_max_bytes"]
            ):
                raise WebError("Expanded XML exceeds 20 MB budget")
            text = "\n".join(
                " ".join(ElementTree.fromstring(archive.read(n)).itertext())
                for n in names
            )
    elif suffix == ".html":
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(path.read_bytes(), "html.parser")
        metadata = {
            "title": soup.title.get_text(strip=True) if soup.title else "",
            "provenance": "Local HTML/saved DOM, not a fresh server verification",
        }
        for node in soup.select("script,style,noscript,template"):
            node.decompose()
        text = (soup.select_one("article,main") or soup).get_text("\n", strip=True)
    elif suffix in {".txt", ".md", ".csv", ".json", ".xml", ".rst", ".tex"}:
        text = path.read_text(encoding="utf-8-sig")
    else:
        raise WebError(
            "Unsupported document: export PDF/text/DOCX/ODT/PPTX; arbitrary binary is not UTF-8 text"
        )
    return {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "metadata": metadata,
        "text": text,
        "characters": len(text),
        "entities": extract_osint_entities(text),
        "page_budget": pages,
        "empty_or_scanned": not bool(text.strip()),
    }


def compare(left, right):
    a, b = left["text"], right["text"]
    matcher = SequenceMatcher(None, a.casefold(), b.casefold(), autojunk=False)
    blocks = [
        {
            "left_offset": m.a,
            "right_offset": m.b,
            "length": m.size,
            "excerpt": a[m.a : m.a + min(m.size, 250)],
        }
        for m in matcher.get_matching_blocks()
        if m.size >= 30
    ]
    return {
        "lexical_similarity": matcher.ratio(),
        "matching_spans": blocks,
        "exact_bytes": left["sha256"] == right["sha256"],
        "qualification": "Lexical overlap is not semantic equivalence or proof of plagiarism",
    }
