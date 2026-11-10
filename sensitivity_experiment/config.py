import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALGORITHM_DIR = ROOT / "algorithms"
GENERATOR_FILE = ROOT / "generator" / "create_files_config.py"

DEFAULTS = {

    "output": str(ROOT / "results"),

    "seed": 1,
    "chains": 10,
    "min_length": 2,
    "identities_per_chain": 100,
    "noise_size": 100,
    "misc_min": 2,
    "misc_max": 11,
    "percentages": [80],
    "experiments": 5,


    "min_supports": [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08],
    "risups": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    "similarities": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
    "score_thresholds": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    "algorithms": ["cam", "gspx", "lpwe"],

    "jobs": 1,
    "timeout": 120,
}

SETTINGS = dict(DEFAULTS)
SETTINGS.update(json.loads(os.environ.get("SENSITIVITY_SETTINGS", "{}")))

OUT_DIR = Path(SETTINGS["output"]).resolve()
RUN_DIR = OUT_DIR
WORK_DIR = OUT_DIR / "_work"
JOB_DIR = OUT_DIR / "_job_outputs"

SEED = SETTINGS["seed"]
CHAINS = SETTINGS["chains"]
MIN_LENGTH = SETTINGS["min_length"]
IDENTITIES_PER_CHAIN = SETTINGS["identities_per_chain"]
NOISE_SIZE = SETTINGS["noise_size"]
MISC_MIN, MISC_MAX = SETTINGS["misc_min"], SETTINGS["misc_max"]
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
