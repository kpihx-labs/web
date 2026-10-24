"""Explicit volume backup/purge test using a unique throwaway Docker project."""

import re
import subprocess
import tarfile
from pathlib import Path
from uuid import uuid4


def run(arguments, check=True):
    return subprocess.run(
        arguments, text=True, capture_output=True, timeout=120, check=check
    )


def main():
    backend = Path(__file__).resolve().parents[2] / "searxng"
    project = "web-lifecycle-" + uuid4().hex[:10]
    volume = project + "_caddy-data"
    run(
        [
            "docker",
            "volume",
            "create",
            "--label",
            "com.docker.compose.project=" + project,
            "--label",
            "com.docker.compose.volume=caddy-data",
            volume,
        ]
    )
    try:
        run(
            [
                "docker",
                "run",
                "--rm",
                "--pull=never",
                "-v",
                volume + ":/data",
                "alpine",
                "dd",
                "if=/dev/zero",
                "of=/data/fixture",
                "bs=32",
                "count=1",
            ]
        )
        denied = run(
            ["make", "-C", str(backend), "purge", "PROJECT=" + project], check=False
        )
        assert denied.returncode != 0 and "Refused" in denied.stdout
        result = run(
            [
                "make",
                "-C",
                str(backend),
                "purge",
                "PROJECT=" + project,
                "CONFIRM=" + project,
            ]
        )
        folder = re.search(r"Backups retained: (.+)", result.stdout).group(1)
        archive = Path(folder) / (volume + ".bak")
        with tarfile.open(archive) as snapshot:
            member = next(m for m in snapshot if m.name.endswith("fixture"))
            assert snapshot.extractfile(member).read() == bytes(32)
        assert run(["docker", "volume", "inspect", volume], check=False).returncode != 0
        print(
            "PASS: no-confirm refusal; owned volume removed only after verified private backup:",
            archive,
        )
    finally:
        if run(["docker", "volume", "inspect", volume], check=False).returncode == 0:
            run(["docker", "volume", "rm", volume])


if __name__ == "__main__":
    main()
