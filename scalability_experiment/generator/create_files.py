from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path


DEFAULT_SIZES = (1000, 2500, 5000, 10000, 20000)
DEFAULT_SEEDS = (1729, 2718, 3141, 5772, 8119)


def create_ground_truth_sequences(
    min_length: int = 2, max_length: int = 11
) -> list[list[str]]:
    sequences: list[list[str]] = []
    for offset, length in enumerate(range(min_length, max_length + 1)):
        prefix = chr(65 + offset)
        sequences.append([f"{prefix}{index}" for index in range(1, length + 1)])
    return sequences


def retain_in_order(
    base_sequence: list[str], availability: float, rng: random.Random
) -> list[str]:
    return [item for item in base_sequence if rng.random() < availability]


def create_miscellaneous_sequence(
    minimum: int, maximum: int, vocabulary_size: int, rng: random.Random
) -> list[str]:
    length = rng.randint(minimum, maximum)
    indices = rng.sample(range(1, vocabulary_size + 1), length)
    return [f"cr{index}" for index in indices]


def interleave_preserving_order(
    first: list[str], second: list[str], rng: random.Random
) -> list[str]:
    first = first.copy()
    second = second.copy()
    combined: list[str] = []
    while first or second:
        if not first:
            combined.append(second.pop(0))
        elif not second:
            combined.append(first.pop(0))
        elif rng.randrange(2) == 0:
            combined.append(first.pop(0))
        else:
            combined.append(second.pop(0))
    return combined


def records_per_chain(total_records: int, chain_count: int) -> list[int]:
    base, remainder = divmod(total_records, chain_count)
    return [base + (1 if index < remainder else 0) for index in range(chain_count)]


def generate_dataset(
    total_records: int,
    seed: int,
    availability: float,
    miscellaneous_count: int,
    minimum_misc_per_record: int,
    maximum_misc_per_record: int,
    ground_truth: list[list[str]],
) -> list[list[str]]:
    rng = random.Random(seed)
    records: list[list[str]] = []
    for chain, count in zip(
        ground_truth, records_per_chain(total_records, len(ground_truth))
    ):
        for _ in range(count):
            retained = retain_in_order(chain, availability, rng)
            miscellaneous = create_miscellaneous_sequence(
                minimum_misc_per_record,
                maximum_misc_per_record,
                miscellaneous_count,
                rng,
            )
            records.append(interleave_preserving_order(retained, miscellaneous, rng))
    rng.shuffle(records)
    assert len(records) == total_records
    return records


def write_csv(path: Path, rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("datasets"))
    parser.add_argument("--sizes", nargs="+", type=int, default=DEFAULT_SIZES)
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    parser.add_argument("--availability", type=float, default=0.80)
    parser.add_argument("--miscellaneous-count", type=int, default=100)
    parser.add_argument("--minimum-misc-per-record", type=int, default=2)
    parser.add_argument("--maximum-misc-per-record", type=int, default=11)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not 0.0 <= args.availability <= 1.0:
        raise ValueError("--availability must be between 0 and 1")
    if args.maximum_misc_per_record > args.miscellaneous_count:
        raise ValueError("miscellaneous vocabulary is smaller than a requested record")

    ground_truth = create_ground_truth_sequences()
    write_csv(args.output_dir / "ground_truth_sequences.csv", ground_truth)

    for size in args.sizes:
        if size <= 0:
            raise ValueError("all dataset sizes must be positive")
        for seed_index, seed in enumerate(args.seeds):
            records = generate_dataset(
                total_records=size,
                seed=seed,
                availability=args.availability,
                miscellaneous_count=args.miscellaneous_count,
                minimum_misc_per_record=args.minimum_misc_per_record,
                maximum_misc_per_record=args.maximum_misc_per_record,
                ground_truth=ground_truth,
            )
            path = args.output_dir / f"N_{size}" / f"crs80_seed_{seed_index}.csv"
            write_csv(path, records)
            print(f"generated {path} ({size} records, seed={seed})")


if __name__ == "__main__":
    main()
