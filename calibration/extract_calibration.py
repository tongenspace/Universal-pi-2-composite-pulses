"""Extract the explicitly selected single-qubit fields from IQM quality metrics.

Usage: python extract_calibration.py source/SOURCE_1.json source/SOURCE_2.json --output-dir data
Only Python's standard library is required.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path

METRICS = {
    "prx_error": {
        "label": "PRX gate error", "unit": "%", "source_unit": "",
        "field_template": "metrics.rb.prx.drag_crf_sx.{qubit}.fidelity:par=d2",
        "transform": "100 * (1 - value)", "uncertainty_scale": 100,
    },
    "t1": {
        "label": "T1 time", "unit": "us", "source_unit": "s",
        "field_template": "characterization.model.{qubit}.t1_time",
        "transform": "1e6 * value", "uncertainty_scale": 1e6,
    },
    "t2_ramsey": {
        "label": "T2 time (Ramsey)", "unit": "us", "source_unit": "s",
        "field_template": "characterization.model.{qubit}.t2_time",
        "transform": "1e6 * value", "uncertainty_scale": 1e6,
    },
    "t2_echo": {
        "label": "T2 time (echo)", "unit": "us", "source_unit": "s",
        "field_template": "characterization.model.{qubit}.t2_echo_time",
        "transform": "1e6 * value", "uncertainty_scale": 1e6,
    },
    "readout_error": {
        "label": "Readout error", "unit": "%", "source_unit": "",
        "field_template": "metrics.ssro.measure_fidelity.constant.{qubit}.fidelity",
        "transform": "100 * (1 - value)", "uncertainty_scale": 100,
    },
    "readout_0_to_1": {
        "label": "Readout error 0 to 1", "unit": "%", "source_unit": "",
        "field_template": "metrics.ssro.measure_fidelity.constant.{qubit}.error_0_to_1",
        "transform": "100 * value", "uncertainty_scale": 100,
    },
    "readout_1_to_0": {
        "label": "Readout error 1 to 0", "unit": "%", "source_unit": "",
        "field_template": "metrics.ssro.measure_fidelity.constant.{qubit}.error_1_to_0",
        "transform": "100 * value", "uncertainty_scale": 100,
    },
}


def match_metric(field):
    """Exact allowlist: prevents readout-family mixing and two-qubit matches."""
    for metric, spec in METRICS.items():
        pattern = re.escape(spec["field_template"]).replace(r"\{qubit\}", r"(QB[1-9][0-9]*)")
        match = re.fullmatch(pattern, field)
        if match:
            return metric, match.group(1)
    return None


def display_value(metric, value):
    if value is None:
        return None
    if metric in ("prx_error", "readout_error"):
        return 100 * (1 - value)
    return value * METRICS[metric]["uncertainty_scale"]


def extract(paths):
    snapshots = []
    for path in sorted(map(Path, paths)):
        raw = path.read_bytes()
        source = json.loads(raw)
        if source["observation_set_type"] != "quality-metric-set":
            raise ValueError(f"Unexpected source type: {path.name}")
        date = path.name[:10]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            raise ValueError("A YYYY-MM-DD filename prefix is required.")
        if source["describes_id"] not in path.name:
            raise ValueError("Filename calibration ID disagrees with describes_id.")
        selected = []
        keys = set()
        for obs in source["observations"]:
            matched = match_metric(obs["dut_field"])
            if matched is None:
                continue
            metric, qubit = matched
            if matched in keys:
                raise ValueError(f"Duplicate {matched} in {path.name}")
            keys.add(matched)
            if obs["unit"] != METRICS[metric]["source_unit"]:
                raise ValueError(f"Unexpected units in {obs['dut_field']}")
            v, u = obs["value"], obs.get("uncertainty")
            if v is not None and not math.isfinite(v):
                raise ValueError("Non-finite observation")
            if u is not None and (not math.isfinite(u) or u < 0):
                raise ValueError("Invalid uncertainty")
            selected.append(dict(obs))
        selected.sort(key=lambda o: (int(match_metric(o["dut_field"])[1][2:]),
                                    list(METRICS).index(match_metric(o["dut_field"])[0])))
        snapshots.append({
            "snapshot_date": date,
            "source_filename": path.name,
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "source_observation_count": len(source["observations"]),
            "selected_observation_count": len(selected),
            "source_metadata": {k: v for k, v in source.items() if k != "observations"},
            "observations": selected,
        })
    return {
        "schema_version": "1.0",
        "device": "IQM Garnet",
        "provenance": {
            "source_directory": "source",
            "date_semantics": "snapshot_date is the date in each source filename; source timestamps are preserved.",
            "uncertainty_semantics": "Uncertainty is preserved as reported; its confidence level and distribution are unspecified in the source files.",
        },
        "metric_definitions": METRICS,
        "snapshots": snapshots,
    }


def to_rows(dataset):
    rows = []
    for snap in dataset["snapshots"]:
        meta = snap["source_metadata"]
        for obs in snap["observations"]:
            metric, qubit = match_metric(obs["dut_field"])
            spec = METRICS[metric]
            uncertainty = obs.get("uncertainty")
            rows.append({
                "snapshot_date": snap["snapshot_date"],
                "calibration_set_id": meta["describes_id"],
                "quality_metric_set_id": meta["observation_set_id"],
                "qubit": qubit, "qubit_index": int(qubit[2:]),
                "metric": metric, "value": display_value(metric, obs["value"]),
                "unit": spec["unit"],
                "uncertainty": None if uncertainty is None else uncertainty * spec["uncertainty_scale"],
                "source_value": obs["value"], "source_unit": obs["unit"],
                "source_uncertainty": uncertainty, "source_dut_field": obs["dut_field"],
                "observation_id": obs["observation_id"],
                "observation_invalid": obs["invalid"], "set_invalid": meta["invalid"],
                "quality_set_created_timestamp": meta["created_timestamp"],
                "quality_set_end_timestamp": meta["end_timestamp"],
                "observation_created_timestamp": obs["created_timestamp"],
                "observation_modified_timestamp": obs["modified_timestamp"],
                "source_filename": snap["source_filename"], "source_sha256": snap["source_sha256"],
            })
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="+", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("data"))
    args = parser.parse_args()
    dataset = extract(args.sources)
    rows = to_rows(dataset)
    if not rows:
        raise ValueError("No selected single-qubit observations found")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "garnet_single_qubit.json").write_text(
        json.dumps(dataset, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    with (args.output_dir / "garnet_single_qubit.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Extracted {len(rows)} observations across {len(dataset['snapshots'])} snapshots.")


if __name__ == "__main__":
    main()
