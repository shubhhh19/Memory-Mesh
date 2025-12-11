"""memorymesh package."""

import os
from importlib.metadata import version

# numpy performs a macOS framework check that is blocked inside some sandboxed
# environments. Setting this disables the check before numpy is ever imported.
os.environ.setdefault("NPY_DISABLE_MAC_OS_CHECK", "1")

__all__ = ["__version__"]

try:
    __version__ = version("ai-memory-layer")
except Exception:  # pragma: no cover - package metadata missing in dev installs
    __version__ = "0.0.0"
