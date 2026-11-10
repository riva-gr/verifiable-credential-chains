from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from config import DATA_DIRNAME, DEFAULTS, GENERATED_REPLICATES, VARIANTS

STEPS = {"generate": "prepare_dataset.py", "run": "execute.py",
         "select": "select_parameters.py", "plot": "plot.py"}
ANALYSIS_STEPS = {"select", "plot"}
SETTINGS_VARIABLE = "LPWE_MODS_SETTINGS"


GRID_KEYS = ["variants", "similarities", "score_thresholds"]


def floats(text):
    return [float(v) for v in text.split(",")]


def ints(text):
    return [int(v) for v in text.split(",")]


def parse_args():
    d = DEFAULTS
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_argument_group("output and steps")
    g.add_argument("--output", default=d["output"],
                   help="output folder (default: results/)")
    g.add_argument("--steps", default=",".join(STEPS),
                   help="comma-separated subset of: " + ", ".join(STEPS))
    g.add_argument("--resume", action="store_true",
                   help="continue an interrupted run in --output")
    g.add_argument("--force", action="store_true",
                   help="delete --output and start from scratch")
    g.add_argument("--retry-failed", action="store_true",
                   help="with --resume: run again the runs that failed or timed out")

    g = ap.add_argument_group("dataset")
    g.add_argument("--experiments", type=int, default=d["experiments"],
                   help=f"replicates per percentage, 1 to {GENERATED_REPLICATES} (default 5)")
    g.add_argument("--percentages", type=ints, default=d["percentages"],
                   help="ground-truth percentages, e.g. 10,20,30 (default 10..100)")

    g = ap.add_argument_group("parameter search")
    g.add_argument("--variants", default=",".join(d["variants"]),
                   help="comma-separated subset of: " + ", ".join(VARIANTS))
    g.add_argument("--similarities", type=floats, default=d["similarities"],
                   help="similarity thresholds (default 0.1,...,0.9)")
    g.add_argument("--score-thresholds", type=floats, default=d["score_thresholds"],
                   help="score thresholds, one decimal (default 0.1,...,0.9)")
    g.add_argument("--time-similarity", type=float, default=d["time_similarity"],
                   help="similarity threshold of the processing-time comparison (default 0.2)")
    g.add_argument("--time-score-threshold", type=float, default=d["time_score_threshold"],
                   help="score threshold of the processing-time comparison (default 0.8)")

    g = ap.add_argument_group("execution")
    g.add_argument("--jobs", type=int, default=d["jobs"],
                   help="runs executed at the same time (default 1)")
    g.add_argument("--timeout", type=int, default=d["timeout"],
                   help="seconds allowed per single run (default 300)")
    return ap.parse_args()


def check_values(name, values, one_decimal=False):
    if not values:
        sys.exit(f"--{name}: no values")
    if len(set(values)) != len(values):
        sys.exit(f"--{name}: duplicate values")
    for v in values:
        if not (math.isfinite(v) and 0 < v <= 1):
            sys.exit(f"--{name}: {v} is not in (0, 1]")
        if one_decimal and v != round(v, 1):
            sys.exit(f"--{name}: {v} has more than one decimal")


def check_output(out: Path) -> None:
    if ROOT.is_relative_to(out):
        sys.exit(f"--output {out} contains the package folder {ROOT}; "
                 "choose another folder")
    for folder in (out, *out.parents):
        if (folder / "run_experiment.py").exists() and (
                folder == out or not out.relative_to(folder).parts[0].startswith("results")):
            sys.exit(f"--output {out} is inside the package folder {folder}: there it must be "
                     "a folder whose name starts with 'results' (e.g. results_quick)")
    for folder in (out, *out.parents):
        if ROOT.is_relative_to(folder):
            break
        if folder.name in (".git", ".venv") or (folder / "pyvenv.cfg").exists():
            sys.exit(f"--output {out} is inside {folder} (repository metadata or a "
                     "virtual environment); choose another folder")
    if out.exists() and not out.is_dir():
        sys.exit(f"--output {out} is a file")


