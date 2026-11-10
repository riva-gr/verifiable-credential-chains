import argparse
import copy
import csv
import json
import random
from pathlib import Path


DEFAULT_SIZE = 1000
DEFAULT_SEEDS = [1729, 2718, 3141, 5772, 8119]
DEFAULT_POISON_PERCENTAGES = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]


def create_ground_truth_sequences(min_length=2, max_length=11):
    sequences = []
    for length in range(min_length, max_length + 1):
        letter = chr(65 + len(sequences))
        sequences.append([f"{letter}{index}" for index in range(1, length + 1)])
    return sequences


def create_in_order_sequence(base_sequence, inclusion_probability, rng):
    return [
        credential
        for credential in base_sequence
        if rng.random() < inclusion_probability
    ]


def create_miscellaneous_sequence(min_length, max_length, vocabulary_size, rng):
    length = rng.randint(min_length, max_length)
    values = rng.sample(range(1, vocabulary_size + 1), length)
    return [f"cr{value}" for value in values]


def interleave_sequences(first, second, rng):
    first = copy.copy(first)
    second = copy.copy(second)
    combined = []
    while first or second:
        selected = rng.choice([first, second])
        if not selected:
            selected = first if selected == second else second
        combined.append(selected.pop(0))
    return combined


def build_benign_population(size, ground_truth, availability, rng):
    population = []
    base_count, remainder = divmod(size, len(ground_truth))

    for chain_index, chain in enumerate(ground_truth):
        chain_count = base_count + (1 if chain_index < remainder else 0)
        in_order_sequences = [
            create_in_order_sequence(chain, availability, rng)
            for _ in range(chain_count)
        ]
        miscellaneous_sequences = [
            create_miscellaneous_sequence(2, 11, 100, rng)
            for _ in range(chain_count)
        ]
        for in_order, miscellaneous in zip(
            in_order_sequences,
            miscellaneous_sequences,
        ):
            record = interleave_sequences(in_order, miscellaneous, rng)
            population.append((record, chain_index))

    return population


def validate_poisoned_dataset(
    rows,
    benign_rows,
    malicious_indices,
    target_benign_indices,
    anchor_label,
    poison_label,
    expected_size,
):
    if len(rows) != expected_size:
        raise RuntimeError("Generated dataset has an unexpected number of rows.")

    malicious = set(malicious_indices)
    if malicious & set(target_benign_indices):
        raise RuntimeError("A benign target identity was replaced by an attacker.")

    poison_occurrences = 0
    for index, row in enumerate(rows):
        contains_poison = poison_label in row
        if contains_poison:
            poison_occurrences += 1

        if index in malicious:
            if not contains_poison or anchor_label not in row:
                raise RuntimeError("A malicious row is missing the attack labels.")
            if row.index(anchor_label) >= row.index(poison_label):
                raise RuntimeError("A malicious row has the wrong attack ordering.")
        elif row != benign_rows[index] or contains_poison:
            raise RuntimeError("A non-malicious row was unexpectedly modified.")

    if poison_occurrences != len(malicious):
        raise RuntimeError("The poison-label count does not match the attack size.")


def build_poison_record(target_chain, poison_label, availability, rng):
    anchor_label = target_chain[-1]
    imitated_chain = create_in_order_sequence(target_chain, availability, rng)


    if anchor_label not in imitated_chain:
        imitated_chain.append(anchor_label)
    imitated_chain = [item for item in target_chain if item in imitated_chain]
    imitated_chain.append(poison_label)

    miscellaneous = create_miscellaneous_sequence(2, 11, 100, rng)
    return interleave_sequences(imitated_chain, miscellaneous, rng)


def percentage_folder(percentage):
    value = float(percentage)
    if value.is_integer():
        text = str(int(value))
    else:
        text = str(value).replace(".", "p")
    return f"poison_{text}pct"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("datasets"))
    parser.add_argument("--size", type=int, default=DEFAULT_SIZE)
    parser.add_argument(
        "--seeds",
        nargs="+",
        type=int,
        default=DEFAULT_SEEDS,
    )
    parser.add_argument(
        "--poison-percentages",
        nargs="+",
        type=float,
        default=DEFAULT_POISON_PERCENTAGES,
    )
    parser.add_argument("--availability", type=float, default=0.80)
    parser.add_argument("--poison-label", default="POISON_Z")
    parser.add_argument(
        "--target-chain-index",
        type=int,
        default=-1,
        help="Zero-based ground-truth chain index; -1 selects the longest chain.",
    )
    return parser.parse_args()


