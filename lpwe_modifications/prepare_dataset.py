import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import config


def sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_inputs() -> None:
    data = config.DATA_DIR
    path = data / "manifest.json"
    if not path.exists():
        sys.exit(f"dataset missing in {data}: run the generate step first")
    manifest = json.loads(path.read_text())
    names = ["ground_truth_sequences.csv"] + [f"crs{p}_({e}).csv" for p in config.PERCENTAGES
                                              for e in config.EXPERIMENTS]
    for name in names:
        expected = manifest["files"].get(name)
        if expected is None or not (data / name).exists():
            sys.exit(f"{name} is missing from the dataset in {data}")
        if sha256(data / name) != expected:
            sys.exit(f"{name} does not match its checksum in manifest.json: the input "
                     "changed after the dataset was generated; use --force to start again")


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ, TERM="dumb")
        subprocess.run([sys.executable, str(config.GENERATOR_FILE)], cwd=tmp, env=env,
                       stdout=subprocess.DEVNULL, check=True)
        shutil.rmtree(config.DATA_DIR, ignore_errors=True)
        config.DATA_DIR.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(Path(tmp) / config.DATA_DIRNAME), str(config.DATA_DIR))
    manifest = {"generator": "generator/create_files.py",
                "files": {f.name: sha256(f) for f in sorted(config.DATA_DIR.glob("*.csv"))}}
    (config.DATA_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"{len(manifest['files'])} files written to {config.DATA_DIR}")


if __name__ == "__main__":
    main()
