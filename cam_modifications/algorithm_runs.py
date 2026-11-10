from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time

import config

FIELDS = ["Running time", "Overall Coverage", "Overall Accuracy", "Overall Precision",
          "Overall Recall", "Overall F1 score"]
PATTERNS = [re.compile(re.escape(f) + r":\s*(\S+)") for f in FIELDS]


def run(variant: str, p: int, e: int, params: dict, key: str) -> dict:
    work = config.WORK_DIR / key
    shutil.rmtree(work, ignore_errors=True)
    inputs = work / config.DATA_DIRNAME
    inputs.mkdir(parents=True)
    for name in ("ground_truth_sequences.csv", f"crs{p}_({e}).csv"):
        shutil.copyfile(config.DATA_DIR / name, inputs / name)
    script = config.ALGORITHM_DIR / config.VARIANTS[variant][0]
    cmd = [sys.executable, str(script), str(params["min_support"]), str(params["risup"]),
           str(e), str(p)]
    env = dict(os.environ, TERM="dumb", MPLBACKEND="Agg", **config.THREAD_ENV)
    start = time.time()
    row, error = "", ""
    try:
        proc = subprocess.run(cmd, cwd=work, env=env, capture_output=True,
                              text=True, timeout=config.TIMEOUT_S)
        status = "ok" if proc.returncode == 0 else f"exit code {proc.returncode}"
        if proc.returncode:
            error = " ".join(proc.stderr.strip().splitlines()[-1:])[:300]
    except subprocess.TimeoutExpired:
        status = f"timeout>{config.TIMEOUT_S}s"
    wall = round(time.time() - start, 2)
    if status == "ok":
        found = [m.group(1) for m in (pat.search(proc.stdout) for pat in PATTERNS) if m]
        if len(found) == len(FIELDS):
            t, cov, acc, prec, rec, f1 = found
            row = f"{p}  {t} {cov} {acc} {prec}  {rec}  {f1}"
        else:
            status = "metrics not found in the output"
    shutil.rmtree(work, ignore_errors=True)
    return {"status": status, "wall_s": wall, "error": error, "row": row}
