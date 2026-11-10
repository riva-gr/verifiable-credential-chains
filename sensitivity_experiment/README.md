# Parameter sensitivity: GSP-X, CAM and LPwE

Accuracy and F1 score of GSP-X, CAM and LPwE for every parameter setting, at 80% of the ground
truth and a noise pool of 100 credentials (the 80% datasets of the triple comparison).

## Setup (tested with Python 3.12.3)

Linux / macOS:

```bash
cd sensitivity_experiment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
cd sensitivity_experiment
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```bash
python run_experiment.py --jobs 4
```

Processing time is not reported in this experiment, so runs can be executed several at a time
(`--jobs`). Figures are written to `results/figures/` and tables to `results/summary/`. The full
run takes about 20 minutes with `--jobs 4` (about 1 hour with `--jobs 1`), most of it in CAM
runs with minimum support 0.01 and low `risup` that reach the 120 s limit.

Quick check (about 2 minutes):

```bash
python run_experiment.py --experiments 2 --min-supports 0.03,0.08 --similarities 0.1,0.5 --output results_quick
```

Continue an interrupted run:

```bash
python run_experiment.py --jobs 4 --resume
```

Redo the tables and the figures from existing results:

```bash
python run_experiment.py --steps summarize,plot
```

Tests (a few seconds):

```bash
python -m unittest discover tests
```

## Summary

No setting is selected: every setting of the grid is shown, with the mean over the replicates
whose run completed. A run that fails or exceeds the time limit is left out of the mean of its
setting; a setting without a completed run has no point. Whether a run close to the limit
finishes depends on the hardware.

Error bars are approximate 95% Student-t confidence intervals, mean ± t(0.975, n−1)·s/√n,
with s the sample standard deviation over the n replicates; they assume independent replicates.

| File in `results/summary/` | Content |
|---|---|
| `sensitivity.csv` | n, mean, SD and 95% CI per algorithm and setting |
| `all_runs.csv`, `failed_runs.csv` | every run, and the runs that did not complete |

## Options

Lists are comma-separated, with no spaces.

| Option | Default | Meaning |
|---|---|---|
| `--output DIR` | `results` | output folder (inside the package folder, its name must start with `results`) |
| `--steps LIST` | `generate,run,summarize,plot` | steps to run |
| `--resume` | off | continue an interrupted run in `--output` |
| `--force` | off | delete `--output` and start again |
| `--retry-failed` | off | with `--resume`: rerun the runs that failed or timed out |
| `--retry-skipped` | off | with `--resume`: run the runs that earlier versions skipped |
| `--seed N` | `1` | dataset seed |
| `--experiments N` | `5` | replicate files |
| `--algorithms LIST` | `cam,gspx,lpwe` | algorithms to run |
| `--min-supports LIST` | `0.01,0.02,...,0.08` | CAM and GSP-X minimum support (one line each) |
| `--risups LIST` | `0.1,0.2,...,1.0` | CAM and GSP-X relative in-order support |
| `--similarities LIST` | `0.1,0.2,...,0.8` | LPwE similarity threshold (one line each) |
| `--score-thresholds LIST` | `0.1,0.2,...,1.0` | LPwE score threshold |
| `--jobs N` | `1` | runs executed at the same time |
| `--timeout S` | `120` | seconds allowed per algorithm run |

## License

MIT (see `LICENSE`). `environment-paper.txt` lists the package versions used for the paper.
