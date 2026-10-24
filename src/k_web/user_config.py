"""Operator-owned plain Python configuration. Never load dormant paid API keys."""

import os
import runpy
from dataclasses import asdict
from pathlib import Path

from . import __version__
from .config import CONFIG


def config_dir():
    return Path(
        os.environ.get(
            "WEB_CONFIG_DIR",
            Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "web",
        )
    )


def results_dir():
    return Path(os.environ.get("WEB_RESULTS_DIR", "/tmp/web-results"))


def initialize():
    directory = config_dir()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = directory / "config.py"
    if not path.exists():
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write(
                '"""Optional web settings. Defaults work without API keys."""\nSETTINGS = {}\n'
            )
    return directory


def settings():
    values = {
        **asdict(CONFIG),
        "timeout": 30.0,
        "geocoder": "https://nominatim.openstreetmap.org/search",
        "overpass": "https://overpass-api.de/api/interpreter",
        "router": "https://brouter.de/brouter",
        "route_profile": "trekking",
        "user_agent": f"k-web/{__version__} (personal CLI)",
    }
    path = config_dir() / "config.py"
    if path.exists():
        supplied = runpy.run_path(str(path)).get("SETTINGS", {})
        if not isinstance(supplied, dict):
            raise ValueError("SETTINGS in web/config.py must be a dictionary")
        values.update(supplied)
    if str(values["user_agent"]).startswith("xsearch/"):
        values["user_agent"] = f"k-web/{__version__} (personal CLI)"
    return values
