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
from summarize import MAX_SEEDS

STEPS = {"generate": "prepare_dataset.py", "run": "execute.py",
         "summarize": "summarize.py", "plot": "plot.py"}
ANALYSIS_STEPS = {"summarize", "plot"}
SETTINGS_VARIABLE = "SCALABILITY_SETTINGS"


FIXED_KEYS = ["seeds", "min_support", "risup", "similarity", "score_threshold"]


def numbers(kind):
    def parse(text):
        return [kind(v) for v in text.split(",")]
    return parse


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

    g = ap.add_argument_group("datasets")
    g.add_argument("--sizes", type=numbers(int), default=d["sizes"],
                   help="identities per dataset (default 1000,2500,5000,10000,20000)")
    g.add_argument("--seeds", type=numbers(int), default=d["seeds"],
                   help="one dataset per seed and size (default 1729,2718,3141,5772,8119)")

    g = ap.add_argument_group("algorithms")
    g.add_argument("--algorithms", default=",".join(d["algorithms"]),
                   help="comma-separated subset of: gspx, cam, lpwe")
    g.add_argument("--min-support", type=float, default=d["min_support"],
                   help="GSP-X and CAM (default 0.02)")
    g.add_argument("--risup", type=float, default=d["risup"],
                   help="GSP-X and CAM (default 1.0)")
    g.add_argument("--similarity", type=float, default=d["similarity"],
                   help="LPwE (default 0.2)")
    g.add_argument("--score-threshold", type=float, default=d["score_threshold"],
                   help="LPwE (default 0.8)")

    g = ap.add_argument_group("execution")
    g.add_argument("--timeout", type=int, default=d["timeout"],
                   help="seconds allowed per algorithm run (default 7200)")
    return ap.parse_args()


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


def check(a, algorithms):
    for x in algorithms:
        if x not in ("gspx", "cam", "lpwe"):
            sys.exit(f"unknown algorithm '{x}'; choose from gspx, cam, lpwe")
    if not algorithms or len(set(algorithms)) != len(algorithms):
        sys.exit("--algorithms: one or more distinct values")
    for name in ("min_support", "risup", "similarity", "score_threshold"):
        v = getattr(a, name)
        if not (math.isfinite(v) and 0 < v <= 1):
            sys.exit(f"--{name.replace('_', '-')}: {v} is not in (0, 1]")
    if not a.sizes or len(set(a.sizes)) != len(a.sizes) or not all(n >= 1 for n in a.sizes):
        sys.exit("--sizes: distinct integers of at least 1")
    if not 1 <= len(a.seeds) <= MAX_SEEDS or len(set(a.seeds)) != len(a.seeds) or \
            not all(s >= 0 for s in a.seeds):
        sys.exit(f"--seeds: 1 to {MAX_SEEDS} distinct integers of at least 0")
    if a.timeout < 1:
        sys.exit("--timeout must be at least 1")


def main() -> None:
    a = parse_args()
    if not hasattr(os, "wait4"):
        sys.exit("peak memory is measured with os.wait4, which needs Linux or macOS")
    steps = [s.strip() for s in a.steps.split(",") if s.strip()]
    for s in steps:
        if s not in STEPS:
            sys.exit(f"unknown step '{s}'; choose from {', '.join(STEPS)}")
    steps = [s for s in STEPS if s in steps]
    algorithms = [x.strip() for x in a.algorithms.split(",") if x.strip()]
    check(a, algorithms)

    out = Path(a.output).resolve()
    check_output(out)
    settings = {"output": str(out), "sizes": sorted(a.sizes), "seeds": a.seeds,
                "algorithms": algorithms, "min_support": a.min_support, "risup": a.risup,
                "similarity": a.similarity, "score_threshold": a.score_threshold,
                "timeout": a.timeout}
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
        diff = [k for k in FIXED_KEYS if old.get(k) != settings[k]]
        if analysis:
            diff += [k for k in ("sizes", "algorithms")
                     if not set(settings[k]) <= set(old.get(k, []))]
        else:
            diff += [k for k in ("sizes", "timeout") if old.get(k) != settings[k]]
        if diff:
            sys.exit(f"{out} was produced with other values for: {', '.join(diff)}. "
                     "Use another --output or --force.")
        record["algorithms"] = [x for x in ("gspx", "cam", "lpwe")
                                if x in set(old["algorithms"]) | set(algorithms)]
    if not analysis:
        out.mkdir(parents=True, exist_ok=True)
        saved.write_text(json.dumps(record, indent=2))

    settings["retry_failed"] = a.retry_failed
    env = dict(os.environ, MPLBACKEND="Agg", **{SETTINGS_VARIABLE: json.dumps(settings)})
    for step in steps:
        print(f"\n=== {step} ===", flush=True)
        if subprocess.run([sys.executable, str(ROOT / STEPS[step])], env=env,
                          cwd=ROOT).returncode:
            sys.exit(f"step '{step}' stopped")
    print(f"\nDone. Results in {out}")


if __name__ == "__main__":
    main()
