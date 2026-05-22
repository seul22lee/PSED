import json
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

# Load JSON data
json_path = "/home/ftk3187/github/PSED/0226_kb/extracted/Arts et al. - 2019 - Sticking probabilities of H2O and Al(CH3)3 during atomic layer deposition of Al2O3 extracted from th/extracted_data/figure-009.json"

with open(json_path, "r") as f:
    data = json.load(f)

metadata = data["metadata"]
series_data = data["data"]

# Color / style settings
styles = {
    "Ylilammi (2018)": {"color": "black",  "ls": "-",  "marker": "o", "ms": 5},
    "TMA-limited":     {"color": "#e6771e", "ls": "--", "marker": None, "ms": 0},
    "H2O-limited":     {"color": "#1f77b4", "ls": "-.", "marker": None, "ms": 0},
}

fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=True)

for ax, series in zip(axes, series_data):
    name   = series["series"]
    pts    = np.array(series["points"])
    x, y   = pts[:, 0], pts[:, 1]
    sty    = styles.get(name, {"color": "gray", "ls": "-", "marker": None, "ms": 0})

    ax.plot(
        x, y,
        color=sty["color"],
        linestyle=sty["ls"],
        marker=sty["marker"] if sty["marker"] else "",
        markersize=sty["ms"],
        linewidth=2,
        label=name,
    )

    # Mark theta = 1/2 point and draw linear fit through it
    # Find x where y ≈ 0.5
    half_idx = np.argmin(np.abs(y - 0.5))
    x_half, y_half = x[half_idx], y[half_idx]

    # Slope from two neighbouring points around theta=1/2
    if 0 < half_idx < len(x) - 1:
        slope = (y[half_idx + 1] - y[half_idx - 1]) / (x[half_idx + 1] - x[half_idx - 1])
    else:
        slope = (y[-1] - y[-2]) / (x[-1] - x[-2])

    # Linear fit line: y = slope*(x - x_half) + 0.5, clipped to [0,1]
    x_fit = np.linspace(x[0], x[-1], 500)
    y_fit = slope * (x_fit - x_half) + 0.5
    mask  = (y_fit >= 0) & (y_fit <= 1)
    ax.plot(x_fit[mask], y_fit[mask], color="red", linestyle=":", linewidth=1.5,
            label="Linear fit at θ=½")

    ax.axhline(0.5, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.axvline(x_half, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.scatter([x_half], [y_half], color="red", zorder=5, s=40)

    ax.set_title(name, fontsize=12, fontweight="bold")
    ax.set_xlabel(metadata["x_label"], fontsize=11)
    ax.set_xlim(left=0)
    ax.set_ylim(-0.02, 1.05)
    ax.yaxis.set_major_locator(ticker.MultipleLocator(0.2))
    ax.yaxis.set_minor_locator(ticker.MultipleLocator(0.1))
    ax.xaxis.set_minor_locator(ticker.AutoMinorLocator())
    ax.grid(True, which="major", alpha=0.3)
    ax.grid(True, which="minor", alpha=0.1)
    ax.legend(fontsize=9)

axes[0].set_ylabel(metadata["y_label"], fontsize=11)

fig.suptitle(
    "Normalized Al₂O₃ thickness vs. Distance/cavity height\n"
    "(Arts et al. 2019 – Figure 009)",
    fontsize=13, fontweight="bold", y=1.01
)

plt.tight_layout()
plt.savefig("/mnt/user-data/outputs/figure009.png", dpi=150, bbox_inches="tight")
print("Saved → /mnt/user-data/outputs/figure009.png")
plt.show()