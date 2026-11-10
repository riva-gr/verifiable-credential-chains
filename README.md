# Verifiable credential chains: GSP-X, CAM and LPwE

Code and experiments of the article *Building Trust on Arbitrary Properties of Microservices
Through Verifiable Credential Chains* by T. G. Papaioannou and V. Ritas (submitted to IEEE Access).

Each folder is a self-contained experiment with its own README, requirements and tests.

| Folder | Manuscript section | Full run |
|---|---|---|
| [`triple_comparison`](triple_comparison/README.md) | Original Algorithm Results: comparison of the three algorithms | about 2 h |
| [`sensitivity_experiment`](sensitivity_experiment/README.md) | Original Algorithm Results: parameter sensitivity | about 20 min (`--jobs 4`) |
| [`noise_experiment`](noise_experiment/README.md) | Original Algorithm Results: noise | about 2 h (`--jobs 4`) |
| [`scalability_experiment`](scalability_experiment/README.md) | Scalability Analysis | about 4 h |
| [`poisoning_experiment`](poisoning_experiment/README.md) | Robustness Against Targeted Credential Poisoning | about 8 min (`--jobs 4`) |
| [`bpi_triple_comparison`](bpi_triple_comparison/README.md) | Real-World Validation (BPI Challenge 2017) | about 10.5 h |
| [`gspx_modifications`](gspx_modifications/README.md) | Modified Algorithm Results: GSP-X | about 45 min |
| [`cam_modifications`](cam_modifications/README.md) | Modified Algorithm Results: CAM | about 1 h |
| [`lpwe_modifications`](lpwe_modifications/README.md) | Modified Algorithm Results: LPwE | about 2 h |

## Run an experiment (tested with Python 3.12.3)

```bash
cd noise_experiment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run_experiment.py
```

Results are written to `results/` inside the folder. Options, quick checks and Windows
instructions (where supported) are in each folder's README.

## License

MIT (see `LICENSE`). The files in `bpi_triple_comparison/data/` are derived from the BPI
Challenge 2017 event log and are subject to its terms of use (see `bpi_triple_comparison/data/README.md`).
