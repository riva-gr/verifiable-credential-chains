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
from config import DEFAULTS
from select_parameters import MAX_REPLICATES

STEPS = {"generate": "prepare_dataset.py", "run": "execute.py",
         "select": "select_parameters.py", "plot": "plot.py"}
ANALYSIS_STEPS = {"select", "plot"}
SETTINGS_VARIABLE = "NOISE_EXPERIMENT_SETTINGS"


DATASET_KEYS = ["seed", "chains", "min_length", "identities_per_chain", "misc_min",
                "misc_max", "percentages"]


GRID_KEYS = ["algorithms", "min_supports", "risups", "similarities", "score_thresholds"]


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
    g.add_argument("--retry-skipped", action="store_true",
                   help="with --resume: run the runs that earlier versions skipped")

    g = ap.add_argument_group("dataset")
    g.add_argument("--seed", type=int, default=d["seed"])
    g.add_argument("--experiments", type=int, default=d["experiments"],
                   help="replicate files per noise size (default 5)")
    g.add_argument("--noise-sizes", type=ints, default=d["noise_sizes"],
                   help="noise pool sizes (default 12,65,100,300,500,1000)")
    g.add_argument("--part1-noise-sizes", type=ints, default=d["part1_noise_sizes"],
                   help="noise pool sizes of the accuracy and F1 figures "
                        "(default 65,100,300,500,1000)")

    g = ap.add_argument_group("parameter search")
    g.add_argument("--algorithms", default=",".join(d["algorithms"]),
                   help="comma-separated subset of: cam, gspx, lpwe")
    g.add_argument("--min-supports", type=floats, default=d["min_supports"],
                   help="CAM and GSP-X (default 0.01,...,0.05)")
    g.add_argument("--risups", type=floats, default=d["risups"],
                   help="CAM and GSP-X, one decimal (default 0.1,...,1.0; the accuracy "
                        "and F1 figures use 0.5 and above)")
    g.add_argument("--similarities", type=floats, default=d["similarities"],
                   help="LPwE (default 0.1,...,0.9)")
    g.add_argument("--score-thresholds", type=floats, default=d["score_thresholds"],
                   help="LPwE, one decimal (default 0.1,...,0.9)")

    g = ap.add_argument_group("execution")
    g.add_argument("--jobs", type=int, default=d["jobs"],
                   help="runs executed at the same time (default 1)")
    g.add_argument("--timeout", type=int, default=d["timeout"],
                   help="seconds allowed per single algorithm run (default 120)")
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
    algorithms = [x.strip() for x in a.algorithms.split(",") if x.strip()]
    for s in steps:
        if s not in STEPS:
            sys.exit(f"unknown step '{s}'; choose from {', '.join(STEPS)}")
    for x in algorithms:
        if x not in ("cam", "gspx", "lpwe"):
            sys.exit(f"unknown algorithm '{x}'; choose from cam, gspx, lpwe")
    if not algorithms:
        sys.exit("--algorithms: no algorithms")
    if len(set(algorithms)) != len(algorithms):
        sys.exit("--algorithms: duplicate values")
    if a.jobs < 1 or a.timeout < 1:
        sys.exit("--jobs and --timeout must be at least 1")
    steps = [s for s in STEPS if s in steps]
    if not 1 <= a.experiments <= MAX_REPLICATES:
        sys.exit(f"--experiments must be from 1 to {MAX_REPLICATES}")
    for name, sizes in (("noise-sizes", a.noise_sizes),
                        ("part1-noise-sizes", a.part1_noise_sizes)):
        if len(set(sizes)) != len(sizes) or not all(n >= DEFAULTS["misc_max"] for n in sizes):
            sys.exit(f"--{name}: distinct integers of at least {DEFAULTS['misc_max']} "
                     "(the largest number of noise credentials per identity)")
    check_values("min-supports", a.min_supports)
    check_values("risups", a.risups, one_decimal=True)
    check_values("similarities", a.similarities)
    check_values("score-thresholds", a.score_thresholds, one_decimal=True)

    out = Path(a.output).resolve()
    check_output(out)
    settings = {
        "output": str(out), "seed": a.seed,
        "chains": DEFAULTS["chains"], "min_length": DEFAULTS["min_length"],
        "identities_per_chain": DEFAULTS["identities_per_chain"],
        "misc_min": DEFAULTS["misc_min"], "misc_max": DEFAULTS["misc_max"],
        "percentages": DEFAULTS["percentages"], "experiments": a.experiments,
        "noise_sizes": sorted(a.noise_sizes),
        "part1_noise_sizes": sorted(set(a.part1_noise_sizes)),
        "min_supports": a.min_supports, "risups": a.risups,
        "part1_min_risup": DEFAULTS["part1_min_risup"],
        "similarities": a.similarities, "score_thresholds": a.score_thresholds,
        "algorithms": algorithms, "jobs": a.jobs, "timeout": a.timeout,
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
        diff = [k for k in DATASET_KEYS if old.get(k) != settings[k]]
        if not set(a.noise_sizes) <= set(old["noise_sizes"]):
            diff.append("noise_sizes")
        if a.experiments > old["experiments"]:
            diff.append("experiments")
        if not analysis and old.get("timeout") != a.timeout:
            diff.append("timeout")
        if analysis:
            diff += [k for k in GRID_KEYS if not set(settings[k]) <= set(old.get(k, []))]
        if diff:
            sys.exit(f"{out} was produced with other values for: {', '.join(diff)}. "
                     "Use another --output or --force.")
        record.update(noise_sizes=old["noise_sizes"], experiments=old["experiments"],
                      part1_noise_sizes=old["part1_noise_sizes"])
        for k in GRID_KEYS:
            record[k] = sorted(set(old.get(k, [])) | set(settings[k]))
    if not analysis:
        out.mkdir(parents=True, exist_ok=True)
        saved.write_text(json.dumps(record, indent=2))

    settings.update(retry_failed=a.retry_failed, retry_skipped=a.retry_skipped)
    env = dict(os.environ, MPLBACKEND="Agg", **{SETTINGS_VARIABLE: json.dumps(settings)})
    for step in steps:
        print(f"\n=== {step} ===", flush=True)
        if subprocess.run([sys.executable, str(ROOT / STEPS[step])], env=env,
                          cwd=ROOT).returncode:
            sys.exit(f"step '{step}' stopped")
    print(f"\nDone. Results in {out}")


if __name__ == "__main__":
    main()
