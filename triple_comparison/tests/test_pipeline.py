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
SETTINGS = {"output": str(TMP / "results"), "percentages": [50], "experiments": 3,
            "min_supports": [0.01, 0.02], "risups": [0.9, 1.0],
            "similarities": [0.1, 0.2], "score_thresholds": [0.5, 0.6],
            "algorithms": ["cam", "lpwe"]}
for variable in ("TRIPLE_COMPARISON_SETTINGS", "BPI_COMPARISON_SETTINGS"):
    os.environ[variable] = json.dumps(SETTINGS)
sys.path.insert(0, str(ROOT))

import algorithm_runs
import config
import execute
import run_experiment
import select_parameters as sp


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


def run(algo, e, f1, status="ok", time=1.0, **params):
    r = {"algorithm": algo, "percentage": 50, "replicate": e, **params, "status": status}
    if status == "ok":
        r.update(time=time, coverage=1.0, accuracy=f1, precision=f1, recall=f1, f1=f1)
    return r


def cam(e, s, r, f1, **kw):
    return run("cam", e, f1, min_support=s, risup=r, **kw)


def lpwe(e, s, t, f1, **kw):
    return run("lpwe", e, f1, similarity=s, score_threshold=t, **kw)


def chosen(selected, algo, e):
    return next(r for r in selected if r["algorithm"] == algo and r["replicate"] == e)


