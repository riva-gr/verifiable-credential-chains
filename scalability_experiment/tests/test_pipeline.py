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
SETTINGS = {"output": str(TMP / "results"), "sizes": [1000, 2000], "seeds": [11, 22, 33],
            "algorithms": ["cam", "lpwe"]}
os.environ["SCALABILITY_SETTINGS"] = json.dumps(SETTINGS)
sys.path.insert(0, str(ROOT))

import algorithm_runs
import config
import execute
import summarize as sm

PARAMS = {"min_support": 0.02, "risup": 1.0, "similarity": 0.2, "score_threshold": 0.8}


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


def run(algo, n, e, time_s, memory=10.0, status="ok"):
    x = {"algorithm": config.LABELS[algo], "identities": n, "experiment": e,
         "seed": SETTINGS["seeds"][e], "status": status, "peak_memory_mib": memory}
    if status == "ok":
        x.update(time_s=time_s, coverage=1.0, accuracy=0.9, precision=1.0, recall=0.9,
                 f1=0.95)
    return x


def point(rows, algo, n):
    return next(r for r in rows if (r["algorithm"], r["identities"]) ==
                (config.LABELS[algo], n))


class MeasurementTests(unittest.TestCase):
    def setUp(self):
        self.algorithms = TMP / "stand_in_algorithms"
        self.algorithms.mkdir(exist_ok=True)
        self.data = TMP / "stand_in_data.csv"
        self.data.write_text("A1,A2\n")

    def script(self, name, body):
        (self.algorithms / f"{name}.py").write_text(body)

    def run_algo(self, algo, timeout=60):
        with mock.patch.object(config, "ALGORITHM_DIR", self.algorithms):
            return algorithm_runs.run(algo, self.data, self.data, 0, PARAMS, f"{algo}_test",
                                      TMP / "work", timeout)

    def test_time_and_metrics_come_from_the_results_file(self):
        self.script("cam", "import os\n"
                    "os.makedirs('cam_results/min_support_0.02', exist_ok=True)\n"
                    "open('cam_results/min_support_0.02/CAM_risup_1.0.txt', 'a').write("
                    "'\\n80  0.379  1.0000 0.9500 1.0000  0.9500  0.9744  ')\n"
                    "block = bytearray(50 * 1024 * 1024)\n")
        r = self.run_algo("cam")
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["metrics"], {"time_s": 0.379, "coverage": 1.0, "accuracy": 0.95,
                                        "precision": 1.0, "recall": 0.95, "f1": 0.9744})
        self.assertGreater(r["peak_memory_mib"], 50)

    def test_lpwe_time_and_metrics_come_from_its_printed_block(self):
        self.script("lpwe", "print('Metrics: \\n Score threshold: 0.8\\n Running time: 40.887\\n"
                    " Coverage: 0.9938\\n Accuracy: 0.9590\\n Precision: 0.9896\\n"
                    " Recall: 0.9688\\n F1 score: 0.9791')\n")
        r = self.run_algo("lpwe")
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["metrics"]["time_s"], 40.887)
        self.assertEqual(r["metrics"]["f1"], 0.9791)

    def test_failures_and_timeouts_are_recorded(self):
        self.script("cam", "raise SystemExit('stopped')\n")
        self.assertEqual(self.run_algo("cam")["status"], "exit code 1")
        self.script("cam", "import time\ntime.sleep(30)\n")
        self.assertEqual(self.run_algo("cam", timeout=1)["status"], "timeout>1s")
        self.script("cam", "print('no results file')\n")
        self.assertEqual(self.run_algo("cam")["status"], "no results")


