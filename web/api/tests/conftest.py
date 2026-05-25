import os
import sys
from pathlib import Path

# Make `web.api` importable when running pytest from repo root or from web/api.
_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[3]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "python" / "src"))

# Default to no token unless a test sets one.
os.environ.pop("REDTONOMOUS_API_TOKEN", None)
