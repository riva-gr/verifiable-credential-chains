import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TMP = Path(tempfile.mkdtemp(prefix="pipeline_tests_"))
SETTINGS = {"output": str(TMP / "results"), "experiments": 3,
            "noise_sizes": [100, 300], "part1_noise_sizes": [300],
            "min_supports": [0.01, 0.02], "risups": [0.4, 0.9, 1.0],
            "similarities": [0.1, 0.2], "score_thresholds": [0.5, 0.6],
            "algorithms": ["cam", "lpwe"]}
os.environ["NOISE_EXPERIMENT_SETTINGS"] = json.dumps(SETTINGS)
sys.path.insert(0, str(ROOT))

import algorithm_runs
import config
import execute
import run_experiment
import select_parameters as sp


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


def run(algo, e, f1, status="ok", noise=300, acc=None, **params):
    r = {"noise_size": noise, "algorithm": algo, "percentage": 70, "replicate": e,
         **params, "status": status}
    if status == "ok":
        r.update(time=1.0, coverage=1.0, accuracy=f1 if acc is None else acc,
                 precision=f1, recall=f1, f1=f1)
    return r


def cam(e, s, r, f1, **kw):
    return run("cam", e, f1, min_support=s, risup=r, **kw)


def lpwe(e, s, t, f1, **kw):
    return run("lpwe", e, f1, similarity=s, score_threshold=t, **kw)


def chosen(selected, algo, e):
    return next(r for r in selected if r["algorithm"] == algo and r["replicate"] == e)


def row(rows, algo, noise, t):
    return next(r for r in rows if (r["algorithm"], r["noise_size"], r["threshold"]) ==
                (algo, noise, t))


class SelectionTests(unittest.TestCase):
    def test_each_replicate_has_its_own_winner(self):
        runs = [cam(0, 0.01, 1.0, 0.9), cam(0, 0.02, 1.0, 0.8),
                cam(1, 0.01, 1.0, 0.7), cam(1, 0.02, 1.0, 0.95)]
        selected = sp.select(runs)
        self.assertEqual(chosen(selected, "cam", 0)["min_support"], 0.01)
        self.assertEqual(chosen(selected, "cam", 1)["min_support"], 0.02)

    def test_ties_go_to_the_largest_values_without_averaging(self):
        runs = [cam(0, 0.01, 1.0, 0.9), cam(0, 0.02, 0.9, 0.9),
                lpwe(0, 0.1, 0.6, 0.8), lpwe(0, 0.2, 0.5, 0.8), lpwe(0, 0.2, 0.6, 0.8)]
        selected = sp.select(runs)
        c, l = chosen(selected, "cam", 0), chosen(selected, "lpwe", 0)
        self.assertEqual((c["min_support"], c["risup"]), (0.02, 0.9))
        self.assertEqual((l["similarity"], l["score_threshold"]), (0.2, 0.6))
        self.assertEqual((c["tied_settings"], l["tied_settings"]), (2, 3))

    def test_a_failed_run_is_excluded_from_its_own_replicate_only(self):
        runs = [cam(0, 0.01, 1.0, 0.99), cam(1, 0.01, 1.0, 0, status="timeout>120s"),
                cam(2, 0.01, 1.0, 0.99)] + [cam(e, 0.02, 1.0, 0.5) for e in range(3)]
        selected = sp.select(runs)
        self.assertEqual([chosen(selected, "cam", e)["min_support"] for e in range(3)],
                         [0.01, 0.02, 0.01])
        self.assertEqual(chosen(selected, "cam", 1)["failed_settings"], 1)

    def test_a_replicate_without_completed_runs_stops_the_selection(self):
        with self.assertRaises(SystemExit):
            sp.select([cam(0, 0.01, 1.0, 0.9), cam(1, 0.01, 1.0, 0, status="exit code 1")])

    def test_part1_uses_the_triple_comparison_grid(self):
        runs = [cam(0, 0.01, 0.4, 0.99), cam(0, 0.01, 1.0, 0.5),
                cam(0, 0.01, 1.0, 0.99, noise=100)]
        selected = sp.select(sp.part1_candidates(runs))
        self.assertEqual(len(selected), 1)
        self.assertEqual((selected[0]["risup"], selected[0]["f1"]), (1.0, 0.5))

    def test_confidence_interval_uses_the_actual_n(self):
        self.assertEqual(sp.interval([0.5]), (0.5, None, None, None))
        mean, sd, low, high = sp.interval([0.90, 0.92, 0.94, 0.96, 0.98])
        self.assertAlmostEqual(sd, 0.0316227766, places=9)
        self.assertAlmostEqual(high - mean, 2.776445 * 0.0316227766 / 5 ** 0.5, places=9)


