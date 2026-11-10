import csv
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config

matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["font.family"] = "sans-serif"
matplotlib.rcParams["font.sans-serif"] = ["Arial", "Liberation Sans", "DejaVu Sans"]

ALGORITHMS = [("gspx", "GSP-X", "-", "C0"), ("cam", "CAM", "--", "C1"),
              ("lpwe", "LPwE", ":", "C2")]
PART1 = [("accuracy", "Accuracy", "Accuracy"), ("f1", "F1 Score", "F1")]

PART2 = {"gspx": ("GSPX", "RISUP Threshold", 0.5), "cam": ("CAM", "RISUP Threshold", 0.5),
         "lpwe": ("LPwE", "Score Threshold", 0.7)}


def read(name):
    path = config.RUN_DIR / "summary" / name
    if not path.exists():
        sys.exit(f"summary/{name} missing: run the select step first")
    with open(path) as fh:
        return list(csv.DictReader(fh))


def bars(row, metric):
    mean = float(row[f"{metric}_mean"])
    if not row[f"{metric}_ci95_low"]:
        return mean, 0.0, 0.0
    low = max(float(row[f"{metric}_ci95_low"]), 0.0)
    high = min(float(row[f"{metric}_ci95_high"]), 1.0)
    return mean, mean - low, high - mean


def save(name):
    out = config.RUN_DIR / "figures" / name
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, dpi=600, bbox_inches="tight")
    plt.close()
    print(out)


def part1():
    rows = read("optimal_summary.csv")
    if not rows:
        print("no noise size of the accuracy and F1 figures in the results")
        return
    sizes = sorted({int(r["noise_size"]) for r in rows})
    x = {n: i for i, n in enumerate(sizes)}
    for metric, name, prefix in PART1:
        plt.figure(figsize=(8, 6))
        for algo, label, style, color in ALGORITHMS:
            group = sorted((r for r in rows if r["algorithm"] == algo),
                           key=lambda r: int(r["noise_size"]))
            if not group:
                continue
            mean, lower, upper = zip(*(bars(r, metric) for r in group))
            plt.errorbar([x[int(r["noise_size"])] for r in group], mean, yerr=[lower, upper],
                         label=label, fmt=style, color=color, elinewidth=2, capsize=3,
                         linewidth=2.5)
        plt.xlabel("Noise Size", fontsize=41)
        plt.ylabel(name, fontsize=42)
        plt.title(name + " Comparison", fontsize=42)
        plt.legend(fontsize=28, loc="best")
        plt.xticks(range(len(sizes)), [str(n) for n in sizes], fontsize=28)
        plt.yticks(fontsize=28)
        plt.grid(True, which="both", linestyle="--", linewidth=0.5)
        plt.xlim([-0.2, len(sizes) - 0.8])
        plt.ylim([0, 1.05])
        save(f"{prefix}_best_{config.PERCENTAGES[0]}_noises.pdf")


def part2():
    rows = read("threshold_summary.csv")
    sizes = sorted({int(r["noise_size"]) for r in rows})
    x = {n: i for i, n in enumerate(sizes)}
    norm = matplotlib.colors.Normalize(vmin=0, vmax=1)
    for algo, *_ in ALGORITHMS:
        group = [r for r in rows if r["algorithm"] == algo]
        if not group:
            continue
        prefix, ylabel, alpha = PART2[algo]
        done = [r for r in group if int(r["n"]) > 0]
        none = [r for r in group if int(r["n"]) == 0]
        plt.figure(figsize=(10, 8))
        sc = plt.scatter([x[int(r["noise_size"])] for r in done],
                         [float(r["threshold"]) for r in done],
                         c=[float(r["accuracy_mean"]) for r in done],
                         s=500, cmap="Blues", alpha=alpha, norm=norm)
        if none:
            plt.scatter([x[int(r["noise_size"])] for r in none],
                        [float(r["threshold"]) for r in none], marker="x", s=200, c="grey")
        plt.xlabel("Noise Size", fontsize=44)
        plt.ylabel(ylabel, fontsize=44)
        plt.grid(True, which="both", linestyle="--", linewidth=0.5)
        plt.xticks(range(len(sizes)), labels=[str(n) for n in sizes], fontsize=28)
        plt.yticks(fontsize=28)
        if not done:
            sc = matplotlib.cm.ScalarMappable(norm=norm, cmap="Blues")
        cbar = plt.colorbar(sc, ax=plt.gca())
        cbar.set_label("Accuracy", fontsize=44)
        cbar.ax.tick_params(labelsize=28)
        save(f"{prefix}_Accuracy_scatterplot.pdf")


def main() -> None:
    part1()
    part2()


if __name__ == "__main__":
    main()
