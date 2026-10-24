"""Private labelled query snapshots; format is deliberately not part of the key."""

import hashlib
import json
import os
import time
from pathlib import Path
from uuid import uuid4


def location(query, options):
    key = hashlib.sha256(
        json.dumps([query, options], sort_keys=True, default=str).encode()
    ).hexdigest()
    return (
        Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
        / "web/search"
        / (key + ".json")
    )


def load(path, maximum_age):
    try:
        record = json.loads(path.read_text())
        age = max(0.0, time.time() - record["stored_at"])
        if age <= maximum_age:
            return record["data"], round(age, 2)
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None


def store(path, data):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid4().hex)
    descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(descriptor, "w") as stream:
            json.dump(
                {"stored_at": time.time(), "data": data}, stream, ensure_ascii=False
            )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
