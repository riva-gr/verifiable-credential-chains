# Noise experiment: GSP-X, CAM and LPwE vs size of the noise pool

Each synthetic identity holds credentials of one ground-truth chain (65 credentials in 10
chains) plus 2 to 11 unrelated credentials from a pool of miscellaneous ("noise")
credentials. At 70% of the ground truth, the experiment varies the size of that pool:

- accuracy and F1 score of the three algorithms at the best setting within the tested grid,
  for noise pools of 65, 100, 300, 500 and 1000 credentials;
- accuracy for every `risup` threshold (GSP-X, CAM) and score threshold (LPwE), for noise pools
  of 12, 65, 100, 300, 500 and 1000 credentials.

With a noise pool of 100 the datasets are the 70% datasets of the triple comparison.

## Setup (tested with Python 3.12.3)

Linux / macOS:

```bash
cd noise_experiment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
cd noise_experiment
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
run takes about 2 hours with `--jobs 4` (about 8 hours with `--jobs 1`), most of it in CAM and
GSP-X runs with low `risup` and small noise pools that reach the 120 s limit.

Quick check (about 5 minutes):

```bash
python run_experiment.py --experiments 2 --noise-sizes 300,1000 --risups 0.5,1.0 --similarities 0.1,0.5 --output results_quick
```

Continue an interrupted run:

```bash
python run_experiment.py --jobs 4 --resume
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

For each algorithm, noise size and replicate, the setting with the highest F1 is selected
using that replicate's ground truth: the results are the best observed performance within the
tested grid (for the accuracy and F1 figures, `risup` 0.5 to 1.0, as in the triple comparison).
In the threshold figures, the same rule is applied within each threshold value: per replicate,
the minimum support (GSP-X, CAM) or similarity threshold (LPwE) with the highest F1; a dot is
the mean accuracy over the replicates, and a grey × marks a threshold at which no run completed.

Ties (equal F1, as printed with 4 decimals) go to the largest minimum support, then the largest
`risup` (CAM, GSP-X), or to the largest similarity, then the largest score threshold (LPwE). A
run that fails or exceeds the time limit is excluded from its own replicate only; whether a run
close to the limit finishes depends on the hardware.

Error bars are approximate 95% Student-t confidence intervals, mean ± t(0.975, n−1)·s/√n,
with s the sample standard deviation over the n replicates; they assume independent replicates.

| File in `results/summary/` | Content |
|---|---|
| `selected_parameters.csv` | selected setting and its metrics, per replicate |
| `optimal_summary.csv` | n, mean, SD and 95% CI per algorithm and noise size |
| `threshold_summary.csv` | n, mean accuracy and selected settings per threshold value |
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
| `--retry-skipped` | off | with `--resume`: run the runs that earlier versions skipped |
| `--seed N` | `1` | dataset seed |
| `--experiments N` | `5` | replicate files per noise size |
| `--noise-sizes LIST` | `12,65,100,300,500,1000` | noise pool sizes |
| `--part1-noise-sizes LIST` | `65,100,300,500,1000` | noise pool sizes of the accuracy and F1 figures |
| `--algorithms LIST` | `cam,gspx,lpwe` | algorithms to run |
| `--min-supports LIST` | `0.01,0.02,...,0.05` | CAM and GSP-X minimum support |
| `--risups LIST` | `0.1,0.2,...,1.0` | CAM and GSP-X relative in-order support |
| `--similarities LIST` | `0.1,0.2,...,0.9` | LPwE similarity threshold |
| `--score-thresholds LIST` | `0.1,0.2,...,0.9` | LPwE score threshold |
| `--jobs N` | `1` | runs executed at the same time |
| `--timeout S` | `120` | seconds allowed per algorithm run |

## License

MIT (see `LICENSE`). `environment-paper.txt` lists the package versions used for the paper.
