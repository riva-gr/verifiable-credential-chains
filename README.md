# Verifiable credential chains: GSP-X, CAM and LPwE

Code and experiments of the article *Building Trust on Arbitrary Properties of Microservices
Through Verifiable Credential Chains* by T. G. Papaioannou and V. Ritas (submitted to IEEE Access).

Each folder is a self-contained experiment with its own README, requirements and tests.

| Folder | Manuscript section |
|---|---|
| [`triple_comparison`](triple_comparison/README.md) | Original Algorithm Results: comparison of the three algorithms |
| [`sensitivity_experiment`](sensitivity_experiment/README.md) | Original Algorithm Results: parameter sensitivity |
| [`noise_experiment`](noise_experiment/README.md) | Original Algorithm Results: noise |
| [`scalability_experiment`](scalability_experiment/README.md) | Scalability Analysis |
| [`poisoning_experiment`](poisoning_experiment/README.md) | Robustness Against Targeted Credential Poisoning |
| [`bpi_triple_comparison`](bpi_triple_comparison/README.md) | Real-World Validation (BPI Challenge 2017) |
| [`gspx_modifications`](gspx_modifications/README.md) | Modified Algorithm Results: GSP-X |
| [`cam_modifications`](cam_modifications/README.md) | Modified Algorithm Results: CAM |
| [`lpwe_modifications`](lpwe_modifications/README.md) | Modified Algorithm Results: LPwE |

## Run an experiment (tested with Python 3.12.3)

Linux / macOS:

```bash
cd noise_experiment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run_experiment.py
```

Windows (PowerShell):

```powershell
cd noise_experiment
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run_experiment.py
```

`scalability_experiment` runs on Linux or macOS only.

Results are written to `results/` inside the folder. Options and quick checks are in each folder's README.

## License

MIT (see `LICENSE`). The files in `bpi_triple_comparison/data/` are derived from the BPI
Challenge 2017 event log and are subject to its terms of use (see `bpi_triple_comparison/data/README.md`).