class ThresholdTests(unittest.TestCase):
    def test_ties_within_a_threshold_go_to_the_largest_value(self):
        runs = [cam(e, s, 0.9, 0.8, acc=a) for e in range(3)
                for s, a in ((0.01, 0.2), (0.02, 0.6))]
        r = row(sp.thresholds(runs), "cam", 300, 0.9)
        self.assertEqual((r["n"], r["accuracy_mean"]), (3, 0.6))
        self.assertIn("min_support=0.02", r["selected_per_replicate"])

    def test_failed_replicates_reduce_n_and_none_completed_gives_zero(self):
        runs = [cam(0, 0.01, 0.4, 0.5, acc=0.4), cam(1, 0.01, 0.4, 0, status="timeout>120s"),
                cam(2, 0.01, 0.4, 0.7, acc=0.8)]
        runs += [cam(e, 0.01, 1.0, 0, status="timeout>120s") for e in range(3)]
        rows = sp.thresholds(runs)
        r = row(rows, "cam", 300, 0.4)
        self.assertEqual((r["n"], r["failed_runs"]), (2, 1))
        self.assertAlmostEqual(r["accuracy_mean"], 0.6)
        r = row(rows, "cam", 300, 1.0)
        self.assertEqual((r["n"], r["accuracy_mean"]), (0, None))


