"""Back-compat shim."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from redactd.coarse import GROUPS, TYPES, COARSE  # noqa: F401