def main() -> None:
    a = parse_args()
    steps = [s.strip() for s in a.steps.split(",") if s.strip()]
    variants = [x.strip() for x in a.variants.split(",") if x.strip()]
    for s in steps:
        if s not in STEPS:
            sys.exit(f"unknown step '{s}'; choose from {', '.join(STEPS)}")
    for x in variants:
        if x not in VARIANTS:
            sys.exit(f"unknown variant '{x}'; choose from {', '.join(VARIANTS)}")
    if not variants or len(set(variants)) != len(variants):
        sys.exit("--variants: one or more distinct values")
    steps = [s for s in STEPS if s in steps]
    if not 1 <= a.experiments <= GENERATED_REPLICATES:
        sys.exit(f"--experiments must be from 1 to {GENERATED_REPLICATES}")
    if len(set(a.percentages)) != len(a.percentages) or \
            not all(p in range(10, 101, 10) for p in a.percentages):
        sys.exit("--percentages: distinct values from 10, 20, ..., 100")
    check_values("similarities", a.similarities)
    check_values("score-thresholds", a.score_thresholds, one_decimal=True)
    if a.time_similarity not in a.similarities or \
            a.time_score_threshold not in a.score_thresholds:
        sys.exit("--time-similarity and --time-score-threshold must be in the grids")

    if a.jobs < 1 or a.timeout < 1:
        sys.exit("--jobs and --timeout must be at least 1")

    out = Path(a.output).resolve()
    check_output(out)
    settings = {
        "output": str(out), "percentages": a.percentages, "experiments": a.experiments,
        "variants": variants, "similarities": a.similarities,
        "score_thresholds": a.score_thresholds, "time_similarity": a.time_similarity,
        "time_score_threshold": a.time_score_threshold, "jobs": a.jobs, "timeout": a.timeout,
    }
    record = dict(settings)
    saved = out / "settings.json"
    old = None
    if saved.exists() and not a.force:
        try:
            old = json.loads(saved.read_text())
        except (OSError, ValueError):
            sys.exit(f"{saved} cannot be read: use --force to start again, "
                     "or another --output")
    analysis = set(steps) <= ANALYSIS_STEPS and not a.force

    if analysis:
        if old is None:
            sys.exit(f"{out} contains no results: run the experiment first")
    elif out.exists() and any(out.iterdir()):
        if a.force:
            shutil.rmtree(out)
            old = None
        elif not (a.resume or steps != list(STEPS)):
            sys.exit(f"{out} already contains results. Use --resume to continue it, "
                     "--force to start again, or another --output.")
    if old is not None:
        diff = []
        if not analysis and old.get("timeout") != a.timeout:
            diff.append("timeout")
        if analysis:
            diff += [k for k in GRID_KEYS + ["percentages"]
                     if not set(settings[k]) <= set(old.get(k, []))]
            if a.experiments > old["experiments"]:
                diff.append("experiments")
        if diff:
            sys.exit(f"{out} was produced with other values for: {', '.join(diff)}. "
                     "Use another --output or --force.")
        record["experiments"] = max(old["experiments"], a.experiments)
        for k in GRID_KEYS + ["percentages"]:
            record[k] = sorted(set(old.get(k, [])) | set(settings[k]))
    if not analysis:
        out.mkdir(parents=True, exist_ok=True)
        saved.write_text(json.dumps(record, indent=2))

    if old is not None and "generate" in steps and \
            (out / DATA_DIRNAME / "manifest.json").exists():
        steps.remove("generate")

    settings.update(retry_failed=a.retry_failed)
    env = dict(os.environ, MPLBACKEND="Agg", **{SETTINGS_VARIABLE: json.dumps(settings)})
    for step in steps:
        print(f"\n=== {step} ===", flush=True)
        if subprocess.run([sys.executable, str(ROOT / STEPS[step])], env=env,
                          cwd=ROOT).returncode:
            sys.exit(f"step '{step}' stopped")
    print(f"\nDone. Results in {out}")


if __name__ == "__main__":
    main()
