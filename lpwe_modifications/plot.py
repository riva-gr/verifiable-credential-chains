import csv
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config

matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["font.family"] = "sans-serif"
matplotlib.rcParams["font.sans-serif"] = ["Arial", "Liberation Sans", "DejaVu Sans"]

FIGURES = [("optimal_summary.csv", "accuracy", "Accuracy", "Accuracy"),
           ("optimal_summary.csv", "f1", "F1 Score", "F1_Score"),
           ("time_fixed_setting.csv", "time", "Processing Time", "Processing_Time")]
FONT_SIZE = 42


def load(name):
    path = config.RUN_DIR / "summary" / name
    if not path.exists():
        sys.exit(f"summary/{name} missing: run the select step first")
    data = {}
    with open(path) as fh:
        for row in csv.DictReader(fh):
            data.setdefault(row["variant"], {})[int(row["percentage"])] = row
    return data


def bars(row, metric):
    mean = float(row[f"{metric}_mean"])
    if not row[f"{metric}_ci95_low"]:
        return mean, 0.0, 0.0
    low, high = float(row[f"{metric}_ci95_low"]), float(row[f"{metric}_ci95_high"])
    low = max(low, 0.0)
    if metric != "time":
        high = min(high, 1.0)
    return mean, mean - low, high - mean


def plot(data, metric, name, tag):
    plt.figure(figsize=(8, 6))
    top, xs_all = 0.0, []
    for variant, (_, label, style, color) in config.VARIANTS.items():
        if variant not in data:
            continue
        xs = sorted(data[variant])
        xs_all += xs
        mean, lower, upper = zip(*(bars(data[variant][p], metric) for p in xs))
        top = max(top, 1.2 * max(mean), 1.05 * max(m + u for m, u in zip(mean, upper)))
        plt.errorbar(xs, mean, yerr=[lower, upper], label=label, fmt=style, color=color,
                     elinewidth=2, capsize=3, linewidth=2.5)

    xs = sorted(set(xs_all))
    plt.xlabel("Ground Truth (%)", fontsize=FONT_SIZE)
    plt.ylabel("Time (s)" if metric == "time" else name, fontsize=FONT_SIZE)
    plt.title(name + " Comparison", fontsize=FONT_SIZE)
    plt.legend(fontsize=18, loc="best")
    plt.xticks(xs, fontsize=28)
    plt.yticks(fontsize=28)
    plt.grid(True, which="both", linestyle="--", linewidth=0.5)
    if metric == "time":
        plt.xlim([min(xs) * 0.9, max(xs) * 1.01])
        plt.ylim([0, top])
    else:
        if len(xs) > 1:
            plt.xlim([min(xs), max(xs)])
        plt.ylim([0, 1.05])
    out = config.RUN_DIR / "figures" / f"LPwE_modifications_comparison_(optimal)_{tag}.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, dpi=600, bbox_inches="tight")
    plt.close()
    print(out)


def main() -> None:
    for table, metric, name, tag in FIGURES:
        plot(load(table), metric, name, tag)


if __name__ == "__main__":
    main()
