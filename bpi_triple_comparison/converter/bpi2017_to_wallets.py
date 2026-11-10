from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path

END_STATES = ["A_Pending", "A_Denied", "A_Cancelled"]
NOT_IN_CHAINS = {"A_Incomplete", "O_Sent (online only)"}
COLUMNS = {"case:concept:name", "concept:name", "time:timestamp", "lifecycle:transition"}


def read_cases(log: Path, prefixes: tuple[str, ...]) -> dict[str, list[tuple[str, str]]]:
    cases: dict[str, list[tuple[str, str]]] = defaultdict(list)
    with log.open(newline="") as fh:
        reader = csv.DictReader(fh)
        missing = COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(f"log is missing columns: {sorted(missing)}")
        for row in reader:
            if row["lifecycle:transition"] != "complete":
                continue
            if not row["concept:name"].startswith(prefixes):
                continue
            cases[row["case:concept:name"]].append((row["time:timestamp"], row["concept:name"]))
    return cases


def wallets_of(cases: dict[str, list[tuple[str, str]]]) -> list[list[str]]:
    wallets = []
    for events in cases.values():
        events.sort(key=lambda t: t[0])
        wallet: list[str] = []
        for _, activity in events:
            if activity not in wallet:
                wallet.append(activity)
        if len(wallet) >= 2:
            wallets.append(wallet)
    return wallets


def reference_chains(wallets: list[list[str]]) -> list[list[str]]:
    chains = []
    for end in END_STATES:
        orders = Counter(tuple(c for c in w if c not in NOT_IN_CHAINS)
                         for w in wallets if end in w)
        chains.append(list(orders.most_common(1)[0][0]))
    return chains


def write(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", newline="") as fh:
        csv.writer(fh).writerows(rows)
    print(f"{path}  ({len(rows)} rows)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("log", type=Path, help="BPI Challenge 2017 event log as CSV")
    ap.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parent.parent / "data")
    a = ap.parse_args()
    a.data_dir.mkdir(parents=True, exist_ok=True)

    wallets = wallets_of(read_cases(a.log, ("A_", "O_")))
    write(a.data_dir / "bpi2017_wallets.csv", wallets)
    write(a.data_dir / "reference_chains.csv", reference_chains(wallets))


if __name__ == "__main__":
    main()
