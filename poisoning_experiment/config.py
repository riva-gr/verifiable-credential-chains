import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALGORITHM_DIR = ROOT / "algorithms"
GENERATOR_FILE = ROOT / "generator" / "create_poisoning_datasets.py"

DEFAULTS = {

    "output": str(ROOT / "results"),

    "size": 1000,
    "seeds": [1729, 2718, 3141, 5772, 8119],
    "percentages": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    "poison_label": "POISON_Z",

    "algorithms": ["gspx", "cam", "lpwe"],
    "min_support": 0.02,
    "risup": 1.0,
    "similarity": 0.2,
    "score_threshold": 0.8,

    "jobs": 1,
    "timeout": 600,
}

SETTINGS = dict(DEFAULTS)
SETTINGS.update(json.loads(os.environ.get("POISONING_SETTINGS", "{}")))

OUT_DIR = Path(SETTINGS["output"]).resolve()
RUN_DIR = OUT_DIR
DATA_DIR = OUT_DIR / "datasets"
WORK_DIR = OUT_DIR / "_work"
JOB_DIR = OUT_DIR / "_job_outputs"

SIZE = SETTINGS["size"]
SEEDS = list(SETTINGS["seeds"])
PERCENTAGES = list(SETTINGS["percentages"])
POISON_LABEL = SETTINGS["poison_label"]
ALGORITHMS = list(SETTINGS["algorithms"])
MIN_SUPPORT, RISUP = SETTINGS["min_support"], SETTINGS["risup"]
SIMILARITY, SCORE_THRESHOLD = SETTINGS["similarity"], SETTINGS["score_threshold"]
JOBS = SETTINGS["jobs"]
TIMEOUT_S = SETTINGS["timeout"]

LABELS = {"gspx": "GSP-X", "cam": "CAM", "lpwe": "LPwE"}
GT_PERCENTAGE = 80
DATA_DIRNAME = "GT_and_CSV_files"


def data_dir(percentage) -> Path:
    return DATA_DIR / f"poison_{int(percentage)}pct" / DATA_DIRNAME
