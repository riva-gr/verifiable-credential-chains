from __future__ import annotations

import csv
import json
import shutil
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import algorithm_runs
import config
import prepare_dataset

JOB_DIR = config.JOB_DIR


def params() -> dict:
    return {"min_support": config.MIN_SUPPORT, "risup": config.RISUP,
            "similarity": config.SIMILARITY, "score_threshold": config.SCORE_THRESHOLD}


def job_list():
    return [{"algo": a, "p": p, "e": e, "seed": seed}
            for p in config.PERCENTAGES for e, seed in enumerate(config.SEEDS)
            for a in config.ALGORITHMS]


def job_key(job) -> str:
    return f"{job['algo']}__p{job['p']}__e{job['e']}__seed{job['seed']}"


def stored(job):
    path = JOB_DIR / f"{job_key(job)}.json"
    if not path.exists():
        return None
    rec = json.loads(path.read_text())
    if rec.get("params") != params() or any(rec.get(k) != v for k, v in job.items()):
        sys.exit(f"{path} was produced with other settings: use --force to start again, "
                 "or another --output")
    return rec


def forget_failed(jobs) -> int:
    n = 0
    for job in jobs:
        rec = stored(job)
        if rec is not None and rec["status"] != "ok":
            (JOB_DIR / f"{job_key(job)}.json").unlink()
            n += 1
    return n


def run_job(job) -> dict:
    key = job_key(job)
    out = JOB_DIR / f"{key}.json"
    if out.exists():
        return {"key": key, "status": "cached"}
    res = algorithm_runs.run(job["algo"], config.data_dir(job["p"]), job["p"], job["e"],
                             job["seed"], params(), key, config.WORK_DIR, config.TIMEOUT_S)
    rec = {"key": key, **job, "params": params(), **res}
    JOB_DIR.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    tmp.write_text(json.dumps(rec))
    tmp.replace(out)
    return rec


def main() -> None:
    prepare_dataset.verify_inputs()
    jobs = job_list()
    if config.SETTINGS.get("retry_failed"):
        n = forget_failed(jobs)
        if n:
            print(f"{n} stored runs will be executed again")
    todo = [j for j in jobs if stored(j) is None]
    print(f"{len(jobs)} runs in total, {len(jobs) - len(todo)} already done, "
          f"{len(todo)} to run ({config.JOBS} at a time)", flush=True)

    log_path = config.RUN_DIR / "summary" / "execution_log.csv"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    new_log = not log_path.exists()
    start = time.time()
    failed = 0
    with open(log_path, "a", newline="") as log, \
            ProcessPoolExecutor(max_workers=config.JOBS) as pool:
        w = csv.writer(log)
        if new_log:
            w.writerow(["algo", "p", "e", "seed", "status", "wall_s", "error"])
        futures = [pool.submit(run_job, j) for j in todo]
        for i, fut in enumerate(as_completed(futures), 1):
            r = fut.result()
            if r["status"] != "cached":
                w.writerow([r["algo"], r["p"], r["e"], r["seed"], r["status"], r["wall_s"],
                            r["error"]])
                log.flush()
                if r["status"] != "ok":
                    failed += 1
                    print(f"  not completed: {r['key']}: {r['status']}", flush=True)
            if i % 20 == 0 or i == len(futures):
                print(f"  {i}/{len(futures)} runs ({time.time() - start:.0f}s)", flush=True)

    shutil.rmtree(config.WORK_DIR, ignore_errors=True)
    print(f"done; {failed} new runs failed or timed out (see summary/execution_log.csv)")


if __name__ == "__main__":
    main()
