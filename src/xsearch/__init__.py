"""xsearch core library and unified multi-network search engine."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("xsearch")
except PackageNotFoundError:
    __version__ = "0.1.0"
