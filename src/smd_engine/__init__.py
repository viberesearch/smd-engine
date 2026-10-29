"""Records, checks and renderings for SMD-style thinking sessions."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("smd-engine")  # the installed package, as in pyproject.toml
except PackageNotFoundError:  # a source tree that is not installed
    __version__ = "0+unknown"
SCHEMA_VERSION = "0.3"
