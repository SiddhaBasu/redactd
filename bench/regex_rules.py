"""Back-compat shim: rules live in redactd.rules."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from redactd.rules import *  # noqa: F401,F403
from redactd.rules import detect, detect_org, COMPILED, ORG_RX  # noqa: F401
