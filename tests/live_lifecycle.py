"""Explicit isolated wheel install/purge/uninstall, never the user's real state."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    wheel = next((Path(__file__).resolve().parents[1] / "dist").glob("k_web-*.whl"))
    cache = subprocess.check_output(["uv", "cache", "dir"], text=True).strip()
    with tempfile.TemporaryDirectory(prefix="web-lifecycle-") as root:
        base = Path(root)
        env = {
            **os.environ,
            "HOME": str(base / "home"),
            "UV_CACHE_DIR": cache,
            "UV_TOOL_DIR": str(base / "tools"),
            "UV_TOOL_BIN_DIR": str(base / "bin"),
            "UV_PYTHON": sys.executable,
            "UV_LINK_MODE": "copy",
            "PATH": str(base / "bin") + os.pathsep + os.environ["PATH"],
            "WEB_RESULTS_DIR": str(base / "web-results"),
            "WEB_CONFIG_DIR": str(base / "home/.config/web"),
            "XDG_CONFIG_HOME": str(base / "home/.config"),
            "XDG_CACHE_HOME": str(base / "home/.cache"),
            "XDG_STATE_HOME": str(base / "home/.local/state"),
        }

        def run(args):
            subprocess.run(args, env=env, check=True, timeout=120)

        run(["uv", "tool", "install", "--offline", str(wheel)])
        binary = str(base / "bin/web")
        run([binary, "setup"])
        run([binary, "capabilities", "-f", "json"])
        run([binary, "purge", "--yes"])
        assert not Path(env["WEB_CONFIG_DIR"]).exists()
        run(["make", "-C", str(Path(__file__).resolve().parents[1]), "uninstall"])
        assert not Path(binary).exists()
        print(
            "PASS: isolated built-wheel install, setup, private-state purge and uninstall"
        )


if __name__ == "__main__":
    main()
