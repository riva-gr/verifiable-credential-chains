from __future__ import annotations

import csv
import hashlib
import random
import string
from pathlib import Path


OUT_DIR = "GT_and_CSV_files"


SEED = 1


CHAINS = 10


MIN_LENGTH = 2


IDENTITIES_PER_CHAIN = 100


NOISE_SIZE = 100


MISC_MIN = 2
MISC_MAX = 11


PERCENTAGES = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]


EXPERIMENTS = 5


def stable_seed(base_seed: int, experiment: int, percentage: int) -> int:


    key = f"{base_seed}-{experiment}-{percentage}".encode()
    digest = hashlib.blake2b(key, digest_size=8).digest()
    return int.from_bytes(digest, "big")


def ground_truth_chains(n_chains: int, min_length: int) -> list[list[str]]:

    return [[f"{string.ascii_uppercase[i]}{j}"
             for j in range(1, min_length + i + 1)]
            for i in range(n_chains)]


def in_order_subset(chain: list[str], keep_prob: float,
                    rng: random.Random) -> list[str]:

    return [c for c in chain if rng.random() < keep_prob]


def misc_credentials(rng: random.Random, lo: int, hi: int,
                     pool: int) -> list[str]:

    k = rng.randint(lo, hi)
    return [f"cr{n}" for n in rng.sample(range(1, pool + 1), k)]


def interleave(sequences: list[list[str]], rng: random.Random) -> list[str]:

    pools = [list(s) for s in sequences if s]
    out: list[str] = []
    while pools:
        pool = rng.choice(pools)
        out.append(pool.pop(0))
        if not pool:
            pools.remove(pool)
    return out


def build_dataset(gt_chains: list[list[str]], percentage: int,
                  rng: random.Random) -> list[list[str]]:

    keep_prob = percentage / 100
    rows: list[list[str]] = []
    for chain in gt_chains:
        for _ in range(IDENTITIES_PER_CHAIN):
            parts = [in_order_subset(chain, keep_prob, rng)]
            parts.append(misc_credentials(rng, MISC_MIN, MISC_MAX, NOISE_SIZE))
            row = interleave(parts, rng)
            if row:
                rows.append(row)
    return rows


def validate() -> None:

    if not 1 <= CHAINS <= len(string.ascii_uppercase):
        raise SystemExit("CHAINS must be between 1 and 26")
    if MISC_MIN < 0 or MISC_MAX < MISC_MIN:
        raise SystemExit("require 0 <= MISC_MIN <= MISC_MAX")
    if MISC_MAX > NOISE_SIZE:
        raise SystemExit("MISC_MAX cannot exceed NOISE_SIZE")
    if any(p < 1 or p > 100 for p in PERCENTAGES):
        raise SystemExit("every value in PERCENTAGES must lie in 1..100")
    if EXPERIMENTS < 1:
        raise SystemExit("EXPERIMENTS must be at least 1")


def main() -> None:
    validate()

    out_dir = Path(OUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    gt_chains = ground_truth_chains(CHAINS, MIN_LENGTH)

    with (out_dir / "ground_truth_sequences.csv").open("w", newline="") as fh:
        csv.writer(fh).writerows(gt_chains)

    total = 0
    for exp in range(EXPERIMENTS):
        for pct in PERCENTAGES:
            rng = random.Random(stable_seed(SEED, exp, pct))
            rows = build_dataset(gt_chains, pct, rng)
            with (out_dir / f"crs{pct}_({exp}).csv").open("w", newline="") as fh:
                csv.writer(fh).writerows(rows)
            total += 1

    gt_creds = sum(len(c) for c in gt_chains)
    print(f"ground truth : {CHAINS} chains, {gt_creds} credentials, "
          f"lengths {MIN_LENGTH}..{MIN_LENGTH + CHAINS - 1}")
    print(f"wallets      : {CHAINS * IDENTITIES_PER_CHAIN} per file, "
          f"noise pool {NOISE_SIZE}")
    print(f"written      : {total} dataset files + ground truth "
          f"-> {out_dir}  (seed {SEED})")


if __name__ == "__main__":
    main()
