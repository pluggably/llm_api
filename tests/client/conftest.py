import sys
from pathlib import Path

CLIENT_ROOT = Path(__file__).resolve().parents[2] / "clients" / "python"
if str(CLIENT_ROOT) not in sys.path:
    sys.path.insert(0, str(CLIENT_ROOT))
