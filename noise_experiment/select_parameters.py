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
PARAMS = {"cam": ("min_support", "risup"), "gspx": ("min_support", "risup"),
          "lpwe": ("similarity", "score_threshold")}
PARAM_COLUMNS = ["min_support", "risup", "similarity", "score_threshold"]

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
        if rec["status"].startswith("skipped"):
            problems.append(f"{key}: skipped")
            continue
        algo, p, e, pr = job["algo"], job["p"], job["e"], job["params"]
        if algo == "lpwe":
            settings = [({"similarity": pr["similarity"], "score_threshold": t},
                         algorithm_runs.lpwe_relpath(pr["similarity"], t))
                        for t in config.SCORE_THRESHOLDS]
        else:
            settings = [({"min_support": pr["min_support"], "risup": pr["risup"]},
                         algorithm_runs.chain_relpath(algo, pr["min_support"], pr["risup"]))]
        for params, rel in settings:
            run = {"noise_size": job["noise"], "algorithm": algo, "percentage": p,
                   "replicate": e, **params, "status": rec["status"]}
            if rec["status"] == "ok":
                if rel not in rec["rows"]:
                    problems.append(f"{key}: no result for {params}")
                    continue
                values = rec["rows"][rel].split()
                if int(values[0]) != p:
                    problems.append(f"{key}: result row of percentage {values[0]}")
                    continue
                run.update(zip(METRICS, map(float, values[1:7])))
            runs.append(run)
    return runs, problems


def best(ok):
    names = PARAMS[ok[0]["algorithm"]]
    return max(ok, key=lambda r: (r["f1"], r[names[0]], r[names[1]]))


def part1_candidates(runs):
    return [r for r in runs if r["noise_size"] in config.PART1_NOISE_SIZES and
            (r["algorithm"] == "lpwe" or r["risup"] in config.PART1_RISUPS)]


def select(runs):
    groups = {}
    for r in runs:
        groups.setdefault((r["algorithm"], r["noise_size"], r["replicate"]), []).append(r)
    selected, empty = [], []
    for (algo, n, e), group in groups.items():
        ok = [r for r in group if r["status"] == "ok"]
        if not ok:
            empty.append(f"{algo} noise {n} replicate {e}")
            continue
        b = best(ok)
        selected.append({**b, "tied_settings": sum(r["f1"] == b["f1"] for r in ok),
                         "failed_settings": len(group) - len(ok)})
    if empty:
        sys.exit("no completed run to select from for: " + "; ".join(empty))
    order = {a: i for i, a in enumerate(config.ALGORITHMS)}
    selected.sort(key=lambda r: (order[r["algorithm"]], r["noise_size"], r["replicate"]))
    return selected


def interval(values):
    n = len(values)
    mean = statistics.mean(values)
    if n < 2:
        return mean, None, None, None
    sd = statistics.stdev(values)
    half = T975[n - 2] * sd / math.sqrt(n)
    return mean, sd, mean - half, mean + half


def summarize(selected):
    rows = []
    for algo in config.ALGORITHMS:
        for n in config.PART1_NOISE_SIZES:
            group = [r for r in selected if r["algorithm"] == algo and r["noise_size"] == n]
            if not group:
                continue
            row = {"algorithm": algo, "noise_size": n, "n": len(group)}
            for m in METRICS:
                mean, sd, low, high = interval([r[m] for r in group])
                row.update({f"{m}_mean": mean, f"{m}_sd": sd,
                            f"{m}_ci95_low": low, f"{m}_ci95_high": high})
            rows.append(row)
    return rows


def thresholds(runs):
    rows = []
    for algo in config.ALGORITHMS:
        tname = PARAMS[algo][1]
        values = config.SCORE_THRESHOLDS if algo == "lpwe" else config.RISUPS
        for n in config.NOISE_SIZES:
            for t in values:
                chosen, failed = [], 0
                for e in config.EXPERIMENTS:
                    group = [r for r in runs if r["algorithm"] == algo and r["noise_size"] == n
                             and r["replicate"] == e and r[tname] == t]
                    ok = [r for r in group if r["status"] == "ok"]
                    failed += len(group) - len(ok)
                    if ok:
                        chosen.append(best(ok))
                row = {"algorithm": algo, "noise_size": n, "threshold": t,
                       "n": len(chosen), "failed_runs": failed,
                       "accuracy_mean": None, "f1_mean": None,
                       "selected_per_replicate": "; ".join(
                           f"e{r['replicate']}: {PARAMS[algo][0]}={r[PARAMS[algo][0]]}"
                           for r in chosen)}
                if chosen:
                    row["accuracy_mean"] = statistics.mean(r["accuracy"] for r in chosen)
                    row["f1_mean"] = statistics.mean(r["f1"] for r in chosen)
                rows.append(row)
    return rows


