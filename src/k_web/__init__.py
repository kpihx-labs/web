"""Local-first web investigation primitives."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("kpihx-web")
except PackageNotFoundError:
    __version__ = "uninstalled"
