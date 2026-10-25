"""EXIF inspection and explicit sanitized reverse-image upload."""

import hashlib
import shutil
import subprocess
import tempfile
from pathlib import Path

from PicImageSearch import Bing, Google, Network, Yandex
from PIL import Image, ImageOps

from .backend import BackendError
from .http import WebError
from .user_config import settings


async def inspect(
    path, online=False, engines=("yandex",), limit=10, text_search=False, persist=True
):
    if limit < 0:
        raise WebError(
            "Image limit must be nonnegative; zero selects all fetched candidates"
        )
    path = Path(path)
    if path.stat().st_size > settings()["local_max_bytes"]:
        raise WebError("Image exceeds configured local_max_bytes")
    with Image.open(path) as original:
        exif = original.getexif()
        gps = exif.get_ifd(34853) if 34853 in exif else {}

        def degrees(value):
            return float(value[0]) + float(value[1]) / 60 + float(value[2]) / 3600

        metadata: dict[str, object] = {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "width": original.width,
            "height": original.height,
            "camera": str(exif.get(272, "")),
            "make": str(exif.get(271, "")),
            "date": str(exif.get(306, "")),
        }
        details = exif.get_ifd(34665) if 34665 in exif else {}
        metadata["date"] = str(details.get(36867, metadata["date"]))
        metadata["software"] = str(exif.get(305, ""))
        if 2 in gps and 4 in gps:
            metadata["latitude"] = degrees(gps[2]) * (
                -1 if gps.get(1) in ("S", b"S") else 1
            )
            metadata["longitude"] = degrees(gps[4]) * (
                -1 if gps.get(3) in ("W", b"W") else 1
            )
        if 6 in gps:
            metadata["altitude_m"] = float(gps[6]) * (
                -1 if gps.get(5) in (1, b"\x01") else 1
            )
        image = ImageOps.exif_transpose(original).convert("RGBA")
        image.info.clear()
        image.getexif().clear()
    results, errors = [], []
    providers = {"yandex": Yandex, "google": Google, "bing": Bing}
    if set(engines) - providers.keys():
        raise WebError(
            "Image engines: yandex, google, bing; third-party layouts may be blocked or change"
        )
    if online:
        with tempfile.TemporaryDirectory(prefix="web-image-") as folder:
            clean = Path(folder) / "pixels.png"
            image.save(clean)  # No original EXIF/GPS is uploaded.
            async with Network() as client:
                for name in engines:
                    try:
                        response = await providers[name](client=client).search(
                            file=clean
                        )
                        for row in response.raw[:limit] if limit else response.raw:
                            results.append(
                                {"engine": name, "title": row.title, "url": row.url}
                            )
                    except Exception as error:
                        errors.append(
                            {
                                "engine": name,
                                "error": type(error).__name__,
                                "action": "Use an authorized browser manually; no CAPTCHA bypass was attempted",
                            }
                        )
    ocr_query = None
    if online and text_search:
        if not shutil.which("tesseract"):
            errors.append(
                {"engine": "local-ocr", "error": "Install tesseract-ocr; see make deps"}
            )
        else:
            ocr = subprocess.run(
                ["tesseract", str(path), "stdout"],
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            ).stdout
            ocr_query = " ".join(ocr.split()[:15])
            if ocr_query:
                from .research import search

                try:
                    candidates = await search(ocr_query, limit=limit, persist=persist)
                except (WebError, BackendError) as error:
                    candidates = {"results": [], "partial": True}
                    errors.append(
                        {
                            "engine": "ocr-text-search",
                            "error": str(error),
                            "action": "Discovery failed; local image metadata/other candidates are retained",
                        }
                    )
                if candidates.get("partial"):
                    errors.append(
                        {
                            "engine": "ocr-text-search",
                            "error": "Partial text discovery coverage",
                            "details": candidates.get(
                                "upstream_issues",
                                candidates.get("backend_failures", []),
                            ),
                        }
                    )
                results.extend(
                    {
                        "engine": "ocr-text-search",
                        "title": row["title"],
                        "url": row["url"],
                        "evidence": "Text candidate only; image equality NOT verified",
                    }
                    for row in candidates["results"]
                )
    return {
        "non_exhaustive": online,
        "limit": limit,
        "engines_requested": list(engines),
        "qualification": "Provider candidates are not proof of image equality or identity attribution",
        "ocr_query_disclosed": ocr_query,
        "metadata": metadata,
        "uploaded_sanitized_pixels": online,
        "results": results,
        "errors": errors,
        "partial": bool(errors) or (online and not results),
    }