class StoredRunsTests(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(config.JOB_DIR, ignore_errors=True)
        config.JOB_DIR.mkdir(parents=True)

    def write(self, job, status="ok", f1=0.5):
        pr = job["params"]
        rels = ([algorithm_runs.lpwe_relpath(pr["similarity"], t) for t in pr["score_thresholds"]]
                if job["algo"] == "lpwe"
                else [algorithm_runs.chain_relpath(job["algo"], pr["min_support"], pr["risup"])])
        rows = ({rel: f"\n{job['p']}  1.000 1.0000 {f1:.4f} {f1:.4f}  {f1:.4f}  {f1:.4f}  "
                 for rel in rels} if status == "ok" else {})
        rec = {"key": execute.job_key(job), "noise": job["noise"], "algo": job["algo"],
               "p": job["p"], "e": job["e"], "params": pr, "status": status, "rows": rows}
        (config.JOB_DIR / f"{execute.job_key(job)}.json").write_text(json.dumps(rec))

    def test_records_are_identified_by_noise_size_and_replicate(self):
        for job in reversed(execute.job_list()):
            self.write(job, f1=0.1 * (job["e"] + 1) + job["noise"] / 1000)
        runs, problems = sp.load_runs()
        self.assertEqual(problems, [])
        self.assertEqual(len(runs), 2 * 3 * (6 + 4))
        for r in runs:
            self.assertAlmostEqual(r["f1"], 0.1 * (r["replicate"] + 1) + r["noise_size"] / 1000)

    def test_missing_and_skipped_runs_are_reported(self):
        jobs = execute.job_list()
        for job in jobs[2:]:
            self.write(job)
        self.write(jobs[1], status="skipped (another experiment of this block did not complete)")
        runs, problems = sp.load_runs()
        self.assertEqual(problems, [f"{execute.job_key(jobs[0])}: not run",
                                    f"{execute.job_key(jobs[1])}: skipped"])

    def test_a_failure_does_not_skip_the_other_replicates(self):
        jobs = [j for j in execute.job_list() if j["algo"] == "cam"]
        self.write(jobs[0], status="timeout>120s")
        stub = {"status": "ok", "wall_s": 0.1, "error": "", "rows": {}}
        with mock.patch.object(algorithm_runs, "run", return_value=stub) as runner:
            rec = execute.run_job(jobs[1])
        runner.assert_called_once()
        self.assertEqual(rec["status"], "ok")

    def test_an_lpwe_run_lacking_a_requested_score_is_run_again(self):
        jobs = [j for j in execute.job_list() if j["algo"] == "lpwe"]
        self.write({**jobs[0], "params": {**jobs[0]["params"], "score_thresholds": [0.5]}})
        for job in jobs[1:]:
            self.write(job)
        todo = [j for j in execute.plan(execute.job_list()) if j["algo"] == "lpwe"]
        self.assertEqual([execute.job_key(j) for j in todo], [execute.job_key(jobs[0])])
        self.assertTrue(todo[0]["rerun"])
        self.assertEqual(todo[0]["params"]["score_thresholds"], [0.5, 0.6])

    def test_retry_options_forget_only_their_runs(self):
        jobs = execute.job_list()[:3]
        for job, status in zip(jobs, ["ok", "timeout>120s", "skipped (earlier version)"]):
            self.write(job, status=status)
        self.assertEqual(execute.forget(jobs, failed=False, skipped=True), 1)
        self.assertEqual(execute.forget(jobs, failed=True, skipped=False), 1)
        left = [(config.JOB_DIR / f"{execute.job_key(j)}.json").exists() for j in jobs]
        self.assertEqual(left, [True, False, False])


class CommandLineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pkg = TMP / "package"
        shutil.copytree(ROOT, cls.pkg, ignore=shutil.ignore_patterns(
            "results*", "__pycache__", ".venv"))

    def cli(self, *args):
        env = {k: v for k, v in os.environ.items() if not k.endswith("_SETTINGS")}
        r = subprocess.run([sys.executable, str(self.pkg / "run_experiment.py"), *map(str, args)],
                           cwd=self.pkg, env=env, capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr

    def test_force_never_deletes_the_package(self):
        for out in (self.pkg, self.pkg.parent, self.pkg / "algorithms"):
            code, text = self.cli("--force", "--steps", "generate", "--noise-sizes", "100",
                                  "--experiments", "1", "--output", out)
            self.assertNotEqual(code, 0)
            self.assertIn("package folder", text)
        self.assertTrue((self.pkg / "run_experiment.py").exists())
        self.assertTrue((self.pkg / "algorithms" / "cam.py").exists())

    def test_force_never_touches_the_repository_or_another_experiment(self):
        top = self.pkg.parent
        kept = {".git": {"keep"}, ".venv": {"keep"},
                "other_experiment": {"keep", "run_experiment.py"}}
        for name, files in kept.items():
            (top / name).mkdir(exist_ok=True)
            for f in files:
                (top / name / f).write_text("x")
        for out in (top / ".git", top / ".git" / "objects", top / ".venv",
                    top / "other_experiment", top / "other_experiment" / "algorithms"):
            code, text = self.cli("--force", "--steps", "generate", "--output", out)
            self.assertNotEqual(code, 0, out)
            self.assertIn("--output", text)
        for name, files in kept.items():
            self.assertEqual({p.name for p in (top / name).iterdir()}, files)

    def test_force_never_deletes_repository_or_environment_folders(self):
        small = ["--steps", "generate", "--noise-sizes", "100", "--experiments", "1"]
        for name in (".git", ".venv", "my_output"):
            (self.pkg / name).mkdir(exist_ok=True)
            (self.pkg / name / "keep").write_text("x")
            code, text = self.cli("--force", *small, "--output", self.pkg / name)
            self.assertNotEqual(code, 0)
            self.assertIn("must be a folder whose name starts with 'results'", text)
            self.assertTrue((self.pkg / name / "keep").exists())
        code, text = self.cli("--force", *small, "--output", self.pkg / "results_test")
        self.assertEqual(code, 0, text)

    def test_force_restarts_when_the_settings_file_is_unreadable(self):
        out = TMP / "unreadable"
        out.mkdir()
        (out / "settings.json").write_text("{")
        small = ["--noise-sizes", "100", "--experiments", "1", "--output", out]
        code, text = self.cli("--steps", "select", *small)
        self.assertNotEqual(code, 0)
        self.assertIn("cannot be read", text)
        code, text = self.cli("--force", "--steps", "generate", *small)
        self.assertEqual(code, 0, text)
        self.assertTrue((out / "noise_100" / "GT_and_CSV_files" / "manifest.json").exists())

    def test_invalid_values_are_rejected(self):
        out = TMP / "grid"
        for option, values, message in (("--risups", "0.55,0.56", "more than one decimal"),
                                        ("--score-thresholds", "0.5,0.5", "duplicate"),
                                        ("--similarities", "nan", "not in (0, 1]"),
                                        ("--noise-sizes", "10,100", "at least 11"),
                                        ("--part1-noise-sizes", "100,100", "distinct"),
                                        ("--experiments", "32", "from 1 to 31"),
                                        ("--jobs", "0", "at least 1"),
                                        ("--timeout", "-1", "at least 1"),
                                        ("--algorithms", ",", "no algorithms"),
                                        ("--algorithms", "cam,cam", "duplicate")):
            code, text = self.cli(option, values, "--steps", "select", "--output", out)
            self.assertNotEqual(code, 0)
            self.assertIn(message, text)
        self.assertFalse(out.exists())

    def test_changed_inputs_stop_resume_and_selection(self):
        out = TMP / "inputs"
        small = ["--noise-sizes", "100,300", "--experiments", "1", "--algorithms", "cam",
                 "--min-supports", "0.05", "--risups", "1.0", "--output", out]
        code, text = self.cli("--steps", "generate", *small)
        self.assertEqual(code, 0, text)
        code, text = self.cli("--steps", "select", *small)
        self.assertNotEqual(code, 0)
        self.assertIn("incomplete", text)
        self.assertNotIn("checksum", text)
        with open(out / "noise_300" / "GT_and_CSV_files" / "crs70_(0).csv", "a") as fh:
            fh.write("changed\n")
        for steps in (["--resume", "--steps", "run"], ["--steps", "select"]):
            code, text = self.cli(*steps, *small)
            self.assertNotEqual(code, 0)
            self.assertIn("checksum", text)


if __name__ == "__main__":
    unittest.main()
