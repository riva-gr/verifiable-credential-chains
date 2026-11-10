import hashlib
import json
import subprocess
import sys

import config

MANIFEST = config.DATA_DIR / "manifest.json"


def sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dataset_settings() -> dict:
    return {"seeds": config.SEEDS, **config.GENERATOR}


def files():
    yield "ground_truth_sequences.csv", config.GT_FILE
    for n in config.SIZES:
        for e in range(len(config.SEEDS)):
            path = config.dataset_file(n, e)
            yield path.relative_to(config.DATA_DIR).as_posix(), path


def verify_inputs() -> None:
    if not MANIFEST.exists():
        sys.exit(f"dataset missing in {config.DATA_DIR}: run the generate step first")
    manifest = json.loads(MANIFEST.read_text())
    if manifest["settings"] != dataset_settings():
        sys.exit(f"the datasets in {config.DATA_DIR} were generated with other settings")
    for name, path in files():
        expected = manifest["files"].get(name)
        if expected is None or not path.exists():
            sys.exit(f"{name} is missing from the datasets in {config.DATA_DIR}")
        if sha256(path) != expected:
            sys.exit(f"{path} does not match its checksum in manifest.json: the input "
                     "changed after the datasets were generated; use --force to start again")


def main() -> None:
    if MANIFEST.exists():
        print(f"keeping the datasets in {config.DATA_DIR}")
        return
    g = config.GENERATOR
    cmd = [sys.executable, str(config.GENERATOR_FILE), "--output-dir", str(config.DATA_DIR),
           "--sizes", *map(str, config.SIZES), "--seeds", *map(str, config.SEEDS),
           "--availability", str(g["availability"]),
           "--miscellaneous-count", str(g["miscellaneous_count"]),
           "--minimum-misc-per-record", str(g["minimum_misc_per_record"]),
           "--maximum-misc-per-record", str(g["maximum_misc_per_record"])]
    if subprocess.run(cmd).returncode:
        sys.exit("dataset generation failed")
    MANIFEST.write_text(json.dumps({"settings": dataset_settings(),
                                    "files": {name: sha256(path) for name, path in files()}},
                                   indent=2))


if __name__ == "__main__":
    main()
