"""Execute the companion notebooks from fresh kernels, preserving their outputs."""
import argparse
import json
from pathlib import Path
import sys
import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=["all", "square", "drag"], default="all")
    parser.add_argument("--kernel", default="python3")
    parser.add_argument("--require-figure3", action="store_true",
                        help="Exit with status 2 unless fixed-parameter Figure 3 simulation completed.")
    args = parser.parse_args()
    selections = {
        "square": "01_figures_1_2_square_pulses.ipynb",
        "drag": "figure_3_iqm_drag.ipynb",
    }
    if args.require_figure3 and args.only == "square":
        parser.error("--require-figure3 requires --only drag or --only all")
    for key, filename in selections.items():
        if args.only not in (key, "all"):
            continue
        path = ROOT / "notebooks" / filename
        notebook = nbformat.read(path, as_version=4)
        nbformat.validate(notebook)
        print(f"Executing {filename}", flush=True)
        client = NotebookClient(notebook, timeout=3600, kernel_name=args.kernel,
                                resources={"metadata": {"path": str(ROOT)}}, allow_errors=False)
        client.execute()
        # Keep the saved notebook portable even when a local kernel alias was used.
        notebook.metadata.kernelspec = dict(display_name="Python 3", language="python", name="python3")
        nbformat.validate(notebook)
        nbformat.write(notebook, path)
    square_report = ROOT / "results/figures_1_2/validation_report.json"
    if square_report.exists():
        status = json.loads(square_report.read_text(encoding="utf-8"))["status"]
        print(f"figures_1_2: {status}", flush=True)
    drag_report = ROOT / "results/figure_3/artifacts/iqm_drag/run.json"
    if drag_report.exists():
        report = json.loads(drag_report.read_text(encoding="utf-8"))
        print(f"figure_3: {len(report['sequence_names'])} sequences; "
              f"nominal and grid checks recorded", flush=True)
    if args.require_figure3:
        if not drag_report.exists():
            print("Figure 3 run.json was not generated.", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
