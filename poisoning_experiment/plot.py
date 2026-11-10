import csv
import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.transforms import Bbox

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
    "GSP-X": {"color": "tab:blue", "linestyle": "-", "marker": "s"},
    "CAM": {"color": "tab:orange", "linestyle": "--", "marker": "^"},
    "LPwE": {"color": "tab:green", "linestyle": ":", "marker": "o"},
}


def load_summary(path):
    with path.open(newline="", encoding="utf-8") as input_file:
        rows = list(csv.DictReader(input_file))
    if not rows:
        raise ValueError(f"No rows were found in {path}.")
    return rows


def finite_number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def bounded_errors(means, intervals, lower_bound, upper_bound):
    lower_errors = []
    upper_errors = []
    for mean, interval in zip(means, intervals):
        lower_errors.append(min(interval, max(0.0, mean - lower_bound)))
        upper_errors.append(min(interval, max(0.0, upper_bound - mean)))
    return [lower_errors, upper_errors]


def make_plot(
    rows,
    mean_field,
    ci_field,
    ylabel,
    title,
    y_limits=(0.0, 1.05),
    value_scale=1.0,
    step_lines=False,
    legend_position="best",
    legend_anchor=None,
):
    figure, axis = plt.subplots(figsize=(8, 6))
    plotted = False
    plotted_x_values = set()

    for algorithm, style in ALGORITHM_STYLES.items():
        selected_rows = sorted(
            (row for row in rows if row["algorithm"] == algorithm),
            key=lambda row: float(row["poison_percentage"]),
        )
        if not selected_rows:
            continue
        algorithm_mean_field = (
            mean_field[algorithm]
            if isinstance(mean_field, dict)
            else mean_field
        )

        selected = []
        means = []
        for row in selected_rows:
            mean = finite_number(row.get(algorithm_mean_field))
            if mean is None:
                continue
            selected.append(row)
            means.append(value_scale * mean)
        if not selected:
            continue

        x_values = [float(row["poison_percentage"]) for row in selected]
        plotted_x_values.update(x_values)

        common_style = {
            "label": algorithm,
            "color": style["color"],
            "linestyle": style["linestyle"],
            "marker": style["marker"],
            "linewidth": 2.5,
            "markersize": 6,
        }

        if ci_field is None:
            if step_lines:
                axis.step(
                    x_values,
                    means,
                    where="post",
                    **common_style,
                )
            else:
                axis.plot(x_values, means, **common_style)
        else:
            algorithm_ci_field = (
                ci_field[algorithm]
                if isinstance(ci_field, dict)
                else ci_field
            )
            intervals = []
            for row in selected:
                interval = finite_number(row.get(algorithm_ci_field))
                intervals.append(value_scale * interval if interval is not None else 0.0)
            y_errors = bounded_errors(
                means,
                intervals,
                y_limits[0],
                min(y_limits[1], value_scale),
            )
            axis.errorbar(
                x_values,
                means,
                yerr=y_errors,
                elinewidth=2,
                capsize=3,
                capthick=1.5,
                **common_style,
            )
        plotted = True

    if not plotted:
        raise ValueError("No rows matched GSP-X, CAM, or LPwE.")

    axis.set_xlabel("Poisoned Identities (%)", fontsize=FONT_SIZE)
    axis.set_ylabel(ylabel, fontsize=FONT_SIZE)
    axis.set_title(title, fontsize=FONT_SIZE)
    axis.set_xticks(sorted(plotted_x_values))
    axis.tick_params(axis="both", labelsize=TICK_FONT_SIZE)
    axis.set_ylim(*y_limits)
    axis.grid(True, linestyle="--", linewidth=0.5)
    axis.legend(
        fontsize=LEGEND_FONT_SIZE,
        loc=legend_position,
        bbox_to_anchor=legend_anchor,
        handlelength=2.5,
        markerscale=1.5,
        borderpad=0.5,
        labelspacing=0.4,
    )
    return figure


def save_plots(plots, output_directory):
    bounding_boxes = []
    for figure, _ in plots:
        figure.canvas.draw()
        bounding_boxes.append(figure.get_tightbbox(figure.canvas.get_renderer()))


    shared_bounds = Bbox.union(bounding_boxes).padded(0.1)
    output_directory.mkdir(parents=True, exist_ok=True)
    for figure, filename in plots:
        figure.savefig(
            output_directory / f"{filename}.pdf",
            dpi=600,
            bbox_inches=shared_bounds.frozen(),
            pad_inches=0,
        )
        print(output_directory / f"{filename}.pdf")
    for figure, _ in plots:
        plt.close(figure)


def main():
    path = config.RUN_DIR / "summary" / "summary.csv"
    if not path.exists():
        raise SystemExit("summary/summary.csv missing: run the summarize step first")
    rows = load_summary(path)

    success_figure = make_plot(
        rows,
        mean_field="attack_success_rate",
        ci_field=None,
        ylabel="Attack Success (%)",
        title="Targeted Poisoning Attack",
        y_limits=(0.0, 105.0),
        value_scale=100.0,
        step_lines=False,
        legend_position="center left",
        legend_anchor=(0.22, 0.55),
    )

    f1_figure = make_plot(
        rows,
        mean_field={
            "GSP-X": "mean_f1",
            "CAM": "mean_f1",
            "LPwE": "mean_benign_f1",
        },
        ci_field={
            "GSP-X": "f1_ci95",
            "CAM": "f1_ci95",
            "LPwE": "benign_f1_ci95",
        },
        ylabel="F1 Score",
        title="F1 under Targeted Poisoning",
    )

    save_plots(
        [
            (success_figure, "poisoning_attack_success"),
            (f1_figure, "poisoning_f1"),
        ],
        config.RUN_DIR / "figures",
    )


if __name__ == "__main__":
    main()
