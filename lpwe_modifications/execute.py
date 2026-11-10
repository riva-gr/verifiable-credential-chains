from __future__ import annotations

import csv
import json
import shutil
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import algorithm_runs
import config
import prepare_dataset

JOB_DIR = config.JOB_DIR


def job_list():
    return [{"variant": v, "p": p, "e": e,
             "params": {"similarity": s, "score_thresholds": config.SCORE_THRESHOLDS}}
            for v in config.ALGORITHMS for s in config.SIMILARITIES
            for e in config.EXPERIMENTS for p in config.PERCENTAGES]


def job_key(job) -> str:
    return f"main__{job['variant']}__sim{job['params']['similarity']}__p{job['p']}__e{job['e']}"


def plan(jobs) -> list:
    todo = []
    for job in jobs:
        f = JOB_DIR / f"{job_key(job)}.json"
        if not f.exists():
            todo.append(job)
            continue
        rec = json.loads(f.read_text())
        wanted = job["params"]["score_thresholds"]
        if rec["status"] == "ok" and any(algorithm_runs.threshold_key(t) not in rec["rows"]
                                         for t in wanted):
            union = sorted(set(rec["params"]["score_thresholds"]) | set(wanted))
            todo.append({**job, "params": {**job["params"], "score_thresholds": union},
                         "rerun": True})
    return todo


def forget_failed(jobs) -> int:
    n = 0
    for job in jobs:
        f = JOB_DIR / f"{job_key(job)}.json"
        if f.exists() and json.loads(f.read_text())["status"] != "ok":
            f.unlink()
            n += 1
    return n


def run_job(job) -> dict:
    key = job_key(job)
    out = JOB_DIR / f"{key}.json"
    if out.exists() and not job.get("rerun"):
        return {"key": key, "status": "cached"}
    res = algorithm_runs.run(job["variant"], job["p"], job["e"], job["params"], key)
    rec = {"key": key, "variant": job["variant"], "p": job["p"], "e": job["e"],
           "params": job["params"], **res}
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
    todo = plan(jobs)
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
            w.writerow(["variant", "params", "p", "e", "status", "wall_s", "error"])
        futures = [pool.submit(run_job, j) for j in todo]
        for i, fut in enumerate(as_completed(futures), 1):
            r = fut.result()
            if r["status"] != "cached":
                w.writerow([r["variant"], json.dumps(r["params"]), r["p"], r["e"],
                            r["status"], r["wall_s"], r["error"]])
                log.flush()
                if r["status"] != "ok":
                    failed += 1
                    print(f"  not completed: {r['key']}: {r['status']}", flush=True)
            if i % 100 == 0 or i == len(futures):
                print(f"  {i}/{len(futures)} runs ({time.time() - start:.0f}s)", flush=True)

    shutil.rmtree(config.WORK_DIR, ignore_errors=True)
    print(f"done; {failed} new runs failed or timed out (see summary/execution_log.csv)")


if __name__ == "__main__":
    main()
