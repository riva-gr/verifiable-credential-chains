# Scalability: GSP-X, CAM and LPwE

Processing time and peak resident memory of GSP-X, CAM and LPwE for 1,000 to 20,000 identities,
with five datasets (seeds) per size (80% ground truth, 100 miscellaneous credentials).

| Algorithm | Parameters |
|---|---|
| GSP-X, CAM | minimum support 0.02, `risup` 1.0 |
| LPwE | similarity 0.2, score threshold 0.8 |

## Setup (tested with Python 3.12.3, Linux or macOS)

```bash
cd scalability_experiment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python run_experiment.py
```

Time and memory are measured, so the runs are executed one at a time; close other programs and
keep the computer from sleeping. LPwE at
20,000 identities needs about 8 GB of memory. Figures are written to `results/figures/` and
tables to `results/summary/`.

Quick check:

```bash
python run_experiment.py --sizes 1000,2500 --seeds 1729 --output results_quick
```

Continue an interrupted run:

```bash
python run_experiment.py --resume
```

Redo the tables and the figures from existing results:

```bash
python run_experiment.py --steps summarize,plot
```

Tests (a few seconds):

```bash
python -m unittest discover tests
```

## Measurements

Each algorithm script runs unchanged as its own process. Processing time is the script's own
running time, which excludes loading the input files; peak memory is the maximum resident set
size of the script's process. A run that fails or exceeds the time limit is left out of its
point.

Error bars are approximate 95% Student-t confidence intervals, mean ± t(0.975, n−1)·s/√n,
with s the sample standard deviation over the n seeds; they assume independent seeds.

| File in `results/summary/` | Content |
|---|---|
| `summary.csv` | means and 95% CI of time and memory per algorithm and size |
| `raw_results.csv` | one row per run, with the run's accuracy and F1 score |
| `execution_log.csv` | status of every run |

## Options

Lists are comma-separated, with no spaces.

| Option | Default | Meaning |
|---|---|---|
| `--output DIR` | `results` | output folder (inside the package folder, its name must start with `results`) |
| `--steps LIST` | `generate,run,summarize,plot` | steps to run |
| `--resume` | off | continue an interrupted run in `--output` |
| `--force` | off | delete `--output` and start again |
| `--retry-failed` | off | with `--resume`: rerun the runs that failed or timed out |
| `--sizes LIST` | `1000,2500,5000,10000,20000` | identities per dataset |
| `--seeds LIST` | `1729,2718,3141,5772,8119` | one dataset per seed and size |
| `--algorithms LIST` | `gspx,cam,lpwe` | algorithms to run |
| `--min-support X` | `0.02` | GSP-X and CAM minimum support |
| `--risup X` | `1.0` | GSP-X and CAM relative in-order support |
| `--similarity X` | `0.2` | LPwE similarity threshold |
| `--score-threshold X` | `0.8` | LPwE score threshold |
| `--timeout S` | `7200` | seconds allowed per algorithm run |

## License

MIT (see `LICENSE`). `environment-paper.txt` lists the package versions used for the paper.
