import csv
import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, NullLocator

import config


matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
matplotlib.rcParams["font.family"] = "sans-serif"
matplotlib.rcParams["font.sans-serif"] = [
    "Arial",
    "Liberation Sans",
    "DejaVu Sans",
]

FONT_SIZE = 42
TICK_FONT_SIZE = 28
LEGEND_FONT_SIZE = 28


ALGORITHM_STYLES = {
    "GSP-X": {"color": "tab:blue", "linestyle": "-"},
    "CAM": {"color": "tab:orange", "linestyle": "--"},
    "LPwE": {"color": "tab:green", "linestyle": ":"},
}


def finite_number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def make_plot(rows, mean_field, ci_field, ylabel, title, headroom):
    figure, axis = plt.subplots(figsize=(8, 6))
    sizes, handles, top = set(), [], 0.0
    for algorithm, style in ALGORITHM_STYLES.items():
        points = []
        for row in rows:
            mean = finite_number(row[mean_field])
            if row["algorithm"] == algorithm and mean is not None:
                interval = finite_number(row[ci_field]) or 0.0
                points.append((int(row["identities"]), mean, interval))
        if not points:
            continue
        points.sort()
        x = [p[0] for p in points]
        y = [p[1] for p in points]

        lower = [min(p[2], 0.99 * p[1]) for p in points]
        upper = [p[2] for p in points]
        sizes.update(x)
        top = max(top, max(m + u for m, u in zip(y, upper)))
        bars = axis.errorbar(x, y, yerr=[lower, upper], label=algorithm, linewidth=2.5,
                             elinewidth=2, capsize=4, capthick=1.5, **style)
        bars.lines[0].set_label(algorithm)
        handles.append(bars.lines[0])

    axis.set_xscale("log")
    axis.set_yscale("log")
    if headroom > 1:
        axis.set_ylim(top=top * headroom)
    ticks = sorted(sizes)
    axis.xaxis.set_major_locator(FixedLocator(ticks))
    axis.xaxis.set_minor_locator(NullLocator())
    axis.set_xticklabels([f"{n:,}" for n in ticks])
    axis.set_xlabel("Number of Identities", fontsize=FONT_SIZE)
    axis.set_ylabel(ylabel, fontsize=FONT_SIZE)
    axis.set_title(title, fontsize=FONT_SIZE)
    axis.tick_params(axis="both", labelsize=TICK_FONT_SIZE)
    axis.grid(True, linestyle="--", linewidth=0.5)
    axis.legend(handles, [h.get_label() for h in handles], fontsize=LEGEND_FONT_SIZE,
                loc="upper left", handlelength=2.5)
    return figure


def main():
    path = config.RUN_DIR / "summary" / "summary.csv"
    if not path.exists():
        raise SystemExit("summary/summary.csv missing: run the summarize step first")
    with path.open(newline="", encoding="utf-8") as input_file:
        rows = list(csv.DictReader(input_file))

    output_directory = config.RUN_DIR / "figures"
    output_directory.mkdir(parents=True, exist_ok=True)
    for mean_field, ci_field, ylabel, title, headroom, filename in (
            ("mean_time_s", "time_s_ci95", "Time (s)", "Processing Time Comparison",
             10, "scalability_time"),
            ("mean_peak_memory_mib", "peak_memory_mib_ci95", "Memory (MiB)",
             "Peak Memory Comparison", 1, "scalability_memory")):
        figure = make_plot(rows, mean_field, ci_field, ylabel, title, headroom)
        figure.savefig(output_directory / f"{filename}.pdf", dpi=600, bbox_inches="tight")
        plt.close(figure)
        print(output_directory / f"{filename}.pdf")


if __name__ == "__main__":
    main()
