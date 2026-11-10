from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time

import config

BLOCK = re.compile(
    r"Score threshold: (\S+)\s+Running time: (\S+)\s+Coverage: (\S+)\s+"
    r"Accuracy: (\S+)\s+Precision: (\S+)\s+Recall: (\S+)\s+F1 score: (\S+)")


def threshold_key(t: float) -> str:
    return f"{t:.1f}"


def run(variant: str, p: int, e: int, params: dict, key: str) -> dict:
    work = config.WORK_DIR / key
    shutil.rmtree(work, ignore_errors=True)
    inputs = work / config.DATA_DIRNAME
    inputs.mkdir(parents=True)
    for name in ("ground_truth_sequences.csv", f"crs{p}_({e}).csv"):
        shutil.copyfile(config.DATA_DIR / name, inputs / name)
    script = config.ALGORITHM_DIR / config.VARIANTS[variant][0]
    cmd = [sys.executable, str(script), str(p),
           ",".join(str(t) for t in params["score_thresholds"]), str(e),
           str(params["similarity"])]
    env = dict(os.environ, TERM="dumb", MPLBACKEND="Agg", **config.THREAD_ENV)
    start = time.time()
    rows, error = {}, ""
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
        for t, dur, cov, acc, prec, rec, f1 in BLOCK.findall(proc.stdout):
            rows[threshold_key(float(t))] = f"{p}  {dur} {cov} {acc} {prec}  {rec}  {f1}"
        wanted = {threshold_key(t) for t in params["score_thresholds"]}
        if set(rows) != wanted:
            status, rows = f"metrics found for {len(rows)} of {len(wanted)} thresholds", {}
    shutil.rmtree(work, ignore_errors=True)
    return {"status": status, "wall_s": wall, "error": error, "rows": rows}
