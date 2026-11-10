from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import config

LPWE_BLOCK = re.compile(
    r"Score threshold: (\S+)\s+Running time: (\S+)\s+Coverage: (\S+)\s+"
    r"Accuracy: (\S+)\s+Precision: (\S+)\s+Recall: (\S+)\s+F1 score: (\S+)")
FIELDS = ["time_s", "coverage", "accuracy", "precision", "recall", "f1"]


def arguments(algo, experiment, params):
    if algo == "lpwe":
        return [str(config.GT_PERCENTAGE), str(params["score_threshold"]), str(experiment),
                str(params["similarity"])]
    return [str(params["min_support"]), str(params["risup"]), str(experiment),
            str(config.GT_PERCENTAGE)]


def chain_relpath(algo, params) -> str:
    s, r = float(params["min_support"]), params["risup"]
    if algo == "cam":
        return f"cam_results/min_support_{s}/CAM_risup_{r:.1f}.txt"
    return f"gspx_results/min_support_{s}/gspx_risup_{r:.1f}.txt"


def read_results(algo, work: Path, output: str, params) -> dict:
    if algo == "lpwe":
        blocks = LPWE_BLOCK.findall(output)
        if len(blocks) != 1:
            raise ValueError(f"{len(blocks)} metric blocks in the output of lpwe.py")
        values = blocks[0][1:]
    else:
        path = work / chain_relpath(algo, params)
        if not path.exists():
            raise ValueError(f"{path.name} was not written")
        values = path.read_text().split()[1:]
    if len(values) != len(FIELDS):
        raise ValueError(f"unexpected results {values}")
    return {k: float(v) for k, v in zip(FIELDS, values)}


def peak_memory_mib(usage) -> float:
    return usage.ru_maxrss / (1024 * 1024 if sys.platform == "darwin" else 1024)


def run(algo, dataset: Path, gt_file: Path, experiment, params, key, work_root: Path,
        timeout) -> dict:
    work = work_root / key
    shutil.rmtree(work, ignore_errors=True)
    inputs = work / config.DATA_DIRNAME
    inputs.mkdir(parents=True)
    shutil.copyfile(dataset, inputs / f"crs{config.GT_PERCENTAGE}_({experiment}).csv")
    shutil.copyfile(gt_file, inputs / "ground_truth_sequences.csv")
    cmd = [sys.executable, str(config.ALGORITHM_DIR / f"{algo}.py"),
           *arguments(algo, experiment, params)]
    env = dict(os.environ, TERM="dumb", MPLBACKEND="Agg", **config.THREAD_ENV)

    log = work / "algorithm_output.log"
    stopped = threading.Event()
    with open(log, "w") as out:
        proc = subprocess.Popen(cmd, cwd=work, env=env, stdout=out, stderr=subprocess.STDOUT)

        def stop():
            stopped.set()
            proc.kill()

        timer = threading.Timer(timeout, stop)
        timer.start()
        try:
            _, wait_status, usage = os.wait4(proc.pid, 0)
        finally:
            timer.cancel()
        proc.returncode = os.waitstatus_to_exitcode(wait_status)

    output = log.read_text(errors="replace")
    result = {"status": "ok", "peak_memory_mib": round(peak_memory_mib(usage), 4),
              "error": "", "metrics": {}}
    if stopped.is_set():
        result["status"] = f"timeout>{timeout}s"
    elif proc.returncode:
        result["status"] = f"exit code {proc.returncode}"
        result["error"] = " ".join(output.strip().splitlines()[-1:])[:300]
    else:
        try:
            result["metrics"] = read_results(algo, work, output, params)
        except ValueError as exc:
            result["status"], result["error"] = "no results", str(exc)
    shutil.rmtree(work, ignore_errors=True)
    return result
