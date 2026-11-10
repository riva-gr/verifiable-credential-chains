# Targeted credential poisoning: GSP-X, CAM and LPwE

An adversary replaces 0% to 10% of 1,000 identities (outside the target group) with records
that imitate the longest ground-truth chain (`J1`…`J11`) and place the injected credential
`POISON_Z` after `J11`. Attack success and F1 score of GSP-X, CAM and LPwE are reported for
five random seeds per poisoning level (80% ground truth, 100 miscellaneous credentials).

| Algorithm | Parameters | Attack succeeds when |
|---|---|---|
| GSP-X, CAM | minimum support 0.02, `risup` 1.0 | a returned chain contains `J11` before `POISON_Z` |
| LPwE | similarity 0.2, score threshold 0.8 | `POISON_Z` is added to a benign identity of the target group |

## Setup (tested with Python 3.12.3)

Linux / macOS:

```bash
cd poisoning_experiment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
cd poisoning_experiment
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```bash
python run_experiment.py --jobs 4
```

Processing time is not reported in this experiment, so runs can be executed several at a time
(`--jobs`). Figures are written to `results/figures/` and tables to `results/summary/`. 

Quick check:

```bash
python run_experiment.py --seeds 1729 --percentages 0,2 --output results_quick
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

Attack success rate is the fraction of completed runs in which the attack succeeds. F1 is the
algorithm's own F1 for GSP-X and CAM, and for LPwE the F1 over the benign identities
(adversary-controlled identities excluded), computed as `lpwe.py` computes it. A run that fails
or exceeds the time limit is left out of its point.

Error bars are approximate 95% Student-t confidence intervals, mean ± t(0.975, n−1)·s/√n,
with s the sample standard deviation over the n seeds; they assume independent seeds.

| File in `results/summary/` | Content |
|---|---|
| `summary.csv` | attack success rate, means and 95% CI per algorithm and poisoning level |
| `raw_results.csv` | one row per algorithm, poisoning level and seed |
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
| `--size N` | `1000` | identities per dataset |
| `--seeds LIST` | `1729,2718,3141,5772,8119` | one dataset per seed and poisoning level |
| `--percentages LIST` | `0,1,...,10` | poisoned identities (%) |
| `--algorithms LIST` | `gspx,cam,lpwe` | algorithms to run |
| `--min-support X` | `0.02` | GSP-X and CAM minimum support |
| `--risup X` | `1.0` | GSP-X and CAM relative in-order support |
| `--similarity X` | `0.2` | LPwE similarity threshold |
| `--score-threshold X` | `0.8` | LPwE score threshold |
| `--jobs N` | `1` | runs executed at the same time |
| `--timeout S` | `600` | seconds allowed per algorithm run |

## License

MIT (see `LICENSE`). `environment-paper.txt` lists the package versions used for the paper.