class SummaryTests(unittest.TestCase):
    def test_means_per_algorithm_and_size(self):
        runs = [run(a, n, e, n / 1000 * (e + 1), memory=n / 100)
                for a in ("cam", "lpwe") for n in (1000, 2000) for e in range(3)]
        rows = sm.summarize(runs)
        self.assertEqual(len(rows), 4)
        r = point(rows, "lpwe", 2000)
        self.assertEqual((r["completed_runs"], r["failed_runs"]), (3, 0))
        self.assertAlmostEqual(r["mean_time_s"], 4.0)
        self.assertAlmostEqual(r["mean_peak_memory_mib"], 20.0)
        self.assertAlmostEqual(r["peak_memory_mib_ci95"], 0.0)

    def test_failed_runs_are_left_out_of_their_point_only(self):
        runs = [run("cam", 1000, 0, 1.0), run("cam", 1000, 1, 0, status="timeout>7200s"),
                run("cam", 1000, 2, 3.0)] + [run("cam", 2000, e, 0, status="exit code 1")
                                             for e in range(3)]
        rows = sm.summarize(runs)
        r = point(rows, "cam", 1000)
        self.assertEqual((r["completed_runs"], r["failed_runs"]), (2, 1))
        self.assertAlmostEqual(r["mean_time_s"], 2.0)
        r = point(rows, "cam", 2000)
        self.assertEqual((r["completed_runs"], r["mean_time_s"]), (0, ""))

    def test_confidence_interval_uses_the_actual_n(self):
        self.assertEqual(sm.mean_and_ci95([0.5]), (0.5, ""))
        mean, half = sm.mean_and_ci95([0.90, 0.92, 0.94, 0.96, 0.98])
        self.assertAlmostEqual(half, 2.776445 * 0.0316227766 / 5 ** 0.5, places=9)
        mean, half = sm.mean_and_ci95([1.0, 2.0, 3.0, 4.0])
        self.assertAlmostEqual(half, 3.182446 * 1.2909944487 / 2, places=9)