def write_csv(path, rows, fields):
    def fmt(k, v):
        if v is None or k in PARAM_COLUMNS + ["threshold"] or not isinstance(v, float):
            return "" if v is None else v
        return f"{v:.10g}"
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: fmt(k, r.get(k)) for k in fields})


def main() -> None:
    prepare_dataset.verify_inputs()
    runs, problems = load_runs()
    if problems:
        print("\n".join(problems[:20]) + ("\n..." if len(problems) > 20 else ""))
        skipped = sum(x.endswith(": skipped") for x in problems)
        sys.exit(f"{len(problems)} runs of the grid are incomplete ({skipped} skipped by an "
                 "earlier version): complete them with run_experiment.py --resume"
                 + (" --retry-skipped" if skipped else ""))
    if not runs:
        sys.exit("no runs found: run the run step first")
    selected = select(part1_candidates(runs))
    summary = summarize(selected)
    part2 = thresholds(runs)

    out = config.RUN_DIR / "summary"
    out.mkdir(parents=True, exist_ok=True)
    ids = ["noise_size", "algorithm", "percentage", "replicate"]
    write_csv(out / "selected_parameters.csv", selected,
              ids + PARAM_COLUMNS + METRICS + ["tied_settings", "failed_settings"])
    write_csv(out / "optimal_summary.csv", summary,
              ["algorithm", "noise_size", "n"] + [f"{m}_{s}" for m in METRICS
                                                  for s in ("mean", "sd", "ci95_low", "ci95_high")])
    write_csv(out / "threshold_summary.csv", part2,
              ["algorithm", "noise_size", "threshold", "n", "failed_runs", "accuracy_mean",
               "f1_mean", "selected_per_replicate"])
    write_csv(out / "all_runs.csv", runs, ids + PARAM_COLUMNS + ["status"] + METRICS)
    failed = [r for r in runs if r["status"] != "ok"]
    write_csv(out / "failed_runs.csv", failed, ids + PARAM_COLUMNS + ["status"])
    (out / "selection_settings.json").write_text(json.dumps({
        "algorithms": config.ALGORITHMS, "percentages": config.PERCENTAGES,
        "replicates": len(config.EXPERIMENTS), "noise_sizes": config.NOISE_SIZES,
        "part1_noise_sizes": config.PART1_NOISE_SIZES,
        "min_supports": config.MIN_SUPPORTS, "risups": config.RISUPS,
        "part1_risups": config.PART1_RISUPS,
        "similarities": config.SIMILARITIES, "score_thresholds": config.SCORE_THRESHOLDS,
        "selection": "highest F1 per algorithm, noise size and replicate (Part 2: and "
                     "threshold), using that replicate's ground truth",
        "f1_comparison": "exact, as printed by the algorithms (4 decimals)",
        "tie_rule": "largest min_support, then largest risup (CAM, GSP-X); "
                    "largest similarity, then largest score_threshold (LPwE)",
        "failed_runs": "excluded from the selection of their own replicate only",
        "error_bars": "approximate 95% Student-t CI: mean +/- t(0.975, n-1) * s / sqrt(n), "
                      "s = sample standard deviation (ddof=1)",
        "run_settings": "settings.json",
    }, indent=2))

    for r in summary:
        print(f"  {r['algorithm']:5s} noise {r['noise_size']:5d}  F1 {r['f1_mean']:.3f}  "
              f"accuracy {r['accuracy_mean']:.3f}")
    empty = [r for r in part2 if r["n"] == 0]
    print(f"{len(failed)} failed runs; {len(empty)} thresholds without a completed run; "
          f"tables written to {out}")


if __name__ == "__main__":
    main()
