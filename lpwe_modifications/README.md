# LPwE modifications: trust-aware variants of LPwE

Accuracy, F1 score and processing time of trust-agnostic LPwE and its three trust-aware
variants for 10% to 100% of the ground-truth credentials (20 miscellaneous credentials),
at the best parameter setting within the tested grid.

| Variant | Script in `algorithms/` | Trust filter |
|---|---|---|
| `agnostic` | `lpwe.py` | none |
| `prediction` | `lpwe_3_add_only_trustworthy_labels_.py` | only labels with trust ≥ 0.5 are added as predictions |
| `node` | `lpwe_1_remove_untrustworthy_nodes.py` | nodes with mean label trust < 0.5 are removed |
| `label` | `lpwe_2_similarity_by_trustorthiness.py` | Jaccard similarity uses only labels with trust ≥ 0.5 |

Ground-truth credentials receive trust values in [0.5, 1.0] and miscellaneous credentials in
[0, 0.5), drawn with a fixed seed inside the scripts.

## Setup (tested with Python 3.12.3)

Linux / macOS:

```bash
cd lpwe_modifications
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
cd lpwe_modifications
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```bash
python run_experiment.py
```

Figures are written to `results/figures/` and tables to `results/summary/`. The full run
takes about 2 hours.

Quick check (about 2 minutes):

```bash
python run_experiment.py --experiments 2 --percentages 70,80 --similarities 0.2,0.6 --output results_quick
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

For each variant, percentage and replicate, the setting (similarity threshold, score threshold)
with the highest F1 is selected using that replicate's ground truth: the results are the best
observed performance within the tested grid. Ties (equal F1, as printed with 4 decimals) go to
the largest similarity threshold, then the largest score threshold. Each run evaluates all score
thresholds at once. A run that fails or exceeds the time limit is excluded from its own
replicate only; whether a run close to the limit finishes depends on the hardware.
Processing times are compared at a fixed setting (similarity 0.2, score threshold 0.8), over
the replicates whose run completed, because the cost depends strongly on the similarity threshold.

Error bars are approximate 95% Student-t confidence intervals, mean ± t(0.975, n−1)·s/√n,
with s the sample standard deviation over the n replicates; they assume independent replicates.

| File in `results/summary/` | Content |
|---|---|
| `selected_parameters.csv` | selected setting and its metrics, per replicate |
| `optimal_summary.csv` | n, mean, SD and 95% CI per variant and percentage |
| `time_fixed_setting.csv` | processing time at the fixed setting |
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
| `--variants LIST` | `prediction,node,label,agnostic` | variants to run |
| `--similarities LIST` | `0.1,0.2,...,0.9` | similarity threshold |
| `--score-thresholds LIST` | `0.1,0.2,...,0.9` | score threshold (one decimal) |
| `--time-similarity S` | `0.2` | similarity threshold of the processing-time comparison |
| `--time-score-threshold T` | `0.8` | score threshold of the processing-time comparison |
| `--jobs N` | `1` | runs executed at the same time |
| `--timeout S` | `300` | seconds allowed per run |

## License

MIT (see `LICENSE`). `environment-paper.txt` lists the package versions used for the paper.
