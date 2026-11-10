import csv
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config

matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["font.family"] = "sans-serif"
matplotlib.rcParams["font.sans-serif"] = ["Arial", "Liberation Sans", "DejaVu Sans"]


SPEC = {
    "gspx": ("GSPX", ("min_support", "Min. Support"), ("risup", "Relative In Order Support")),
    "cam": ("CAM", ("min_support", "Min. Support"), ("risup", "Relative In Order Support")),
    "lpwe": ("LPwE", ("similarity", "Sim. Index"), ("score_threshold", "Score Threshold")),
}

PANELS = {
    "gspx": [("accuracy", "Accuracy", "Accuracy", "GSP-X Accuracy vs RISup"),
             ("f1", "F1 Score", "F1_Score", "GSP-X F1 Score vs RISup")],
    "cam": [("accuracy", "Accuracy", "Accuracy", "CAM Accuracy vs RISup"),
            ("f1", "F1 Score", "F1_Score", "CAM F1 Score vs RISup")],
    "lpwe": [("accuracy", "Accuracy", "Accuracy", "LPwE Accuracy vs Score Threshold"),
             ("f1", "F1", "F1_Score", "LPwE F1 vs Score Threshold")],
}
MARKERS = ["o", "s", "^", "D", "v", "<", ">", "X", "P", "*"]


def load():
    path = config.RUN_DIR / "summary" / "sensitivity.csv"
    if not path.exists():
        sys.exit("summary/sensitivity.csv missing: run the summarize step first")
    with open(path) as fh:
        return list(csv.DictReader(fh))


def point(row, metric):
    if int(row["n"]) == 0:
        return float("nan"), 0.0, 0.0
    mean = float(row[f"{metric}_mean"])
    if not row[f"{metric}_ci95_low"]:
        return mean, 0.0, 0.0
    low = max(float(row[f"{metric}_ci95_low"]), 0.0)
    high = min(float(row[f"{metric}_ci95_high"]), 1.0)
    return mean, mean - low, high - mean


def main() -> None:
    rows = load()
    for algo in config.ALGORITHMS:
        prefix, (pname, legend_title), (tname, xlabel) = SPEC[algo]
        group = [r for r in rows if r["algorithm"] == algo]
        values = sorted({float(r[pname]) for r in group})
        for metric, ylabel, suffix, title in PANELS[algo]:
            plt.figure(figsize=(8, 6))
            for i, v in enumerate(values):
                line = sorted((r for r in group if float(r[pname]) == v),
                              key=lambda r: float(r[tname]))
                mean, lower, upper = zip(*(point(r, metric) for r in line))
                plt.errorbar([float(r[tname]) for r in line], mean, yerr=[lower, upper],
                             label=f"{v:g}", marker=MARKERS[i % len(MARKERS)], markersize=7,
                             linewidth=2, elinewidth=1.5, capsize=5)
            plt.title(title, fontsize=36)
            plt.xlabel(xlabel, fontsize=38)
            plt.ylabel(ylabel, fontsize=38)
            plt.xticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0], fontsize=26)
            plt.yticks(fontsize=26)
            plt.xlim(-0.03, 1.03)
            plt.ylim(bottom=-0.03)
            plt.grid(True, which="both", linestyle="--", linewidth=0.5)
            plt.legend(title=legend_title, fontsize=20, title_fontsize=20, loc="best")
            out = config.RUN_DIR / "figures" / f"{prefix}_{suffix}.pdf"
            out.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(out, dpi=600, bbox_inches="tight")
            plt.close()
            print(out)


if __name__ == "__main__":
    main()
