import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALGORITHM_DIR = ROOT / "algorithms"

WALLETS_FILE = ROOT / "data" / "bpi2017_wallets.csv"
REFERENCE_FILE = ROOT / "data" / "reference_chains.csv"
SHA256 = {
    WALLETS_FILE: "4cd53885bef733ee7f1516512a5c3c80742e33dc76b709a53e4580d59b31f3cf",
    REFERENCE_FILE: "779907fcdf1cd19d220ae6d68db26d0f5c676b30f472541147aa64fc6b02aee6",
}

DEFAULTS = {
    "output": str(ROOT / "results"),

    "seed": 2017,
    "wallets_per_replicate": 1000,
    "percentages": [10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
    "experiments": 5,

    "min_supports": [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.1,
                     0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    "risups": [0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    "similarities": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
    "score_thresholds": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
    "algorithms": ["cam", "gspx", "lpwe"],

    "jobs": 1,
    "timeout": 1800,
}

SETTINGS = dict(DEFAULTS)
SETTINGS.update(json.loads(os.environ.get("BPI_COMPARISON_SETTINGS", "{}")))

OUT_DIR = Path(SETTINGS["output"]).resolve()
RUN_DIR = OUT_DIR
WORK_DIR = OUT_DIR / "_work"
JOB_DIR = OUT_DIR / "_job_outputs"

SEED = SETTINGS["seed"]
WALLETS_PER_REPLICATE = SETTINGS["wallets_per_replicate"]
PERCENTAGES = list(SETTINGS["percentages"])
EXPERIMENTS = list(range(SETTINGS["experiments"]))

MIN_SUPPORTS = list(SETTINGS["min_supports"])
RISUPS = list(SETTINGS["risups"])
SIMILARITIES = list(SETTINGS["similarities"])
SCORE_THRESHOLDS = list(SETTINGS["score_thresholds"])
ALGORITHMS = list(SETTINGS["algorithms"])

JOBS = SETTINGS["jobs"]
TIMEOUT_S = SETTINGS["timeout"]


THREAD_ENV = {"OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
              "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
              "PYTHONHASHSEED": "0"}


DATA_DIRNAME = "GT_and_CSV_files"