def validate_args(args, number_of_chains):
    if args.size <= 0:
        raise ValueError("--size must be positive.")
    if not 0 < args.availability <= 1:
        raise ValueError("--availability must be in (0, 1].")
    if any(value < 0 or value >= 90 for value in args.poison_percentages):
        raise ValueError("Poison percentages must be in [0, 90).")
    if args.target_chain_index == -1:
        args.target_chain_index = number_of_chains - 1
    if not 0 <= args.target_chain_index < number_of_chains:
        raise ValueError("--target-chain-index is outside the ground truth.")


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output_file:
        csv.writer(output_file).writerows(rows)


def main():
    args = parse_args()
    ground_truth = create_ground_truth_sequences()
    validate_args(args, len(ground_truth))

    target_chain = ground_truth[args.target_chain_index]
    anchor_label = target_chain[-1]
    maximum_percentage = max(args.poison_percentages)
    maximum_poisoned = round(args.size * maximum_percentage / 100)

    for experiment, seed in enumerate(args.seeds):
        benign_rng = random.Random(seed)
        population = build_benign_population(
            args.size,
            ground_truth,
            args.availability,
            benign_rng,
        )
        benign_rows = [record for record, _ in population]
        source_chains = [chain_index for _, chain_index in population]


        eligible_indices = [
            index
            for index, chain_index in enumerate(source_chains)
            if chain_index != args.target_chain_index
        ]
        selection_rng = random.Random(seed + 1_000_003)
        selection_rng.shuffle(eligible_indices)

        if maximum_poisoned > len(eligible_indices):
            raise ValueError(
                "The largest poison percentage exceeds the available "
                "non-target identities."
            )

        selected_at_maximum = eligible_indices[:maximum_poisoned]
        poison_rows = {}
        for position, row_index in enumerate(selected_at_maximum):
            poison_rng = random.Random(seed * 10_000 + position)
            poison_rows[row_index] = build_poison_record(
                target_chain,
                args.poison_label,
                args.availability,
                poison_rng,
            )

        target_benign_indices = [
            index
            for index, chain_index in enumerate(source_chains)
            if chain_index == args.target_chain_index
        ]

        for percentage in args.poison_percentages:
            poisoned_count = round(args.size * percentage / 100)
            malicious_indices = selected_at_maximum[:poisoned_count]
            poisoned_rows = copy.deepcopy(benign_rows)
            for row_index in malicious_indices:
                poisoned_rows[row_index] = poison_rows[row_index]

            validate_poisoned_dataset(
                poisoned_rows,
                benign_rows,
                malicious_indices,
                target_benign_indices,
                anchor_label,
                args.poison_label,
                args.size,
            )

            dataset_root = args.output_dir / percentage_folder(percentage)
            data_directory = dataset_root / "GT_and_CSV_files"
            dataset_path = data_directory / f"crs80_({experiment}).csv"
            ground_truth_path = data_directory / "ground_truth_sequences.csv"
            metadata_path = data_directory / f"poisoning_metadata_({experiment}).json"

            write_csv(dataset_path, poisoned_rows)
            write_csv(ground_truth_path, ground_truth)

            metadata = {
                "size": args.size,
                "experiment": experiment,
                "seed": seed,
                "poison_percentage": percentage,
                "poisoned_records": poisoned_count,
                "poison_label": args.poison_label,
                "anchor_label": anchor_label,
                "target_chain_index": args.target_chain_index,
                "target_chain": target_chain,
                "malicious_indices": malicious_indices,
                "target_benign_indices": target_benign_indices,
                "attack_description": (
                    "Non-target identities are replaced by records that imitate "
                    "the selected ground-truth chain and consistently place the "
                    "poison label after its final credential."
                ),
            }
            metadata_path.write_text(
                json.dumps(metadata, indent=2),
                encoding="utf-8",
            )
            print(
                f"Created {dataset_path} with {poisoned_count} poisoned "
                f"records ({percentage:g}%)."
            )

    print("Dataset generation completed.")


if __name__ == "__main__":
    main()