class SelectionTests(unittest.TestCase):
    def test_each_replicate_has_its_own_winner(self):
        runs = [cam(0, 0.01, 1.0, 0.9), cam(0, 0.02, 1.0, 0.8),
                cam(1, 0.01, 1.0, 0.7), cam(1, 0.02, 1.0, 0.95)]
        selected = sp.select(runs)
        self.assertEqual(chosen(selected, "cam", 0)["min_support"], 0.01)
        self.assertEqual(chosen(selected, "cam", 1)["min_support"], 0.02)
        self.assertEqual(chosen(selected, "cam", 1)["f1"], 0.95)

    def test_ties_go_to_the_largest_values_without_averaging(self):
        runs = [cam(0, 0.01, 1.0, 0.9, time=5.0), cam(0, 0.02, 0.9, 0.9, time=1.0),
                lpwe(0, 0.1, 0.6, 0.8, time=4.0), lpwe(0, 0.2, 0.5, 0.8, time=2.0),
                lpwe(0, 0.2, 0.6, 0.8, time=3.0)]
        selected = sp.select(runs)
        c, l = chosen(selected, "cam", 0), chosen(selected, "lpwe", 0)
        self.assertEqual((c["min_support"], c["risup"], c["time"]), (0.02, 0.9, 1.0))
        self.assertEqual((l["similarity"], l["score_threshold"], l["time"]), (0.2, 0.6, 3.0))
        self.assertEqual((c["tied_settings"], l["tied_settings"]), (2, 3))

    def test_a_failed_run_is_excluded_from_its_own_replicate_only(self):
        runs = [cam(0, 0.01, 1.0, 0.99), cam(1, 0.01, 1.0, 0, status="timeout>120s"),
                cam(2, 0.01, 1.0, 0.99)]
        runs += [cam(e, 0.02, 1.0, 0.5) for e in range(3)]
        selected = sp.select(runs)
        self.assertEqual([chosen(selected, "cam", e)["min_support"] for e in range(3)],
                         [0.01, 0.02, 0.01])
        self.assertEqual(chosen(selected, "cam", 1)["failed_settings"], 1)

    def test_zero_f1_is_a_valid_result(self):
        selected = sp.select([cam(0, 0.01, 1.0, 0.0), cam(0, 0.02, 1.0, 0.0)])
        self.assertEqual(chosen(selected, "cam", 0)["min_support"], 0.02)

    def test_a_replicate_without_completed_runs_stops_the_selection(self):
        runs = [cam(0, 0.01, 1.0, 0.9), cam(1, 0.01, 1.0, 0, status="exit code 1")]
        with self.assertRaises(SystemExit):
            sp.select(runs)

    def test_confidence_interval_uses_the_actual_n(self):
        self.assertEqual(sp.interval([0.5]), (0.5, None, None, None))
        mean, sd, low, high = sp.interval([0.90, 0.92, 0.94, 0.96, 0.98])
        self.assertAlmostEqual(mean, 0.94)
        self.assertAlmostEqual(sd, 0.0316227766, places=9)
        self.assertAlmostEqual(high - mean, 2.776445 * 0.0316227766 / 5 ** 0.5, places=9)
        mean, sd, low, high = sp.interval([0.0, 1.0])
        self.assertAlmostEqual(high - mean, 12.706205 * 2 ** -0.5 / 2 ** 0.5, places=9)


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
        rec = {"key": execute.job_key(job), "algo": job["algo"], "p": job["p"],
               "e": job["e"], "params": pr, "status": status, "rows": rows}
        (config.JOB_DIR / f"{execute.job_key(job)}.json").write_text(json.dumps(rec))

    def test_replicates_are_identified_by_their_records(self):
        jobs = execute.job_list()
        for job in reversed(jobs):
            self.write(job, f1=0.1 * (job["e"] + 1))
        runs, problems = sp.load_runs()
        self.assertEqual(problems, [])
        self.assertEqual(len(runs), 3 * (4 + 2 * 2))
        for r in runs:
            self.assertAlmostEqual(r["f1"], 0.1 * (r["replicate"] + 1))

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
        old = {**jobs[0], "params": {**jobs[0]["params"], "score_thresholds": [0.5]}}
        self.write(old)
        for job in jobs[1:]:
            self.write(job)
        todo = execute.plan(execute.job_list())
        self.assertEqual([execute.job_key(j) for j in todo if j["algo"] == "lpwe"],
                         [execute.job_key(jobs[0])])
        rerun = next(j for j in todo if j["algo"] == "lpwe")
        self.assertTrue(rerun["rerun"])
        self.assertEqual(rerun["params"]["score_thresholds"], [0.5, 0.6])

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
            "results*", "__pycache__", ".venv", "*.xes.gz", "data_rebuilt"))
        cls.first = list(run_experiment.STEPS)[0]

    def cli(self, *args):
        env = {k: v for k, v in os.environ.items() if not k.endswith("_SETTINGS")}
        r = subprocess.run([sys.executable, str(self.pkg / "run_experiment.py"), *map(str, args)],
                           cwd=self.pkg, env=env, capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr

    def test_force_never_deletes_the_package(self):
        for out in (self.pkg, self.pkg.parent, self.pkg / "algorithms"):
            code, text = self.cli("--force", "--steps", self.first, "--percentages", "50",
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
            code, text = self.cli("--force", "--steps", self.first, "--output", out)
            self.assertNotEqual(code, 0, out)
            self.assertIn("--output", text)
        for name, files in kept.items():
            self.assertEqual({p.name for p in (top / name).iterdir()}, files)

    def test_force_never_deletes_repository_or_environment_folders(self):
        small = ["--percentages", "50", "--experiments", "1"]
        for name in (".git", ".venv", "my_output"):
            (self.pkg / name).mkdir(exist_ok=True)
            (self.pkg / name / "keep").write_text("x")
            code, text = self.cli("--force", "--steps", self.first, *small,
                                  "--output", self.pkg / name)
            self.assertNotEqual(code, 0)
            self.assertIn("must be a folder whose name starts with 'results'", text)
            self.assertTrue((self.pkg / name / "keep").exists())
        code, text = self.cli("--force", "--steps", self.first, *small,
                              "--output", self.pkg / "results_test")
        self.assertEqual(code, 0, text)

    def test_force_restarts_when_the_settings_file_is_unreadable(self):
        out = TMP / "unreadable"
        out.mkdir()
        (out / "settings.json").write_text("{")
        small = ["--percentages", "50", "--experiments", "1", "--output", out]
        code, text = self.cli("--steps", "select", *small)
        self.assertNotEqual(code, 0)
        self.assertIn("cannot be read", text)
        code, text = self.cli("--force", "--steps", self.first, *small)
        self.assertEqual(code, 0, text)
        self.assertIsInstance(json.loads((out / "settings.json").read_text()), dict)

    def test_invalid_execution_options_are_rejected(self):
        out = TMP / "execution"
        for args, message in ((["--jobs", "0"], "at least 1"),
                              (["--timeout", "0"], "at least 1"),
                              (["--algorithms", ","], "distinct"),
                              (["--algorithms", "cam,cam"], "distinct")):
            code, text = self.cli(*args, "--steps", "select", "--output", out)
            self.assertNotEqual(code, 0)
            self.assertIn(message, text)
        self.assertFalse(out.exists())

    def test_grid_values_that_would_share_a_results_file_are_rejected(self):
        out = TMP / "grid"
        for option, values, message in (("--risups", "0.55,0.56", "more than one decimal"),
                                        ("--score-thresholds", "0.5,0.50000000001",
                                         "more than one decimal"),
                                        ("--score-thresholds", "0.5,0.5", "duplicate"),
                                        ("--similarities", "nan", "not in (0, 1]"),
                                        ("--experiments", "32", "from 1 to 31")):
            code, text = self.cli(option, values, "--steps", "select", "--output", out)
            self.assertNotEqual(code, 0)
            self.assertIn(message, text)
        self.assertFalse(out.exists())

    def test_changed_inputs_stop_resume_and_selection(self):
        out = TMP / "inputs"
        small = ["--percentages", "50", "--experiments", "1", "--algorithms", "cam",
                 "--min-supports", "0.05", "--risups", "1.0", "--output", out]
        code, text = self.cli("--steps", self.first, *small)
        self.assertEqual(code, 0, text)
        code, text = self.cli("--steps", "select", *small)
        self.assertNotEqual(code, 0)
        self.assertIn("incomplete", text)
        self.assertNotIn("checksum", text)
        with open(out / "GT_and_CSV_files" / "crs50_(0).csv", "a") as fh:
            fh.write("changed\n")
        for steps in (["--resume", "--steps", "run"], ["--steps", "select"]):
            code, text = self.cli(*steps, *small)
            self.assertNotEqual(code, 0)
            self.assertIn("checksum", text)


if __name__ == "__main__":
    unittest.main()
