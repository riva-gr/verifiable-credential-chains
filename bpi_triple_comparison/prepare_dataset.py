from __future__ import annotations

import csv
import hashlib
import json
import random
import sys

import config


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_rows(path) -> list[list[str]]:
    with open(path, newline="") as fh:
        return [row for row in csv.reader(fh) if row]


def mask(row, reference, threshold, rng) -> list[str]:

    return [c for c in row if c not in reference or rng.random() < threshold]


def load():

    for path, expected in config.SHA256.items():
        if sha256(path) != expected:
            sys.exit(f"checksum mismatch for {path}: it differs from the file "
                     "used for the published results")

    wallets = read_rows(config.WALLETS_FILE)
    chains = read_rows(config.REFERENCE_FILE)

    if config.WALLETS_PER_REPLICATE > len(wallets):
        sys.exit(f"--wallets cannot exceed {len(wallets)}")
    return wallets, chains


def write_dataset(run_dir, source, chains) -> None:

    reference = {c for chain in chains for c in chain}
    out = run_dir / "GT_and_CSV_files"
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "ground_truth_sequences.csv", "w", newline="") as fh:
        csv.writer(fh).writerows(chains)
    manifest = {"seed": config.SEED, "source_cases": len(source),
                "wallets_per_replicate": config.WALLETS_PER_REPLICATE,
                "reference_chains": chains,
                "ground_truth_sha256": sha256(out / "ground_truth_sequences.csv"),
                "files": {}}
    for e in config.EXPERIMENTS:
        idx = random.Random(f"{config.SEED}-sample-{e}").sample(
            range(len(source)), config.WALLETS_PER_REPLICATE)
        sample = [source[i] for i in idx]
        for p in config.PERCENTAGES:
            rng = random.Random(f"{config.SEED}-mask-{e}-{p}")
            rows = [mask(r, reference, p / 100, rng) for r in sample]
            path = out / f"crs{p}_({e}).csv"
            with open(path, "w", newline="") as fh:
                csv.writer(fh).writerows(rows)
            kept = sum(c in reference for r in rows for c in r)
            total = sum(c in reference for r in sample for c in r)
            manifest["files"][path.name] = {
                "rows": len(rows), "empty_rows": sum(not r for r in rows),
                "reference_kept_share": round(kept / total, 4),
                "mean_credentials_per_row": round(sum(map(len, rows)) / len(rows), 3),
                "sha256": sha256(path)}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"wrote {len(manifest['files'])} files to {out}")


def verify_inputs() -> None:

    data = config.RUN_DIR / "GT_and_CSV_files"
    path = data / "manifest.json"
    if not path.exists():
        sys.exit(f"dataset missing in {data}: run the prepare step first")
    manifest = json.loads(path.read_text())
    for k, v in (("seed", config.SEED), ("wallets_per_replicate", config.WALLETS_PER_REPLICATE)):
        if manifest.get(k) != v:
            sys.exit(f"the dataset in {data} was prepared with {k} = {manifest.get(k)}")
    gt = data / "ground_truth_sequences.csv"
    if not gt.exists():
        sys.exit(f"ground_truth_sequences.csv is missing from {data}")
    if ("ground_truth_sha256" in manifest and sha256(gt) != manifest["ground_truth_sha256"]) \
            or read_rows(gt) != manifest["reference_chains"]:
        sys.exit("ground_truth_sequences.csv does not match manifest.json: the input "
                 "changed after the dataset was prepared; use --force to start again")
    for p in config.PERCENTAGES:
        for e in config.EXPERIMENTS:
            name = f"crs{p}_({e}).csv"
            entry = manifest["files"].get(name)
            if entry is None or not (data / name).exists():
                sys.exit(f"{name} is missing from the dataset in {data}")
            if sha256(data / name) != entry["sha256"]:
                sys.exit(f"{name} does not match its checksum in manifest.json: the input "
                         "changed after the dataset was prepared; use --force to start again")


def main() -> None:
    wallets, chains = load()
    write_dataset(config.RUN_DIR, wallets, chains)


if __name__ == "__main__":
    main()
