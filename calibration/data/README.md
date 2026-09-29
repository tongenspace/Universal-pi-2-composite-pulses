# Data dictionary

`garnet_single_qubit.json` is the canonical selected-source dataset. Its
`snapshots` retain source metadata and selected observations in their original
units and precision. `metric_definitions` documents exact field templates and
the transformations into the CSV and figures. There are two snapshots, each
with 20 qubits × seven quantities = 140 observations.

`garnet_single_qubit.csv` is the normalized, long-form companion. Rows are ordered
by snapshot date, numeric qubit index, and the metric order below. Blank CSV
uncertainties mean missing, never zero. Neither selected snapshot has missing
values or uncertainties.

| Metric code | Interpretation | CSV `unit` | Conversion from source |
|---|---|---|---|
| `prx_error` | PRX error derived from reported fidelity | `%` | `100 * (1 - value)` |
| `t1` | Relaxation time | `us` | `1e6 * value` |
| `t2_ramsey` | Ramsey coherence time | `us` | `1e6 * value` |
| `t2_echo` | Echo coherence time | `us` | `1e6 * value` |
| `readout_error` | Readout error derived from the selected fidelity | `%` | `100 * (1 - value)` |
| `readout_0_to_1` | Reported directional readout error 0→1 | `%` | `100 * value` |
| `readout_1_to_0` | Reported directional readout error 1→0 | `%` | `100 * value` |

## CSV columns

| Column(s) | Meaning |
|---|---|
| `snapshot_date` | Date prefix in the source filename, ISO format |
| `calibration_set_id` | Source `describes_id` |
| `quality_metric_set_id` | Source `observation_set_id` |
| `qubit`, `qubit_index` | Original QB label and numeric index (1–20) |
| `metric`, `value`, `unit` | Normalized quantity, full-precision value, and display unit |
| `uncertainty` | Reported uncertainty after conversion; percentage points for error, µs for time |
| `source_value`, `source_unit`, `source_uncertainty` | Original values; an empty unit is dimensionless |
| `source_dut_field` | Exact original field, including `:par=d2` where present |
| `observation_id` | Original observation identifier |
| `observation_invalid`, `set_invalid` | Original validity flags; `False` in all selected rows |
| `quality_set_created_timestamp`, `quality_set_end_timestamp` | Original quality-set record timestamps with UTC `Z` |
| `observation_created_timestamp`, `observation_modified_timestamp` | Original per-observation timestamps, without an offset as supplied |
| `source_filename`, `source_sha256` | Filename in `../source/` and SHA-256 hash of that file's bytes |

## Selection

The exact allowlist is implemented in `../extract_calibration.py` and repeated
explicitly in the notebook. It preserves the PRX `drag_crf_sx` fidelity,
`measure_fidelity` readout fidelity and both directional errors, and the three
coherence/relaxation times. Every selected field contains exactly one QB label.
All CZ/two-qubit Clifford, single-qubit Clifford, alternate `measure` readout,
QND fidelity/repeatability, and QNDness metrics are excluded.

Uncertainty confidence levels and distributions are unspecified in the source.
Time quantities are hardware characteristics, not gate-error probabilities.
No experimental pulse-sequence fidelity or job assignment is inferred.
