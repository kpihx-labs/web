"""Explicit destructive-to-this-service-only live test; not collected by pytest.

Run manually with uv run tests/live_backend_recovery.py. Always restore the service.
Never stop Docker, networking, WiFi, the VPN or unrelated stacks.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2] / "searxng"
COMPOSE = ["docker", "compose", "-f", str(PROJECT / "docker-compose.yml")]


def command(arguments, check=True):
    return subprocess.run(arguments, capture_output=True, text=True, timeout=160, check=check)


def xsearch(arguments):
    return command([sys.executable, "-m", "xsearch.cli", *arguments], check=False)


def assert_outage():
    with tempfile.TemporaryDirectory(prefix="xsearch-outage-") as directory:
        result = xsearch(["search", "canary", "-f", "json", "--timeout", "2", "--save-dir", directory])
        assert result.returncode == 2, (result.returncode, result.stderr)
        assert not result.stdout.strip(), result.stdout
        assert not list(Path(directory).iterdir()), "Outage was saved as successful empty results"
        print("PASS: outage exits 2, actionable stderr, empty stdout, no false success autosave")
        engines = xsearch(["engines"])
        assert engines.returncode == 2 and not engines.stdout.strip(), engines
        print("PASS: unreachable engines catalogue does not render a misleading empty table")


def main():
    try:
        command([*COMPOSE, "stop", "searxng"])
        assert_outage()
    finally:
        restored = command([*COMPOSE, "up", "-d", "--wait", "--wait-timeout", "120", "searxng"], check=False)
        print(restored.stdout, restored.stderr)
        if restored.returncode:
            raise RuntimeError("Restore failed. Run make recover in your searxng project NOW.")
    report = xsearch(["doctor", "--live", "-e", "bing,brave", "-f", "json"])
    assert report.returncode in (0, 3), report.stderr + report.stdout
    status = json.loads(report.stdout)
    assert any(check.get("results", 0) > 0 for check in status["checks"])
    print("PASS: restarted backend/frontend and live upstream search recovered", status["state"])

    networks = json.loads(command(["docker", "inspect", "searxng", "--format", "{{json .NetworkSettings.Networks}}"]).stdout)
    if len(networks) != 1:
        raise RuntimeError("Refusing network-fault test: expected exactly one stack network")
    network = next(iter(networks))
    try:
        command(["docker", "network", "disconnect", network, "searxng"])
        assert_outage()
    finally:
        command(["docker", "network", "connect", "--alias", "searxng", network, "searxng"])
    report = xsearch(["doctor", "--live", "-e", "bing,brave", "-f", "json"])
    assert report.returncode in (0, 3), report.stderr + report.stdout
    print("PASS: detached/reconnected container network and live search recovered")


if __name__ == "__main__":
    main()
