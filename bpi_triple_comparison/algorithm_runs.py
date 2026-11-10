from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import config

LPWE_BLOCK = re.compile(
    r"Score threshold: (\S+)\s+Running time: (\S+)\s+Coverage: (\S+)\s+"
    r"Accuracy: (\S+)\s+Precision: (\S+)\s+Recall: (\S+)\s+F1 score: (\S+)")


def chain_relpath(algo: str, min_support: float, risup: float) -> str:

    if algo == "cam":
        return f"cam_results/min_support_{float(min_support)}/CAM_risup_{risup:.1f}.txt"
    return f"gspx_results/min_support_{float(min_support)}/gspx_risup_{risup:.1f}.txt"


def lpwe_relpath(similarity: float, score: float) -> str:
    return (f"lpwe_results/similarity_{float(similarity)}/"
            f"LPWE_score_threshold_{score:.1f}.txt")


def run(algo: str, run_dir: Path, p: int, e: int, params: dict, key: str) -> dict:

    work = config.WORK_DIR / key
    shutil.rmtree(work, ignore_errors=True)
    inputs = work / config.DATA_DIRNAME
    inputs.mkdir(parents=True)
    src = run_dir / "GT_and_CSV_files"
    for name in ("ground_truth_sequences.csv", f"crs{p}_({e}).csv"):
        shutil.copyfile(src / name, inputs / name)

    if algo in ("cam", "gspx"):
        args = [str(params["min_support"]), str(params["risup"]), str(e), str(p)]
    else:
        args = [str(p), ",".join(str(t) for t in params["score_thresholds"]),
                str(e), str(params["similarity"])]
    cmd = [sys.executable, str(config.ALGORITHM_DIR / f"{algo}.py")] + args
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

    if status == "ok" and algo in ("cam", "gspx"):
        rel = chain_relpath(algo, params["min_support"], params["risup"])
        produced = [q for q in work.rglob("*.txt")]
        if len(produced) != 1 or produced[0].relative_to(work).as_posix() != rel:
            status = f"unexpected results files {[q.name for q in produced]}"
        else:
            rows[rel] = produced[0].read_text()
    elif status == "ok":
        blocks = LPWE_BLOCK.findall(proc.stdout)
        for b in blocks:
            score, duration, cov, acc, prec, rec, f1 = b
            text = f"\n{p}  {duration} {cov} {acc} {prec}  {rec}  {f1}  "
            if p == 100:
                text += "\n"
            rows[lpwe_relpath(params["similarity"], float(score))] = text
        if len(rows) != len(params["score_thresholds"]):
            status, rows = f"parsed {len(rows)} metric blocks", {}

    shutil.rmtree(work, ignore_errors=True)
    return {"status": status, "wall_s": wall, "error": error, "rows": rows}
