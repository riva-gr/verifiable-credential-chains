from __future__ import annotations

import csv
import json
import math
import statistics
import sys

import config
import execute
import prepare_dataset

MEASURES = ["time_s", "peak_memory_mib"]
METRICS = ["coverage", "accuracy", "precision", "recall", "f1"]

T975 = [12.706205, 4.302653, 3.182446, 2.776445, 2.570582, 2.446912, 2.364624,
        2.306004, 2.262157, 2.228139, 2.200985, 2.178813, 2.160369, 2.144787,
        2.131450, 2.119905, 2.109816, 2.100922, 2.093024, 2.085963, 2.079614,
        2.073873, 2.068658, 2.063899, 2.059539, 2.055529, 2.051831, 2.048407,
        2.045230, 2.042272]
MAX_SEEDS = len(T975) + 1


def load_runs():
    runs, problems = [], []
    for job in execute.job_list():
        rec = execute.stored(job)
        if rec is None:
            problems.append(f"{execute.job_key(job)}: not run")
            continue
        runs.append({"algorithm": config.LABELS[job["algo"]], "identities": job["n"],
                     "experiment": job["e"], "seed": job["seed"], "status": rec["status"],
                     "peak_memory_mib": rec["peak_memory_mib"], "error": rec["error"],
                     **rec["metrics"]})
    return runs, problems


def mean_and_ci95(values):
    if not values:
        return "", ""
    mean = statistics.mean(values)
    if len(values) < 2:
        return mean, ""
    return mean, T975[len(values) - 2] * statistics.stdev(values) / math.sqrt(len(values))


def summarize(runs):
    rows = []
    for algo in config.ALGORITHMS:
        label = config.LABELS[algo]
        for n in config.SIZES:
            group = [r for r in runs if r["algorithm"] == label and r["identities"] == n]
            ok = [r for r in group if r["status"] == "ok"]
            row = {"algorithm": label, "identities": n, "completed_runs": len(ok),
                   "failed_runs": len(group) - len(ok)}
            for m in MEASURES:
                row[f"mean_{m}"], row[f"{m}_ci95"] = mean_and_ci95([r[m] for r in ok])
            for m in ("accuracy", "f1"):
                row[f"mean_{m}"] = mean_and_ci95([r[m] for r in ok])[0]
            rows.append(row)
    return rows


def write_csv(path, rows, fields):
    def fmt(v):
        return f"{v:.10g}" if isinstance(v, float) else v
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: fmt(r.get(k, "")) for k in fields})


def main() -> None:
    prepare_dataset.verify_inputs()
    runs, problems = load_runs()
    if problems:
        print("\n".join(problems[:20]) + ("\n..." if len(problems) > 20 else ""))
        sys.exit(f"{len(problems)} runs are missing: complete them with "
                 "run_experiment.py --resume")
    rows = summarize(runs)
    out = config.RUN_DIR / "summary"
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "summary.csv", rows,
              ["algorithm", "identities", "completed_runs", "failed_runs"]
              + [f"{s}{m}{e}" for m in MEASURES for s, e in (("mean_", ""), ("", "_ci95"))]
              + ["mean_accuracy", "mean_f1"])
    write_csv(out / "raw_results.csv", runs,
              ["algorithm", "identities", "experiment", "seed", "status"] + MEASURES
              + METRICS + ["error"])
    (out / "summary_settings.json").write_text(json.dumps({
        "sizes": config.SIZES, "seeds": config.SEEDS, "algorithms": config.ALGORITHMS,
        "min_support": config.MIN_SUPPORT, "risup": config.RISUP,
        "similarity": config.SIMILARITY, "score_threshold": config.SCORE_THRESHOLD,
        "timeout_s": config.TIMEOUT_S, "generator": config.GENERATOR,
        "time": "the script's own running time, excluding loading the input files",
        "memory": "maximum resident set size of the script's process (MiB)",
        "failed_runs": "left out of their point",
        "error_bars": "approximate 95% Student-t CI: mean +/- t(0.975, n-1) * s / sqrt(n), "
                      "s = sample standard deviation (ddof=1)",
        "run_settings": "settings.json"}, indent=2))
    for r in rows:
        if r["completed_runs"]:
            print(f"  {r['algorithm']:5s} N={r['identities']:<6d} time {r['mean_time_s']:10.3f} s"
                  f"   memory {r['mean_peak_memory_mib']:9.2f} MiB   F1 {r['mean_f1']:.4f}"
                  f"   ({r['completed_runs']} runs)")
        else:
            print(f"  {r['algorithm']:5s} N={r['identities']:<6d} no completed run")
    failed = [r for r in runs if r["status"] != "ok"]
    print(f"{len(failed)} failed runs; tables written to {out}")


if __name__ == "__main__":
    main()
