import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALGORITHM_DIR = ROOT / "algorithms"
GENERATOR_FILE = ROOT / "generator" / "create_files.py"

DEFAULTS = {

    "output": str(ROOT / "results"),

    "sizes": [1000, 2500, 5000, 10000, 20000],
    "seeds": [1729, 2718, 3141, 5772, 8119],

    "algorithms": ["gspx", "cam", "lpwe"],
    "min_support": 0.02,
    "risup": 1.0,
    "similarity": 0.2,
    "score_threshold": 0.8,

    "timeout": 7200,
}


GENERATOR = {"availability": 0.80, "miscellaneous_count": 100,
             "minimum_misc_per_record": 2, "maximum_misc_per_record": 11}
GT_PERCENTAGE = 80
DATA_DIRNAME = "GT_and_CSV_files"


THREAD_ENV = {"OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
              "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
              "PYTHONHASHSEED": "0"}

SETTINGS = dict(DEFAULTS)
SETTINGS.update(json.loads(os.environ.get("SCALABILITY_SETTINGS", "{}")))

OUT_DIR = Path(SETTINGS["output"]).resolve()
RUN_DIR = OUT_DIR
DATA_DIR = OUT_DIR / "datasets"
WORK_DIR = OUT_DIR / "_work"
JOB_DIR = OUT_DIR / "_job_outputs"

SIZES = list(SETTINGS["sizes"])
SEEDS = list(SETTINGS["seeds"])
ALGORITHMS = list(SETTINGS["algorithms"])
MIN_SUPPORT, RISUP = SETTINGS["min_support"], SETTINGS["risup"]
SIMILARITY, SCORE_THRESHOLD = SETTINGS["similarity"], SETTINGS["score_threshold"]
TIMEOUT_S = SETTINGS["timeout"]

LABELS = {"gspx": "GSP-X", "cam": "CAM", "lpwe": "LPwE"}


def dataset_file(size, experiment) -> Path:
    return DATA_DIR / f"N_{int(size)}" / f"crs80_seed_{int(experiment)}.csv"


GT_FILE = DATA_DIR / "ground_truth_sequences.csv"
