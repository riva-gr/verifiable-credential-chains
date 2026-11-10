from __future__ import annotations

import argparse
import contextlib
import json
import os
import runpy
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def appears_in_order(sequence, first, second):
    try:
        return sequence.index(first) < sequence.index(second)
    except ValueError:
        return False


def chain_metrics(ns, meta):
    chains = ns.get("chains", [])
    false = [c for c in chains if appears_in_order(c, meta["anchor_label"], meta["poison_label"])]
    return {"attack_success": int(bool(false)), "false_relation_chain_count": len(false),
            "poison_chain_count": sum(meta["poison_label"] in c for c in chains),
            "coverage": float(ns.get("coverage", 0.0)),
            "accuracy": float(ns.get("overall_accuracy", 0.0)),
            "precision": float(ns.get("overall_precision", 0.0)),
            "recall": float(ns.get("overall_recall", 0.0)),
            "f1": float(ns.get("f1", 0.0))}


def lpwe_classification_metrics(ns, nodes):
    data, find = ns["data"], ns["findCorrespondingGTseq"]
    initial, final = ns.get("initial_labels_of", {}), ns.get("final_labels_of", {})
    added, gts = ns.get("added_labels_of", {}), ns.get("ground_truth_sequences", [])
    tp = fp = total = recovered = 0
    for node in nodes:
        init = initial.get(node, set(data[node]))
        reference = set(find(init, gts))
        total += len(reference)
        recovered += len(set(final.get(node, init)) & reference)
        for label in added.get(node, set()):
            if label in reference:
                tp += 1
            else:
                fp += 1
    fn = total - recovered
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {"benign_evaluated_node_count": len(nodes),
            "benign_coverage": recovered / total if total else 0.0,
            "benign_accuracy": tp / (tp + fp + fn) if tp + fp + fn else 0.0,
            "benign_precision": precision, "benign_recall": recall,
            "benign_f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0}


def lpwe_metrics(ns, meta):
    targets = [int(v) for v in meta["target_benign_indices"]]
    malicious = {int(v) for v in meta["malicious_indices"]}
    added = ns.get("added_labels_of", {})
    affected = [n for n in targets if meta["poison_label"] in added.get(n, set())]
    benign = [n for n in range(len(ns["data"])) if n not in malicious]
    return {"attack_success": int(bool(affected)), "target_benign_count": len(targets),
            "affected_target_count": len(affected),
            "affected_target_rate": len(affected) / len(targets) if targets else 0.0,
            "coverage": float(ns.get("coverage", 0.0)), "accuracy": float(ns.get("accuracy", 0.0)),
            "precision": float(ns.get("precision", 0.0)), "recall": float(ns.get("recall", 0.0)),
            "f1": float(ns.get("f1", 0.0)), **lpwe_classification_metrics(ns, benign)}


def arguments(algo, experiment, params):
    if algo == "lpwe":
        return ["80", str(params["score_threshold"]), str(experiment), str(params["similarity"])]
    return [str(params["min_support"]), str(params["risup"]), str(experiment), "80"]


def run(algo, data_dir: Path, percentage, experiment, seed, params, key, work_root: Path,
        timeout) -> dict:
    work = work_root / key
    shutil.rmtree(work, ignore_errors=True)
    (work / data_dir.name).mkdir(parents=True)
    for name in ("ground_truth_sequences.csv", f"crs80_({experiment}).csv",
                 f"poisoning_metadata_({experiment}).json"):
        shutil.copyfile(data_dir / name, work / data_dir.name / name)
    out = work / "metrics.json"
    cmd = [sys.executable, str(Path(__file__).resolve()), algo, str(experiment),
           json.dumps(params), str(out)]
    env = dict(os.environ, PYTHONHASHSEED=str(seed), TERM="dumb", MPLBACKEND="Agg",
               OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
    start = time.time()
    metrics, error = {}, ""
    try:
        proc = subprocess.run(cmd, cwd=work, env=env, capture_output=True, text=True,
                              timeout=timeout)
        if proc.returncode == 0 and out.exists():
            status, metrics = "ok", json.loads(out.read_text())
        else:
            status = f"exit code {proc.returncode}"
            error = " ".join(proc.stderr.strip().splitlines()[-1:])[:300]
    except subprocess.TimeoutExpired:
        status = f"timeout>{timeout}s"
    wall = round(time.time() - start, 2)
    shutil.rmtree(work, ignore_errors=True)
    return {"status": status, "wall_s": wall, "error": error, "metrics": metrics}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("algo")
    ap.add_argument("experiment", type=int)
    ap.add_argument("params")
    ap.add_argument("output")
    a = ap.parse_args()
    meta = json.loads(Path("GT_and_CSV_files", f"poisoning_metadata_({a.experiment})."
                           "json").read_text())
    script = ROOT / "algorithms" / f"{a.algo}.py"
    sys.argv = [str(script), *arguments(a.algo, a.experiment, json.loads(a.params))]
    try:
        with open("algorithm_output.log", "w") as log, contextlib.redirect_stdout(log):
            ns = runpy.run_path(str(script), run_name="__main__")
        metrics = lpwe_metrics(ns, meta) if a.algo == "lpwe" else chain_metrics(ns, meta)
    except (Exception, SystemExit):
        traceback.print_exc()
        sys.exit(1)
    Path(a.output).write_text(json.dumps(metrics))


if __name__ == "__main__":
    main()
