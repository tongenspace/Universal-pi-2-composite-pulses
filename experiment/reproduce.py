"""Rebuild experimental tables and figures from the archived local IQM arrays."""
from __future__ import annotations

import hashlib
import os
import sys
import tempfile
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager

ROOT = Path(__file__).resolve().parent


def verify_archives():
    folders = sorted((ROOT / "data/raw/iqm_jobs").iterdir())
    if len(folders) != 12:
        raise ValueError(f"Expected 12 job archives, found {len(folders)}")
    for folder in folders:
        checksums = folder / "SHA256SUMS.txt"
        for line in checksums.read_text(encoding="utf-8").splitlines():
            expected, filename = line.split("  ", 1)
            actual = hashlib.sha256((folder / filename).read_bytes()).hexdigest()
            if actual != expected:
                raise ValueError(f"Archive checksum mismatch: {folder.name}/{filename}")


def main():
    verify_archives()
    path = ROOT / "02_process_validate_iqm_data_publication.ipynb"
    notebook = nbformat.read(path, as_version=4)
    nbformat.validate(notebook)
    with tempfile.TemporaryDirectory(prefix="uvh-experiment-") as runtime:
        os.environ["JUPYTER_RUNTIME_DIR"] = runtime
        os.environ["IPYTHONDIR"] = str(Path(runtime) / "ipython")
        os.environ["MPLCONFIGDIR"] = str(Path(runtime) / "matplotlib")
        manager = KernelManager(kernel_name="python3")
        manager.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
        try:
            NotebookClient(notebook, km=manager, timeout=3600,
                           resources={"metadata": {"path": str(ROOT)}},
                           allow_errors=False).execute()
        finally:
            if manager.has_kernel:
                manager.shutdown_kernel(now=True)
    print("Verified all 12 archives and regenerated experimental tables and PDF figures.")


if __name__ == "__main__":
    main()
