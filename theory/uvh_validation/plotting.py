"""Manuscript-ready population-error contours from signed P1 - 1/2 grids."""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
# Type 42 embeds editable TrueType fonts in exported PDF/PS figures.
plt.rcParams.update({
    "font.family": "STIXGeneral",
    "mathtext.fontset": "stix",
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "svg.fonttype": "none",
})


LEVELS = np.logspace(-6, -1, 6)
COLORS = ("#9467bd", "#ff7f0e","#1f77b4", "#d62728", "#2ca02c", "#17becf")

LINESTYLES = (
    "solid",
    (0, (6, 2)),
    (0, (1, 1.6)),
    (0, (5, 1.5, 1, 1.5)),
    (0, (2.4, 1.4)),
    (0, (6, 1.5, 1, 1.5, 1, 1.5)),
)


def contour_figure(detuning, amplitude, panels, nrows, title=None,
                   column_titles=None, xlabel=r"Detuning $\Delta/\Omega_0$",
                   legend_panel=0, legend_loc="lower right"):
    panels = list(panels)
    if len(panels) != 2 * nrows:
        raise ValueError(f"Expected {2 * nrows} panels, got {len(panels)}")
    if not 0 <= legend_panel < len(panels):
        raise ValueError("legend_panel must index one of the panels")

    fig, axes = plt.subplots(nrows, 2, squeeze=False, sharex=True, sharey=True,
                             figsize=(7.1, 2.95 * nrows + 0.35),
                             layout="constrained")
    for ax, (label, values) in zip(axes.flat, panels, strict=True):
        residual = np.asarray(values)
        if residual.shape != (len(amplitude), len(detuning)):
            raise ValueError(f"{label}: residual grid has shape {residual.shape}")
        if not np.isfinite(residual).all():
            raise ValueError(f"{label}: residual grid has nonfinite values")

        low, high = np.min(residual), np.max(residual)
        for level, color, dash in zip(LEVELS, COLORS, LINESTYLES, strict=True):
            # Use signed contours: abs(residual) on a sampled grid can erase
            # thin bands around a zero crossing during interpolation.
            signed = [v for v in (-level, level) if low < v < high]
            if signed:
                ax.contour(detuning, amplitude, residual, levels=signed,
                           colors=[color], linestyles=[dash], linewidths=1.15)

        ax.text(.035, .965, label, transform=ax.transAxes,
                va="top", ha="left", fontsize=14., fontweight="semibold",
                bbox=dict(facecolor="white", edgecolor="none", alpha=.9,
                          pad=1.5))
        ax.set(xlim=(-.2, .2), ylim=(.8, 1.2),
               xticks=np.linspace(-.2, .2, 5),
               yticks=np.linspace(.8, 1.2, 5))
        ax.set_box_aspect(.88)
        ax.minorticks_on()
        ax.tick_params(which="major", direction="in", top=True, right=True,
                       labelbottom=True, labelleft=True, labelsize=12,
                       length=3.5, width=.7)
        ax.tick_params(which="minor", direction="in", top=True, right=True,
                       length=1.8, width=.5)

    for ax in axes[:, 0]:
        ax.set_ylabel(r"Rabi frequency $\Omega/\Omega_0$", fontsize=15.)
    for ax in axes[-1, :]:
        ax.set_xlabel(xlabel, fontsize=15)

    handles = [Line2D([], [], color=color, linestyle=dash, linewidth=1.3,
                      label=rf"$10^{{{int(np.log10(level))}}}$")
               for level, color, dash in zip(LEVELS, COLORS, LINESTYLES,
                                             strict=True)]
    axes.flat[legend_panel].legend(
        handles=handles,
        loc=legend_loc, ncol=3, fontsize=12., title_fontsize=1.,
        handlelength=2.3, handletextpad=.45, columnspacing=.8,
        labelspacing=.15, borderpad=.3, frameon=True,
        facecolor="white", edgecolor=".65", framealpha=.97,
    )
    return fig


def save_figure(fig, output_dir, stem):
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_dir / f"{stem}.png", dpi=180, bbox_inches="tight")
    fig.savefig(output_dir / f"{stem}.pdf", bbox_inches="tight")
