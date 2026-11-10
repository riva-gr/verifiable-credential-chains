import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent


VARIANTS = {
    "prediction": ("lpwe_3_add_only_trustworthy_labels_.py", "Prediction-level filtering", "-", "C0"),
    "node": ("lpwe_1_remove_untrustworthy_nodes.py", "Node-level filtering", "--", "C1"),
    "label": ("lpwe_2_similarity_by_trustorthiness.py", "Label-level filtering", ":", "C2"),
    "agnostic": ("lpwe.py", "Trust agnostic", "-.", "C3"),
}

DEFAULTS = {
    "output": str(ROOT / "results"),

    "percentages": list(range(10, 101, 10)),
    "experiments": 5,

    "variants": list(VARIANTS),
    "similarities": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
    "score_thresholds": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
    "time_similarity": 0.2,
    "time_score_threshold": 0.8,

    "jobs": 1,
    "timeout": 300,
}
GENERATED_REPLICATES = 5

SETTINGS = dict(DEFAULTS, **json.loads(os.environ.get("LPWE_MODS_SETTINGS", "{}")))

OUT_DIR = RUN_DIR = Path(SETTINGS["output"])
DATA_DIRNAME = "GT_and_CSV_files_noise20"
DATA_DIR = RUN_DIR / DATA_DIRNAME
JOB_DIR = RUN_DIR / "_job_outputs"
WORK_DIR = RUN_DIR / "_work"
ALGORITHM_DIR = ROOT / "algorithms"
GENERATOR_FILE = ROOT / "generator" / "create_files.py"

PERCENTAGES = SETTINGS["percentages"]
EXPERIMENTS = list(range(SETTINGS["experiments"]))
ALGORITHMS = SETTINGS["variants"]
SIMILARITIES = SETTINGS["similarities"]
SCORE_THRESHOLDS = SETTINGS["score_thresholds"]
TIME_SIMILARITY = SETTINGS["time_similarity"]
TIME_SCORE_THRESHOLD = SETTINGS["time_score_threshold"]
JOBS = SETTINGS["jobs"]
TIMEOUT_S = SETTINGS["timeout"]


THREAD_ENV = {"OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
              "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
              "PYTHONHASHSEED": "0"}
