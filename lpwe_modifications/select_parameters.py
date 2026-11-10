from __future__ import annotations

import csv
import json
import math
import statistics
import sys

import algorithm_runs
import config
import execute
import prepare_dataset

METRICS = ["time", "coverage", "accuracy", "precision", "recall", "f1"]
PARAM_COLUMNS = ["similarity", "score_threshold"]

T975 = [12.706205, 4.302653, 3.182446, 2.776445, 2.570582, 2.446912, 2.364624,
        2.306004, 2.262157, 2.228139, 2.200985, 2.178813, 2.160369, 2.144787,
        2.131450, 2.119905, 2.109816, 2.100922, 2.093024, 2.085963, 2.079614,
        2.073873, 2.068658, 2.063899, 2.059539, 2.055529, 2.051831, 2.048407,
        2.045230, 2.042272]
MAX_REPLICATES = len(T975) + 1


def load_runs():
    runs, problems = [], []
    for job in execute.job_list():
        key = execute.job_key(job)
        path = config.JOB_DIR / f"{key}.json"
        if not path.exists():
            problems.append(f"{key}: not run")
            continue
        rec = json.loads(path.read_text())
        for t in config.SCORE_THRESHOLDS:
            run = {"variant": job["variant"], "percentage": job["p"], "replicate": job["e"],
                   "similarity": job["params"]["similarity"], "score_threshold": t,
                   "status": rec["status"]}
            if rec["status"] == "ok":
                row = rec["rows"].get(algorithm_runs.threshold_key(t))
                if row is None:
                    problems.append(f"{key}: no result for score threshold {t}")
                    continue
                values = row.split()
                if int(values[0]) != job["p"]:
                    problems.append(f"{key}: result row of percentage {values[0]}")
                    continue
                run.update(zip(METRICS, map(float, values[1:7])))
            runs.append(run)
    return runs, problems


def select(runs):
    groups = {}
    for r in runs:
        groups.setdefault((r["variant"], r["percentage"], r["replicate"]), []).append(r)
    selected, empty = [], []
    for (variant, p, e), group in groups.items():
        ok = [r for r in group if r["status"] == "ok"]
        if not ok:
            empty.append(f"{variant} {p}% replicate {e}")
            continue
        best = max(ok, key=lambda r: (r["f1"], r["similarity"], r["score_threshold"]))
        tied = sum(r["f1"] == best["f1"] for r in ok)
        selected.append({**best, "tied_settings": tied,
                         "failed_settings": len(group) - len(ok)})
    if empty:
        sys.exit("no completed run to select from for: " + "; ".join(empty))
    order = {v: i for i, v in enumerate(config.ALGORITHMS)}
    selected.sort(key=lambda r: (order[r["variant"]], r["percentage"], r["replicate"]))
    return selected


def interval(values):
    n = len(values)
    mean = statistics.mean(values)
    if n < 2:
        return mean, None, None, None
    sd = statistics.stdev(values)
    half = T975[n - 2] * sd / math.sqrt(n)
    return mean, sd, mean - half, mean + half


def summarize(rows, metrics):
    out = []
    for variant in config.ALGORITHMS:
        for p in config.PERCENTAGES:
            group = [r for r in rows if r["variant"] == variant and r["percentage"] == p]
            if not group:
                continue
            row = {"variant": variant, "percentage": p, "n": len(group)}
            for m in metrics:
                mean, sd, low, high = interval([r[m] for r in group])
                row.update({f"{m}_mean": mean, f"{m}_sd": sd,
                            f"{m}_ci95_low": low, f"{m}_ci95_high": high})
            out.append(row)
    return out


def fixed_setting_runs(runs):
    s, t = config.TIME_SIMILARITY, config.TIME_SCORE_THRESHOLD
    return [x for x in runs if x["status"] == "ok" and x["similarity"] == s
            and x["score_threshold"] == t]


def write_csv(path, rows, fields):
    def fmt(k, v):
        if v is None or k in PARAM_COLUMNS or not isinstance(v, float):
            return "" if v is None else v
        return f"{v:.10g}"
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: fmt(k, r.get(k)) for k in fields})


def stats_fields(metrics):
    return ["variant", "percentage", "n"] + [f"{m}_{s}" for m in metrics
                                             for s in ("mean", "sd", "ci95_low", "ci95_high")]


def main() -> None:
    prepare_dataset.verify_inputs()
    if config.TIME_SIMILARITY not in config.SIMILARITIES or \
            config.TIME_SCORE_THRESHOLD not in config.SCORE_THRESHOLDS:
        sys.exit("the time setting is not in the similarity and score-threshold grids")
    runs, problems = load_runs()
    if problems:
        print("\n".join(problems[:20]) + ("\n..." if len(problems) > 20 else ""))
        sys.exit(f"{len(problems)} runs of the grid are incomplete: complete them with "
                 "run_experiment.py --resume")
    if not runs:
        sys.exit("no runs found: run the run step first")
    selected = select(runs)
    summary = summarize(selected, METRICS)
    times = summarize(fixed_setting_runs(runs), ["time"])

    out = config.RUN_DIR / "summary"
    out.mkdir(parents=True, exist_ok=True)
    ids = ["variant", "percentage", "replicate"]
    write_csv(out / "selected_parameters.csv", selected,
              ids + PARAM_COLUMNS + METRICS + ["tied_settings", "failed_settings"])
    write_csv(out / "optimal_summary.csv", summary, stats_fields(METRICS))
    write_csv(out / "time_fixed_setting.csv", times, stats_fields(["time"]))
    write_csv(out / "all_runs.csv", runs, ids + PARAM_COLUMNS + ["status"] + METRICS)
    failed = [r for r in runs if r["status"] != "ok"]
    write_csv(out / "failed_runs.csv", failed, ids + PARAM_COLUMNS + ["status"])
    (out / "selection_settings.json").write_text(json.dumps({
        "variants": config.ALGORITHMS, "percentages": config.PERCENTAGES,
        "replicates": len(config.EXPERIMENTS),
        "similarities": config.SIMILARITIES, "score_thresholds": config.SCORE_THRESHOLDS,
        "selection": "highest F1 per variant, percentage and replicate, "
                     "using that replicate's ground truth",
        "f1_comparison": "exact, as printed by the scripts (4 decimals)",
        "tie_rule": "largest similarity, then largest score_threshold",
        "failed_runs": "excluded from the selection of their own replicate only",
        "processing_time": f"at similarity {config.TIME_SIMILARITY}, score threshold "
                           f"{config.TIME_SCORE_THRESHOLD}, over the completed runs",
        "error_bars": "approximate 95% Student-t CI: mean +/- t(0.975, n-1) * s / sqrt(n), "
                      "s = sample standard deviation (ddof=1)",
        "run_settings": "settings.json",
    }, indent=2))

    for r in summary:
        print(f"  {r['variant']:10s} {r['percentage']:3d}%  F1 {r['f1_mean']:.3f}  "
              f"accuracy {r['accuracy_mean']:.3f}")
    for r in times:
        if r["n"] < len(config.EXPERIMENTS):
            print(f"  time at the fixed setting: {r['variant']} "
                  f"{r['percentage']}% has {r['n']} completed runs")
    print(f"{len(failed)} failed runs; tables written to {out}")


if __name__ == "__main__":
    main()
