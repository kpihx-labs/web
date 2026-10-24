"""Thin map API adapters. JSON payloads preserve provider-specific capabilities."""

import fcntl
import hashlib
import json
import os
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

from .config import CONFIG


def json_input(value: str | None) -> dict | list:
    if not value:
        return {}
    text = Path(value[1:]).read_text() if value.startswith("@") else value
    return json.loads(text)


def json_object(value: str | None) -> dict:
    result = json_input(value)
    if not isinstance(result, dict):
        raise TypeError(
            "Parameters must be a JSON object, or @file containing an object."
        )
    return result


def json_vertices(value: str) -> list:
    result = json_input(value)
    if not isinstance(result, list):
        raise TypeError("Route vertices must be an ordered JSON list, or @file.")
    return result


class Maps:
    def __init__(self, settings: dict):
        self.settings = settings
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers["User-Agent"] = settings["user_agent"]
        self.last_geocode = 0.0

    def request(
        self, endpoint: str, method: str = "GET", params=None, data=None, body=None
    ):
        if (
            urlparse(endpoint).scheme not in {"https", "http"}
            or urlparse(endpoint).username is not None
        ):
            raise ValueError("Endpoint must be an HTTP(S) URL.")
        try:
            response = self.session.request(
                method,
                endpoint,
                params=params,
                data=data,
                json=body,
                timeout=self.settings["timeout"],
                stream=True,
            )
            with response:
                response.raise_for_status()
                content = bytearray()
                for block in response.iter_content(65536):
                    content.extend(block)
                    if len(content) > self.settings.get(
                        "response_max_bytes", CONFIG.response_max_bytes
                    ):
                        raise ValueError(
                            "Map response exceeds configured response_max_bytes"
                        )
                try:
                    return json.loads(content)
                except ValueError:
                    return {
                        "mime": response.headers.get("Content-Type"),
                        "text": content.decode("utf-8", errors="replace"),
                    }
        except requests.RequestException as error:
            status = getattr(error.response, "status_code", None)
            raise ValueError(
                f"Map API failed ({type(error).__name__}, HTTP {status}); check endpoint, parameters and network; respect rate limits and retry provider outages later. Request credentials/URL query were not logged"
            ) from None

    def search(self, query: str, params: dict):
        # Shared lock/cache also covers separate CLI invocations on this machine.
        directory = (
            Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
            / "web/geocode"
        )
        directory.mkdir(parents=True, mode=0o700, exist_ok=True)
        payload = {"q": query, "format": "jsonv2", **params}
        key = hashlib.sha256(
            json.dumps([self.settings["geocoder"], payload], sort_keys=True).encode()
        ).hexdigest()
        cached = directory / f"{key}.json"
        with (directory / "request.lock").open("a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if (
                cached.exists()
                and time.time() - cached.stat().st_mtime
                < self.settings.get("geocode_cache_seconds", 86400)
            ):
                return json.loads(cached.read_text())
            lock.seek(0)
            previous = float(lock.read() or 0)
            delay = 1.05 - (time.time() - previous)
            if delay > 0:
                time.sleep(delay)
            try:
                result = self.request(self.settings["geocoder"], params=payload)
            finally:
                lock.seek(0)
                lock.truncate()
                lock.write(str(time.time()))
                lock.flush()
            cached.write_text(json.dumps(result))
            cached.chmod(0o600)
            return result

    def point(self, value, near=None):
        if isinstance(value, list) and len(value) == 2:
            lon, lat = map(float, value)
            if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                raise ValueError(
                    "Coordinate outside WGS84 bounds; use [longitude, latitude]."
                )
            return [lon, lat]
        if not isinstance(value, str):
            raise TypeError(
                "Each route vertex must be a place string or [longitude, latitude]."
            )
        parameters: dict = {"limit": 1}
        if near:
            lon, lat = near
            radius = self.settings.get("route_geocode_bias_degrees", 0.5)
            parameters["viewbox"] = (
                f"{lon - radius},{lat - radius},{lon + radius},{lat + radius}"
            )
            parameters["bounded"] = 0
        matches = self.search(value, parameters)
        if not isinstance(matches, list) or not matches:
            raise ValueError(f"Place not found: {value}")
        return [float(matches[0]["lon"]), float(matches[0]["lat"])]

    def query(self, text: str, params: dict):
        method = self.settings.get("overpass_method", "GET").upper()
        if method == "GET":
            return self.request(
                self.settings["overpass"], params={"data": text, **params}
            )
        return self.request(
            self.settings["overpass"], method, params=params, data={"data": text}
        )

    def route(self, vertices: list, profile: str | None, params: dict):
        if not isinstance(vertices, list) or len(vertices) < 2:
            raise ValueError(
                "Route requires an ordered JSON list of at least two vertices."
            )
        points = []
        for vertex in vertices:
            points.append(self.point(vertex, near=points[-1] if points else None))
        result = self.request(
            self.settings["router"],
            params={
                "lonlats": "|".join(f"{lon},{lat}" for lon, lat in points),
                "profile": profile or self.settings["route_profile"],
                "alternativeidx": 0,
                "format": "geojson",
                **params,
            },
        )
        result["web_resolved_vertices"] = points
        return result
