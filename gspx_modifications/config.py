import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent


VARIANTS = {
    "chain": ("gspx_chain_level_filtering.py", "Chain-level filtering", "-", "C0"),
    "node": ("gspx_node_level_filtering.py", "Node-level filtering", "--", "C1"),
    "credential": ("gspx_credential_level_filtering.py", "Credential-level filtering", ":", "C2"),
    "agnostic": ("gspx.py", "Trust agnostic", "-.", "C3"),
}

DEFAULTS = {
    "output": str(ROOT / "results"),

    "percentages": list(range(10, 101, 10)),
    "experiments": 5,

    "variants": list(VARIANTS),
    "min_supports": [0.01, 0.02, 0.03, 0.04, 0.05, 0.07, 0.1],
    "risups": [1.0],
    "time_min_support": 0.03,

    "jobs": 1,
    "timeout": 400,
}
GENERATED_REPLICATES = 5

SETTINGS = dict(DEFAULTS, **json.loads(os.environ.get("GSPX_MODS_SETTINGS", "{}")))

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
MIN_SUPPORTS = SETTINGS["min_supports"]
RISUPS = SETTINGS["risups"]
TIME_MIN_SUPPORT = SETTINGS["time_min_support"]
JOBS = SETTINGS["jobs"]
TIMEOUT_S = SETTINGS["timeout"]


THREAD_ENV = {"OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
              "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
              "PYTHONHASHSEED": "0"}
