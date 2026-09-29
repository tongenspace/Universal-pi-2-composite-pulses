"""The published phase strings, used without alteration."""
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "data" / "pulses.json"
CATALOG = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))["sequences"]
FIGURE1 = ["UVH1s", "UVH5s", "UVH7s", "UVH9s", "UVH11s", "UVH13s"]
FIGURE2 = [f"UVH{n}{family}" for n in range(4, 9) for family in ("a", "d")]
FIGURE3 = ["UVH1s", "UVH5s", "UVH9s", "UVH13s"]


def phases(name):
    return np.pi * np.asarray(CATALOG[name]["phases_pi"], dtype=float)
