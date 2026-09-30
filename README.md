# Reproducing the UVH composite-pulse results

This repository contains the numerical theory validation, the archived IQM
Garnet measurements, and the historical single-qubit calibration used to
document the device. All figures and tables are generated from files included
here. The three sections have separate requirements files so their tested
environments remain reproducible.

| Section | Contents | Main entry point |
|---|---|---|
| [`experiment/`](experiment/) | Twelve archived IQM jobs, per-qubit and ensemble data, validation panels A–D | [`02_process_validate_iqm_data_publication.ipynb`](experiment/02_process_validate_iqm_data_publication.ipynb) |
| [`theory/`](theory/) | Fixed phase lists, square-pulse checks for Figures 1–2, and finite-level DRAG simulation for Figure 3 | [`scripts/execute_notebooks.py`](theory/scripts/execute_notebooks.py) |
| [`calibration/`](calibration/) | Two historical Garnet quality-metric JSON files and selected single-qubit plots | [`garnet_single_qubit_calibration.ipynb`](calibration/garnet_single_qubit_calibration.ipynb) |

Use Python 3.12 for the pinned package versions. Each section can be run in its
own virtual environment. Run these commands from the repository root after
activating the appropriate environment:

```sh
python -m pip install -r experiment/requirements.txt
python experiment/reproduce.py
```

The experiment command checks the SHA-256 manifest for every archived job,
reconstructs the tables under `experiment/data/processed/`, and regenerates
`experiment/figures/validation_panels_A_B.pdf` and
`experiment/figures/validation_panels_C_D.pdf`. It uses the twelve local job
archives. The job manifest in `experiment/metadata/job_manifest.csv` lists the
family and panel of every run.

For the theory notebooks, start with a fresh environment:

```sh
python -m pip install -r theory/requirements.txt
python -m pytest -q theory/tests
python theory/scripts/execute_notebooks.py
```

The theory runner executes the fixed square-pulse and DRAG notebooks in
fresh kernels. Figures 1–2 are written under `theory/results/figures_1_2/`;
Figure 3 is written under `theory/results/figure_3/`. The Figure 3 calculation
may take around 20 minutes on a desktop CPU. The notebooks retain their source
calculations and phase lists.

For the calibration notebook, use its pinned environment and reproduction
instructions in [`calibration/README.md`](calibration/README.md):

```sh
python -m pip install -r calibration/requirements.txt
python calibration/reproduce.py
```

Each workflow writes within its own section. The original quality-metric
files are in `calibration/source/`, and the selected data used for plots are in
`calibration/data/`.

## Data organization

The experimental raw archive is under `experiment/data/raw/iqm_jobs/<job_id>/`.
Each job contains a submitted run definition, job record, sweep arrays, array
index, provenance, and SHA-256 checksums. The processing notebook derives
per-qubit values and ensemble means with standard errors from those arrays.
The checked-in processed tables and PDF panels allow inspection without
rerunning the notebooks.

The theory notebooks use fixed inputs in `theory/data/`. The Figures 1–2
notebook reports numerical checks for the listed phases and regenerates the
panels. Figure 3 stores its calculation settings and diagnostics with the
figure data. Its contour figure has four rows (UVH1s, UVH5s, UVH9s, and
UVH13s) and two columns (two- and five-level models).

The calibration section retains PRX and readout errors, T1, Ramsey T2, and
echo T2. Its data describe the device snapshots; they are not estimates of
the composite sequences' experimental fidelity. The source timestamps do not
by themselves assign a calibration to a particular job.

The archived sweep data make the experimental analysis reproducible without
running new quantum jobs. Repeating the experiment on live hardware would be a
different activity and is not part of these reproduction commands.

## Citation

Citation metadata for this repository release are provided in
[`CITATION.cff`](CITATION.cff).
