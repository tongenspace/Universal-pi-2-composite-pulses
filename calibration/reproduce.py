"""Execute the analysis in a fresh kernel and export an offline HTML report."""
import os
import re
import sys
import tempfile
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter
from jupyter_client import KernelManager


def main():
    root = Path(__file__).resolve().parent
    path = root / "garnet_single_qubit_calibration.ipynb"
    notebook = nbformat.read(path, as_version=4)
    for cell in notebook.cells:
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None
    with tempfile.TemporaryDirectory(prefix="garnet-jupyter-") as runtime:
        os.environ["JUPYTER_RUNTIME_DIR"] = runtime
        os.environ["MPLCONFIGDIR"] = str(Path(runtime) / "matplotlib")
        os.environ["IPYTHONDIR"] = str(Path(runtime) / "ipython")
        manager = KernelManager(kernel_name="python3")
        manager.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
        client = NotebookClient(notebook, km=manager, timeout=180,
                                resources={"metadata": {"path": str(root)}},
                                record_timing=False)
        try:
            client.execute()
        finally:
            if manager.has_kernel:
                manager.shutdown_kernel(now=True)
    nbformat.validate(notebook)
    nbformat.write(notebook, path)
    exporter = HTMLExporter(template_name="lab")
    exporter.exclude_input = True
    # Readable Unicode formulas keep the static report independent of a remote math renderer.
    report = nbformat.from_dict(notebook)
    formulas = {
        r"$\pi/2$": "π/2", r"$100(1-F)$": "100 × (1 − F)",
        r"$10^6$": "1,000,000", r"$y=a x+b$": "y = a x + b",
        r"$u_y=|a|u_x$": "u(y) = |a| u(x)",
        r"$1-(p_{0\to1}+p_{1\to0})/2$": "1 − (p(0→1) + p(1→0))/2",
    }
    for cell in report.cells:
        if cell.cell_type == "markdown":
            for formula, replacement in formulas.items():
                cell.source = cell.source.replace(formula, replacement)
    body, _ = exporter.from_notebook_node(report)
    body = re.sub(r"<script\b[^>]*>.*?</script>", "", body, flags=re.DOTALL | re.IGNORECASE)
    body = body.replace("<title>Notebook</title>", "<title>IQM Garnet — historical single-qubit calibration</title>")
    # All plots and styles are embedded; there is no script runtime or remote asset dependency.
    (root / "garnet_single_qubit_calibration.html").write_text(body, encoding="utf-8")
    executed = sum(c.cell_type == "code" for c in notebook.cells)
    print(f"Executed {executed} code cells successfully; saved notebook and HTML report.")


if __name__ == "__main__":
    main()
