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
            "variants": ["prediction", "agnostic"], "similarities": [0.1, 0.2],
            "score_thresholds": [0.5, 0.8], "time_similarity": 0.2,
            "time_score_threshold": 0.8}
os.environ["LPWE_MODS_SETTINGS"] = json.dumps(SETTINGS)
sys.path.insert(0, str(ROOT))

import algorithm_runs
import config
import execute
import run_experiment
import select_parameters as sp


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


def run(variant, e, s, t, f1, status="ok", time=1.0):
    x = {"variant": variant, "percentage": 50, "replicate": e, "similarity": s,
         "score_threshold": t, "status": status}
    if status == "ok":
        x.update(time=time, coverage=1.0, accuracy=f1, precision=f1, recall=f1, f1=f1)
    return x


def chosen(selected, variant, e):
    return next(r for r in selected if r["variant"] == variant and r["replicate"] == e)


class SelectionTests(unittest.TestCase):
    def test_each_replicate_has_its_own_winner(self):
        runs = [run("agnostic", 0, 0.1, 0.5, 0.9), run("agnostic", 0, 0.2, 0.5, 0.8),
                run("agnostic", 1, 0.1, 0.5, 0.7), run("agnostic", 1, 0.2, 0.5, 0.95)]
        selected = sp.select(runs)
        self.assertEqual(chosen(selected, "agnostic", 0)["similarity"], 0.1)
        self.assertEqual(chosen(selected, "agnostic", 1)["similarity"], 0.2)

    def test_ties_go_to_the_largest_values_without_averaging(self):
        runs = [run("agnostic", 0, 0.1, 0.8, 0.9, time=5.0), run("agnostic", 0, 0.2, 0.5, 0.9, time=1.0),
                run("agnostic", 0, 0.2, 0.8, 0.9, time=2.0)]
        c = chosen(sp.select(runs), "agnostic", 0)
        self.assertEqual((c["similarity"], c["score_threshold"], c["time"], c["tied_settings"]),
                         (0.2, 0.8, 2.0, 3))

    def test_a_failed_run_is_excluded_from_its_own_replicate_only(self):
        runs = [run("agnostic", 0, 0.1, 0.5, 0.99), run("agnostic", 1, 0.1, 0.5, 0, status="timeout>300s"),
                run("agnostic", 2, 0.1, 0.5, 0.99)] + [run("agnostic", e, 0.2, 0.5, 0.5) for e in range(3)]
        selected = sp.select(runs)
        self.assertEqual([chosen(selected, "agnostic", e)["similarity"] for e in range(3)],
                         [0.1, 0.2, 0.1])
        self.assertEqual(chosen(selected, "agnostic", 1)["failed_settings"], 1)

    def test_a_replicate_without_completed_runs_stops_the_selection(self):
        with self.assertRaises(SystemExit):
            sp.select([run("agnostic", 0, 0.1, 0.5, 0.9),
                       run("agnostic", 1, 0.1, 0.5, 0, status="exit code 1")])

    def test_processing_time_uses_the_completed_runs_at_the_fixed_setting(self):
        runs = [run("agnostic", e, 0.2, 0.8, 0.5, time=float(e + 1)) for e in range(3)]
        runs += [run("agnostic", 0, 0.2, 0.5, 0.9, time=9.0),
                 run("prediction", 0, 0.2, 0.8, 0, status="timeout>300s"),
                 run("prediction", 1, 0.2, 0.8, 0.5, time=2.0),
                 run("prediction", 2, 0.2, 0.8, 0.5, time=4.0)]
        rows = {r["variant"]: r for r in sp.summarize(sp.fixed_setting_runs(runs), ["time"])}
        self.assertEqual((rows["agnostic"]["n"], rows["agnostic"]["time_mean"]), (3, 2.0))
        self.assertEqual((rows["prediction"]["n"], rows["prediction"]["time_mean"]), (2, 3.0))

    def test_confidence_interval_uses_the_actual_n(self):
        self.assertEqual(sp.interval([0.5]), (0.5, None, None, None))
        mean, sd, low, high = sp.interval([0.90, 0.92, 0.94, 0.96, 0.98])
        self.assertAlmostEqual(sd, 0.0316227766, places=9)
        self.assertAlmostEqual(high - mean, 2.776445 * 0.0316227766 / 5 ** 0.5, places=9)
        mean, sd, low, high = sp.interval([1.0, 2.0, 3.0, 4.0])
        self.assertAlmostEqual(high - mean, 3.182446 * sd / 2, places=9)


