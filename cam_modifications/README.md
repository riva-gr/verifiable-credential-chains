# CAM modifications: trust-aware variants of CAM

Accuracy, F1 score and processing time of trust-agnostic CAM and its three trust-aware
variants for 10% to 100% of the ground-truth credentials (20 miscellaneous credentials),
at the best parameter setting within the tested grid.

| Variant | Script in `algorithms/` | Trust filter |
|---|---|---|
| `agnostic` | `cam.py` | none |
| `credential` | `cam_remove_untrustworthy_credentials.py` | credentials with trust < 0.5 are removed from every record |
| `node` | `cam_remove_untrustworthy_nodes.py` | records with mean credential trust < 0.5 are dropped |
| `link` | `cam_CAM_trustworthy_links.py` | a link is formed only if both credentials have trust ≥ 0.5 |

Ground-truth credentials receive trust values in [0.5, 1.0] and miscellaneous credentials in
[0, 0.5), drawn with a fixed seed inside the scripts.

## Setup (tested with Python 3.12.3)

Linux / macOS:

```bash
cd cam_modifications
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
cd cam_modifications
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```bash
python run_experiment.py
```

Figures are written to `results/figures/` and tables to `results/summary/`. The full run
takes about 1 hour, most of it in node-level runs that reach the 60 s limit.

Quick check (about 1 minute):

```bash
python run_experiment.py --experiments 2 --percentages 70,80 --output results_quick
```

Continue an interrupted run:

```bash
python run_experiment.py --resume
```

Redo the selection and the figures from existing results:

```bash
python run_experiment.py --steps select,plot
```

Tests (a few seconds):

```bash
python -m unittest discover tests
```

## Parameter selection

For each variant, percentage and replicate, the setting with the highest F1 is selected
using that replicate's ground truth: the results are the best observed performance within the
tested grid. Ties (equal F1, as printed with 4 decimals) go to the largest minimum support,
then the largest `risup`. A run that fails or exceeds the time limit is excluded from its own
replicate only; whether a run close to the limit finishes depends on the hardware.
Processing times are compared at a fixed minimum support (0.05), over the replicates whose
run completed, because the cost depends strongly on the minimum support.

Error bars are approximate 95% Student-t confidence intervals, mean ± t(0.975, n−1)·s/√n,
with s the sample standard deviation over the n replicates; they assume independent replicates.

| File in `results/summary/` | Content |
|---|---|
| `selected_parameters.csv` | selected setting and its metrics, per replicate |
| `optimal_summary.csv` | n, mean, SD and 95% CI per variant and percentage |
| `time_fixed_support.csv` | processing time at the fixed minimum support |
| `all_runs.csv`, `failed_runs.csv` | every run, and the runs that did not complete |

## Options

Lists are comma-separated, with no spaces.

| Option | Default | Meaning |
|---|---|---|
| `--output DIR` | `results` | output folder (inside the package folder, its name must start with `results`) |
| `--steps LIST` | `generate,run,select,plot` | steps to run |
| `--resume` | off | continue an interrupted run in `--output` |
| `--force` | off | delete `--output` and start again |
| `--retry-failed` | off | with `--resume`: rerun the runs that failed or timed out |
| `--experiments N` | `5` | replicates per percentage (1 to 5) |
| `--percentages LIST` | `10,20,...,100` | ground-truth percentages |
| `--variants LIST` | `credential,node,link,agnostic` | variants to run |
| `--min-supports LIST` | `0.01,...,0.05,0.07,0.1` | minimum support |
| `--risups LIST` | `1.0` | relative in-order support |
| `--time-min-support S` | `0.05` | minimum support of the processing-time comparison |
| `--jobs N` | `1` | runs executed at the same time |
| `--timeout S` | `60` | seconds allowed per run |

## License

MIT (see `LICENSE`). `environment-paper.txt` lists the package versions used for the paper.
