"""Portable CSV and JSON result files with input provenance."""
import csv
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path


def write_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError("Cannot write an empty table.")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def provenance(paths):
    return dict(python=platform.python_version(),
                packages={name: importlib.metadata.version(name)
                          for name in ["numpy", "scipy", "matplotlib"]},
                implementation_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                       for p in sorted(Path(__file__).parent.glob("*.py"))},
                input_sha256={Path(p).name: hashlib.sha256(Path(p).read_bytes()).hexdigest()
                              for p in paths})