class StoredRunsTests(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(config.JOB_DIR, ignore_errors=True)
        config.JOB_DIR.mkdir(parents=True)

    def write(self, job, status="ok", time_s=1.0, params=None):
        rec = {"key": execute.job_key(job), **job, "params": params or execute.params(),
               "status": status, "peak_memory_mib": 10.0, "error": "",
               "metrics": {"time_s": time_s, "f1": 1.0} if status == "ok" else {}}
        (config.JOB_DIR / f"{execute.job_key(job)}.json").write_text(json.dumps(rec))

    def test_seeds_are_identified_by_their_records(self):
        for job in reversed(execute.job_list()):
            self.write(job, time_s=0.1 * (job["e"] + 1))
        runs, problems = sm.load_runs()
        self.assertEqual(problems, [])
        self.assertEqual(len(runs), 3 * 2 * 2)
        for r in runs:
            self.assertEqual(r["seed"], SETTINGS["seeds"][r["experiment"]])
            self.assertAlmostEqual(r["time_s"], 0.1 * (r["experiment"] + 1))

    def test_missing_runs_are_reported(self):
        jobs = execute.job_list()
        for job in jobs[1:]:
            self.write(job)
        runs, problems = sm.load_runs()
        self.assertEqual(problems, [f"{execute.job_key(jobs[0])}: not run"])

    def test_runs_with_other_parameters_are_not_reused(self):
        job = execute.job_list()[0]
        self.write(job, params={**execute.params(), "min_support": 0.03})
        with self.assertRaises(SystemExit) as stop:
            execute.stored(job)
        self.assertIn("other settings", str(stop.exception))

    def test_a_failure_does_not_skip_the_other_runs(self):
        jobs = execute.job_list()
        self.write(jobs[0], status="timeout>7200s")
        stub = {"status": "ok", "peak_memory_mib": 1.0, "error": "", "metrics": {}}
        with mock.patch.object(algorithm_runs, "run", return_value=stub) as runner:
            rec = execute.run_job(jobs[1])
        runner.assert_called_once()
        self.assertEqual(rec["status"], "ok")

    def test_retry_failed_forgets_only_failed_runs(self):
        jobs = execute.job_list()[:3]
        for job, status in zip(jobs, ["ok", "timeout>7200s", "exit code 1"]):
            self.write(job, status=status)
        self.assertEqual(execute.forget_failed(jobs), 2)
        left = [(config.JOB_DIR / f"{execute.job_key(j)}.json").exists() for j in jobs]
        self.assertEqual(left, [True, False, False])


class CommandLineTests(unittest.TestCase):
    SMALL = ["--sizes", "100,200", "--seeds", "1729", "--algorithms", "cam"]

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
            code, text = self.cli("--force", "--steps", "generate", *self.SMALL, "--output", out)
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
        for name in (".git", ".venv", "my_output"):
            (self.pkg / name).mkdir(exist_ok=True)
            (self.pkg / name / "keep").write_text("x")
            code, text = self.cli("--force", "--steps", "generate", *self.SMALL,
                                  "--output", self.pkg / name)
            self.assertNotEqual(code, 0)
            self.assertIn("must be a folder whose name starts with 'results'", text)
            self.assertTrue((self.pkg / name / "keep").exists())
        code, text = self.cli("--force", "--steps", "generate", *self.SMALL,
                              "--output", self.pkg / "results_test")
        self.assertEqual(code, 0, text)

    def test_force_restarts_when_the_settings_file_is_unreadable(self):
        out = TMP / "unreadable"
        out.mkdir()
        (out / "settings.json").write_text("{")
        code, text = self.cli("--steps", "summarize", *self.SMALL, "--output", out)
        self.assertNotEqual(code, 0)
        self.assertIn("cannot be read", text)
        code, text = self.cli("--force", "--steps", "generate", *self.SMALL, "--output", out)
        self.assertEqual(code, 0, text)
        self.assertTrue((out / "datasets" / "manifest.json").exists())

    def test_invalid_values_are_rejected(self):
        out = TMP / "invalid"
        for option, value, message in (("--min-support", "nan", "not in (0, 1]"),
                                       ("--risup", "inf", "not in (0, 1]"),
                                       ("--similarity", "0", "not in (0, 1]"),
                                       ("--score-threshold", "1.5", "not in (0, 1]"),
                                       ("--seeds", "1,1", "distinct"),
                                       ("--seeds", "-1", "at least 0"),
                                       ("--sizes", "100,100", "distinct"),
                                       ("--sizes", "0", "at least 1"),
                                       ("--timeout", "0", "at least 1"),
                                       ("--algorithms", ",", "distinct"),
                                       ("--algorithms", "cam,cam", "distinct")):
            code, text = self.cli(option, value, "--steps", "summarize", "--output", out)
            self.assertNotEqual(code, 0)
            self.assertIn(message, text)
        self.assertFalse(out.exists())

    def test_one_set_of_settings_per_output_folder(self):
        out = TMP / "settings"
        code, text = self.cli("--steps", "generate", *self.SMALL, "--output", out)
        self.assertEqual(code, 0, text)
        for option, value in (("--min-support", "0.03"), ("--score-threshold", "0.7"),
                              ("--timeout", "60")):
            code, text = self.cli("--resume", "--steps", "run", *self.SMALL, option, value,
                                  "--output", out)
            self.assertNotEqual(code, 0)
            self.assertIn("other values for", text)
        code, text = self.cli("--resume", "--steps", "run", "--sizes", "100,200",
                              "--seeds", "1729,2718", "--output", out)
        self.assertNotEqual(code, 0)
        self.assertIn("other values for: seeds", text)
        code, text = self.cli("--steps", "summarize", "--sizes", "100,300", "--seeds", "1729",
                              "--algorithms", "cam", "--output", out)
        self.assertNotEqual(code, 0)
        self.assertIn("other values for: sizes", text)

    def test_changed_inputs_stop_resume_and_summary(self):
        out = TMP / "inputs"
        code, text = self.cli("--steps", "generate", *self.SMALL, "--output", out)
        self.assertEqual(code, 0, text)
        code, text = self.cli("--steps", "summarize", *self.SMALL, "--output", out)
        self.assertNotEqual(code, 0)
        self.assertIn("runs are missing", text)
        self.assertNotIn("checksum", text)
        with open(out / "datasets" / "N_200" / "crs80_seed_0.csv", "a") as fh:
            fh.write("changed\n")
        for steps in (["--resume", "--steps", "run"], ["--steps", "summarize"]):
            code, text = self.cli(*steps, *self.SMALL, "--output", out)
            self.assertNotEqual(code, 0)
            self.assertIn("checksum", text)


if __name__ == "__main__":
    unittest.main()
