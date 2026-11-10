# Real-world validation: GSP-X, CAM and LPwE on the BPI Challenge 2017 log

Accuracy, F1 score and processing time of GSP-X, CAM and LPwE on the BPI Challenge 2017
loan-application log, for 10% to 100% of the reference-chain credentials, at the best
parameter setting within the tested grid.

## Setup (tested with Python 3.12.3)

Linux / macOS:

```bash
cd bpi_triple_comparison
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
cd bpi_triple_comparison
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```bash
python run_experiment.py
```

Figures are written to `results/figures/` and tables to `results/summary/`.

Quick check:

```bash
python run_experiment.py --experiments 2 --percentages 20,80 --output results_quick
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

For each algorithm, percentage and sample, the setting with the highest F1 is selected
using that sample's ground truth: the results are the best observed performance within the
tested grid. Ties (equal F1, as printed with 4 decimals) go to the largest minimum support,
then the largest `risup` (CAM, GSP-X), or to the largest similarity, then the largest score
threshold (LPwE). A run that fails or exceeds the time limit is excluded from its own sample
only; whether a run close to the limit finishes depends on the hardware.

Error bars are approximate 95% Student-t confidence intervals, mean ± t(0.975, n−1)·s/√n,
with s the sample standard deviation over the n samples; they assume independent samples.

| File in `results/summary/` | Content |
|---|---|
| `selected_parameters.csv` | selected setting and its metrics, per sample |
| `optimal_summary.csv` | n, mean, SD and 95% CI per algorithm and percentage |
| `all_runs.csv`, `failed_runs.csv` | every run, and the runs that did not complete |

## Options

Lists are comma-separated, with no spaces.

| Option | Default | Meaning |
|---|---|---|
| `--output DIR` | `results` | output folder (inside the package folder, its name must start with `results`) |
| `--steps LIST` | `prepare,run,select,plot` | steps to run |
| `--resume` | off | continue an interrupted run in `--output` |
| `--force` | off | delete `--output` and start again |
| `--retry-failed` | off | with `--resume`: rerun the runs that failed or timed out |
| `--retry-skipped` | off | with `--resume`: run the runs that earlier versions skipped |
| `--seed N` | `2017` | sampling and masking seed |
| `--experiments N` | `5` | independent wallet samples |
| `--percentages LIST` | `10,20,...,100` | shares of reference-chain credentials kept |
| `--wallets N` | `1000` | wallets per sample |
| `--algorithms LIST` | `cam,gspx,lpwe` | algorithms to run |
| `--min-supports LIST` | `0.01,0.02,...,0.1,0.2,...,1.0` | CAM and GSP-X minimum support |
| `--risups LIST` | `0.5,0.6,...,1.0` | CAM and GSP-X relative in-order support |
| `--similarities LIST` | `0.1,0.2,...,0.9` | LPwE similarity threshold |
| `--score-thresholds LIST` | `0.1,0.2,...,0.9` | LPwE score threshold |
| `--jobs N` | `1` | runs executed at the same time |
| `--timeout S` | `1800` | seconds allowed per algorithm run |

## Rebuild the files in `data/` (optional)

1. Download `BPI Challenge 2017.xes.gz` from https://doi.org/10.4121/uuid:5f3067df-f10b-45da-b98b-86ae4c7a310b
2. Convert it to CSV:

   ```bash
   pip install pm4py
   python -c "import pm4py; pm4py.read_xes('BPI Challenge 2017.xes.gz').to_csv('bpi_2017.csv', index=False)"
   ```

3. Build the wallet and reference-chain files in a separate folder:

   ```bash
   python converter/bpi2017_to_wallets.py bpi_2017.csv --data-dir data_rebuilt
   ```

The two files in `data_rebuilt/` should be identical to those in `data/`.

## License

The source code is released under the MIT License (see `LICENSE`). The files in `data/` are
derived from the BPI Challenge 2017 log and follow its terms (see `data/README.md`).
`environment-paper.txt` lists the package versions used for the paper.
