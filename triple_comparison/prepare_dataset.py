import hashlib
import importlib.util
import json
import sys

import config


def sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_inputs() -> None:

    data = config.OUT_DIR / "GT_and_CSV_files"
    path = data / "manifest.json"
    if not path.exists():
        sys.exit(f"dataset missing in {data}: run the generate step first")
    manifest = json.loads(path.read_text())
    if manifest.get("seed") != config.SEED:
        sys.exit(f"the dataset in {data} was generated with seed {manifest.get('seed')}")
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
    spec = importlib.util.spec_from_file_location("create_files_config",
                                                  config.GENERATOR_FILE)
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)

    out = config.OUT_DIR / "GT_and_CSV_files"
    gen.OUT_DIR = str(out)
    gen.SEED = config.SEED
    gen.CHAINS = config.CHAINS
    gen.MIN_LENGTH = config.MIN_LENGTH
    gen.IDENTITIES_PER_CHAIN = config.IDENTITIES_PER_CHAIN
    gen.NOISE_SIZE = config.NOISE_SIZE
    gen.MISC_MIN, gen.MISC_MAX = config.MISC_MIN, config.MISC_MAX
    gen.PERCENTAGES = list(config.PERCENTAGES)
    gen.EXPERIMENTS = len(config.EXPERIMENTS)
    gen.main()

    manifest = {"seed": config.SEED,
                "files": {f.name: sha256(f) for f in sorted(out.glob("*.csv"))}}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