class StoredRunsTests(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(config.JOB_DIR, ignore_errors=True)
        config.JOB_DIR.mkdir(parents=True)

    def write(self, job, status="ok", f1=0.5):
        rows = {algorithm_runs.threshold_key(t):
                f"{job['p']}  1.000 1.0000 {f1:.4f} {f1:.4f}  {f1:.4f}  {f1:.4f}"
                for t in job["params"]["score_thresholds"]} if status == "ok" else {}
        rec = {"key": execute.job_key(job), "variant": job["variant"], "p": job["p"],
               "e": job["e"], "params": job["params"], "status": status, "rows": rows}
        (config.JOB_DIR / f"{execute.job_key(job)}.json").write_text(json.dumps(rec))

    def test_replicates_are_identified_by_their_records(self):
        for job in reversed(execute.job_list()):
            self.write(job, f1=0.1 * (job["e"] + 1))
        runs, problems = sp.load_runs()
        self.assertEqual(problems, [])
        self.assertEqual(len(runs), 2 * 2 * 2 * 3)
        for r in runs:
            self.assertAlmostEqual(r["f1"], 0.1 * (r["replicate"] + 1))

    def test_missing_runs_are_reported(self):
        jobs = execute.job_list()
        for job in jobs[1:]:
            self.write(job)
        runs, problems = sp.load_runs()
        self.assertEqual(problems, [f"{execute.job_key(jobs[0])}: not run"])

    def test_a_run_lacking_a_requested_score_is_run_again(self):
        jobs = execute.job_list()
        self.write({**jobs[0], "params": {**jobs[0]["params"], "score_thresholds": [0.5]}})
        for job in jobs[1:]:
            self.write(job)
        todo = execute.plan(jobs)
        self.assertEqual([execute.job_key(j) for j in todo], [execute.job_key(jobs[0])])
        self.assertTrue(todo[0]["rerun"])
        self.assertEqual(todo[0]["params"]["score_thresholds"], [0.5, 0.8])

    def test_a_failure_does_not_skip_the_other_replicates(self):
        jobs = execute.job_list()
        self.write(jobs[0], status="timeout>300s")
        stub = {"status": "ok", "wall_s": 0.1, "error": "", "rows": {}}
        with mock.patch.object(algorithm_runs, "run", return_value=stub) as runner:
            rec = execute.run_job(jobs[1])
        runner.assert_called_once()
        self.assertEqual(rec["status"], "ok")

    def test_retry_failed_forgets_only_failed_runs(self):
        jobs = execute.job_list()[:2]
        self.write(jobs[0])
        self.write(jobs[1], status="timeout>300s")
        self.assertEqual(execute.forget_failed(jobs), 1)
        left = [(config.JOB_DIR / f"{execute.job_key(j)}.json").exists() for j in jobs]
        self.assertEqual(left, [True, False])


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
            code, text = self.cli("--force", "--steps", "generate", "--output", out)
            self.assertNotEqual(code, 0)
            self.assertIn("package folder", text)
        self.assertTrue((self.pkg / "run_experiment.py").exists())
        self.assertTrue((self.pkg / "algorithms" / "lpwe.py").exists())

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
        small = ["--percentages", "50", "--experiments", "1"]
        for name in (".git", ".venv", "my_output"):
            (self.pkg / name).mkdir(exist_ok=True)
            (self.pkg / name / "keep").write_text("x")
            code, text = self.cli("--force", "--steps", "generate", *small,
                                  "--output", self.pkg / name)
            self.assertNotEqual(code, 0)
            self.assertIn("must be a folder whose name starts with 'results'", text)
            self.assertTrue((self.pkg / name / "keep").exists())
        code, text = self.cli("--force", "--steps", "generate", *small,
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
        code, text = self.cli("--force", "--steps", "generate", *small)
        self.assertEqual(code, 0, text)
        self.assertIsInstance(json.loads((out / "settings.json").read_text()), dict)

    def test_invalid_execution_options_are_rejected(self):
        out = TMP / "execution"
        for args, message in ((["--jobs", "0"], "at least 1"),
                              (["--timeout", "0"], "at least 1"),
                              (["--variants", ","], "distinct"),
                              (["--variants", "agnostic,agnostic"], "distinct")):
            code, text = self.cli(*args, "--steps", "select", "--output", out)
            self.assertNotEqual(code, 0)
            self.assertIn(message, text)
        self.assertFalse(out.exists())

    def test_invalid_grids_are_rejected(self):
        out = TMP / "grid"
        for args, message in ((["--similarities", "0.2,0.2"], "duplicate"),
                              (["--similarities", "nan"], "not in (0, 1]"),
                              (["--score-thresholds", "0.5,0.50000000001"], "more than one decimal"),
                              (["--time-similarity", "0.25"], "must be in the grids"),
                              (["--experiments", "6"], "from 1 to 5"),
                              (["--percentages", "15"], "distinct values from 10")):
            code, text = self.cli(*args, "--steps", "select", "--output", out)
            self.assertNotEqual(code, 0)
            self.assertIn(message, text)
        self.assertFalse(out.exists())

    def test_changed_inputs_stop_resume_and_selection(self):
        out = TMP / "inputs"
        small = ["--percentages", "50", "--experiments", "1", "--variants", "agnostic",
                 "--similarities", "0.2", "--score-thresholds", "0.8", "--output", out]
        code, text = self.cli("--steps", "generate", *small)
        self.assertEqual(code, 0, text)
        code, text = self.cli("--steps", "select", *small)
        self.assertNotEqual(code, 0)
        self.assertIn("incomplete", text)
        self.assertNotIn("checksum", text)
        with open(out / config.DATA_DIRNAME / "crs50_(0).csv", "a") as fh:
            fh.write("changed\n")
        for steps in (["--resume", "--steps", "run"], ["--steps", "select"]):
            code, text = self.cli(*steps, *small)
            self.assertNotEqual(code, 0)
            self.assertIn("checksum", text)


if __name__ == "__main__":
    unittest.main()
