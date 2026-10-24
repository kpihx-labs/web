"""Free SongRec fingerprint adapter; humming is explicitly best-effort, not STT."""

import json
import math
import shutil
import subprocess
import tempfile
from pathlib import Path

from .http import WebError


def identify(
    path, record=None, mode="recording", duration=12.0, source="default", offset=0.0
):
    if mode not in {"recording", "hum"}:
        raise WebError("Mode must be recording or hum")
    if not math.isfinite(offset) or offset < 0 or (record is not None and offset):
        raise WebError("Offset must be finite, nonnegative and used only with a file")
    if not math.isfinite(duration) or (
        record is not None and not math.isfinite(record)
    ):
        raise WebError("Audio durations must be finite")
    if (
        (path is None) == (record is None)
        or duration <= 0
        or (record is not None and record <= 0)
    ):
        raise WebError("Provide one file or --record SECONDS, with positive duration")
    for command in ("ffmpeg", "songrec"):
        if not shutil.which(command):
            raise WebError(
                f"Missing {command}; run make deps for installation guidance"
            )
    with tempfile.TemporaryDirectory(prefix="web-audio-") as folder:
        sample = Path(folder) / "sample.wav"
        args = ["ffmpeg", "-nostdin", "-v", "error"]
        args += (
            ["-f", "pulse", "-i", source, "-t", str(record)]
            if record
            else ["-ss", str(offset), "-i", str(path), "-t", str(duration)]
        )
        subprocess.run(
            [*args, "-ac", "1", "-ar", "16000", str(sample)],
            check=True,
            capture_output=True,
            timeout=60 + (record or 0),
        )
        process = subprocess.run(
            ["songrec", "audio-file-to-recognized-song", str(sample)],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        result = json.loads(process.stdout)
    return {
        "requested_offset": offset,
        "provider": "songrec",
        "mode": mode,
        "matched": bool(result.get("track")),
        "result": result,
        "partial": mode == "hum",
        "capability": "Original-recording fingerprint, not query-by-humming; melody-only matches are not reliable",
    }
