"""ADDED (F2): paper figure - knowledge base <-> digital twin <-> reactor, concept + results (A4, A5, A6).
Reads fitting/campaign_groupA.json, fitting/campaign_ticl4_K.json, demo/dt_recipe_correction.json, demo/dt_qcm_calibration.json."""
import os, sys, json, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Ellipse
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
plt.rcParams.update({"font.size": 8.5, "axes.titlesize": 9, "axes.labelsize": 8.5, "legend.fontsize": 7.2, "xtick.labelsize": 7.8,
                     "ytick.labelsize": 7.8, "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.6,
                     "font.family": "DejaVu Sans", "pdf.fonttype": 42})
C1, C2, C3, GR, INK, INK2 = "#2a78d6", "#eb6834", "#1baf7a", "#8a8984", "#0b0b0b", "#52514e"
A4 = {o["curve"]: o for o in json.load(open(f"{root}/fitting/campaign_groupA.json"))}
TI = {o["curve"]: o for o in json.load(open(f"{root}/fitting/campaign_ticl4_K.json"))}
A5 = json.load(open(f"{root}/demo/dt_recipe_correction.json")); A6 = json.load(open(f"{root}/demo/dt_qcm_doseseries.json"))   # A11: dose series
g = {"__file__": f"{root}/fitting/campaign_groupA.py"}; exec(open(g["__file__"]).read().split("out = []")[0], g)
ROW = {r[3]: r for r in g["ROWS"]}


fig = plt.figure(figsize=(9.4, 6.6))
go = fig.add_gridspec(2, 1, height_ratios=[1.3, 2.0], hspace=0.15, left=0.065, right=0.99, top=0.985, bottom=0.1)
gr = go[1].subgridspec(2, 3, hspace=0.62, wspace=0.27)

# ---------------- (a) concept ----------------
ax = fig.add_subplot(go[0]); ax.set_xlim(0, 100); ax.set_ylim(0, 60); ax.axis("off")
def box(x, y, w, h, title, sub, fc, ec):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2", fc=fc, ec=ec, lw=1.0))
    ax.text(x + w / 2, y + h * 0.7, title, ha="center", va="center", fontsize=10.6, weight="bold", color=INK)
    ax.text(x + w / 2, y + h * 0.3, sub, ha="center", va="center", fontsize=8.5, color=INK2, linespacing=1.35)
def num(x, y, n, col=INK):
    bb = ax.get_position(); wi, hi = bb.width * fig.get_figwidth(), bb.height * fig.get_figheight(); r = 0.065
    ax.add_patch(Ellipse((x, y), 2 * r * 100 / wi, 2 * r * 60 / hi, fc="white", ec=col, lw=1.0)); ax.text(x, y - 0.05, str(n), ha="center", va="center", fontsize=8.8, weight="bold", color=col)
def arrow(x0, y0, x1, y1, col=INK, ls="-", lw=1.0, ms=9):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=ms, lw=lw, color=col, linestyle=ls))
def link(y, n, label, col, x0, x1, ls="-"):
    d = 1 if x1 > x0 else -1
    num(x0 + d * 1.5, y, n, col); arrow(x0 + d * 2.8, y, x1, y, col, ls=ls)
    ax.text((x0 + d * 2.8 + x1) / 2, y + 0.7, label, ha="center", va="bottom", fontsize=6.8, color=INK2, family="DejaVu Sans Mono")
# user input
ax.add_patch(FancyBboxPatch((14, 47.8), 72, 11.0, boxstyle="round,pad=0.4,rounding_size=1.2", fc="#f4f4f2", ec="#3a3a38", lw=1.1))
ax.text(15.2, 53.3, "User input", ha="left", va="center", fontsize=8.8, weight="bold", color=INK)
ax.text(52.5, 53.3, "“Coat a 500 nm lateral gap (AR 200) with Al$_2$O$_3$ (TMA/H$_2$O, 300 °C)\nso that the film reaches 100 µm — in our reactor B.”", ha="center", va="center", fontsize=9.2, style="italic", color=INK, linespacing=1.2)
arrow(50, 47.3, 50, 43.8, INK, lw=0.9)
# agent
ax.add_patch(FancyBboxPatch((1, 34.5), 98, 8.6, boxstyle="round,pad=0.4,rounding_size=1.2", fc="#ffffff", ec="#3a3a38", lw=1.0))
ax.text(2.2, 38.8, "Agent", ha="left", va="center", fontsize=9.4, weight="bold", color=INK)
ax.text(54, 38.8, "plans steps 1–5 and calls tools (query · retrieve · compare · calibrate · design · write);\nevery number comes from the knowledge base or a model output",
        ha="center", va="center", fontsize=8.8, color=INK, linespacing=1.25)
for xc in (12.5, 50.5, 89):   # agent orchestrates each component
    arrow(xc, 34.0, xc, 30.8, GR, lw=0.8, ms=7)
box(1, 1, 22, 29, "Knowledge base", "reported c, K · profiles\nmodel cards", "#f7f7f5", "#3a3a38")
box(37.5, 1, 26, 29, "Digital twin", "reactor transport\nflat sample (QCM) · HAR channel", "#ececea", "#3a3a38")
box(79, 1, 20, 29, "Reactor B", "recipe · QCM\ntest chip", "#f7f7f5", "#3a3a38")
link(26.5, 1, "query(model)", INK2, 23.8, 37.2)
link(19, 2, "retrieve(c, K)", INK2, 23.8, 37.2)
link(11.5, 3, "compare(profiles)", INK2, 23.8, 37.2, ls="--")
link(4, 5, "write(fit)", INK2, 37.2, 23.8)
link(21, 4, "run(recipe)", INK2, 64.3, 78.6)
link(9.5, 4, "measure(QCM)", INK2, 78.6, 64.3)
ax.text(-1.5, 60, "a", fontsize=11, weight="bold", va="top")

def tag(a, letter, step, title):
    a.set_title(f"step {step} · {title}", loc="left", pad=3)
    a.text(-0.02, 1.08, letter, transform=a.transAxes, fontsize=11, weight="bold", va="bottom", ha="right")

# ---------------- (b) model selection ----------------
am = fig.add_subplot(gr[0, 0]); am.set_xlim(0, 1); am.set_ylim(0, 1); am.axis("off")
am.text(0.0, 0.93, "query:  lateral channel · thermal · TMA/H$_2$O", fontsize=7.8, color=INK, va="center",
        bbox=dict(boxstyle="round,pad=0.3", fc="#f1f0ec", ec="#c9c8c2", lw=0.5))
cards = [("diffusion–reaction (yli18)", "lateral channel", "thermal", True, ""),
         ("radical recombination (art19)", "lateral channel", "plasma", False, "ext."),
         ("pore diffusion (ela03)", "cyl. pore", "thermal", False, "ext."),
         ("flat-surface saturation", "planar", "thermal", False, "")]
for i, (name, st, pm, sel, ext) in enumerate(cards):
    y = 0.74 - i * 0.215
    if sel: am.add_patch(FancyBboxPatch((-0.02, y - 0.14), 1.04, 0.19, boxstyle="round,pad=0.005,rounding_size=0.02", fc="#ececea", ec="#3a3a38", lw=0.8))
    am.text(0.0, y, ("✓ " if sel else "✗ ") + name + (f"  [{ext}]" if ext else ""), fontsize=7.4, va="center", color=INK if sel else GR, weight="bold" if sel else "normal")
    am.text(0.06, y - 0.085, st, fontsize=7.0, va="center", color=INK if st == "lateral channel" else GR, style="normal" if st == "lateral channel" else "italic")
    am.text(0.55, y - 0.085, pm, fontsize=7.0, va="center", color=INK if pm == "thermal" else GR, style="normal" if pm == "thermal" else "italic")
tag(am, "b", 1, "Model selection")

# ---------------- (b) priors: c from KB vs fits ----------------
ab = fig.add_subplot(gr[0, 1])
groups = [("yli18\nTMA", ["yli18:fig6#c2"], 5.72e-3), ("yim20\nTMA", [k for k in A4 if k.startswith("yim20") and A4[k]["species"] == "TMA"], 4e-3),
          ("gao15\nTMA", ["gao15:fig5a#c1"], None), ("yim20\nH$_2$O", ["yim20:fig11a#c3"], 3e-4)]
for i, (lab, keys, rep) in enumerate(groups):
    y = len(groups) - 1 - i
    js = np.array([A4[k]["c_joint"] for k in keys]); sl = np.array([A4[k]["c_slope"] for k in keys])
    jitter = np.linspace(-0.18, 0.18, len(keys)) if len(keys) > 1 else [0]
    ab.scatter(js, y + np.array(jitter), s=9, color=C2, zorder=3, lw=0, label="profile fit (this work)" if i == 0 else None)
    ab.scatter(sl, y + np.array(jitter) - 0.0, s=11, facecolor="none", edgecolor=C3, lw=0.8, zorder=3, label="slope method (this work)" if i == 0 else None)
    if rep: ab.scatter([rep], [y], marker="D", s=20, color=C1, zorder=4, label="reported (KB)" if i == 0 else None)
    else: ab.text(3.2e-3, y, "  none reported", fontsize=6.9, color=INK2, va="center")
ab.set_xscale("log"); ab.set_xlim(5e-5, 4e-2); ab.set_yticks(range(len(groups)), [gl[0] for gl in groups][::-1]); ab.set_ylim(-0.6, len(groups) + 0.5)
ab.set_xlabel("lumped sticking coefficient c"); ab.grid(axis="x", color="#e4e3df", lw=0.5); ab.legend(loc="upper left", frameon=False, handletextpad=0.2, borderaxespad=0.1, fontsize=6.8)
k_y = TI["yli18:fig7#c2"]["K"]; # TiCl4 (K identifiable, c not) is stated in the caption
tag(ab, "c", 2, "Priors from the KB")


# ---------------- (d) validation ----------------
ac = fig.add_subplot(gr[0, 2])
for key, col, lab in (("yli18:fig6#c2", C1, "yli18"), ("yim20:fig9d#c3", C2, "yim20"), ("gao15:fig5a#c1", C3, "gao15")):
    r = ROW[key]; P, pl = g["prep"](r); o = A4[key]; x = np.linspace(0, P[:, 0].max() * 1.03, 200)
    ac.plot(P[:, 0], P[:, 1], "o", ms=2.0, mfc="white", mec=col, mew=0.6)
    ac.plot(x, g["model"](r, o["c_joint"], o["pA0_joint"], x, pl), "-", color=col, lw=1.3, label=f"{lab}  ({o['rmse_joint']:.1f} nm)")
ac.set_xlabel("depth in 500 nm gap (µm)"); ac.set_ylabel("thickness (nm)"); ac.set_xlim(0, 200); ac.set_ylim(0, 128)
ac.legend(loc="upper right", frameon=False, fontsize=6.8, title="paper (RMSE)", title_fontsize=6.8)
ac.text(0.02, 0.04, "○ digitized (KB)\n— fitted model", transform=ac.transAxes, fontsize=6.8, color=INK2)
tag(ac, "d", 3, "Check vs. reported")

# ---------------- (e) calibration (QCM dose series, mass units) ----------------
ad = fig.add_subplot(gr[1, 0])
f0 = [f for f in A6["fits"] if abs(f["c_assumed"] - 4e-3) < 1e-9][0]
ad.errorbar(A6["pulses"], A6["meas"], yerr=A6["sigma"], fmt="o", ms=3.2, mfc="white", mec=INK, ecolor=INK, elinewidth=0.6, capsize=1.5, label="QCM Δm (synthetic)")
ad.plot(f0["curve_t"], f0["curve_m"], "-", color=C2, lw=1.4, label="twin fit (c from KB)")
ad.axhline(A6["m_sat"], color=GR, lw=0.6, ls=":"); ad.text(0.055, A6["m_sat"] + 2, f"saturated step {A6['m_sat']:.0f} ng/cm² (WALDO QCM)", fontsize=6.6, color=INK2, va="bottom")
ad.set_xscale("log"); ad.set_xlim(0.05, 6); ad.set_ylim(0, 1.25 * A6["m_sat"])
ad.set_xlabel("TMA pulse length (s)"); ad.set_ylabel("Δm$_{TMA}$ (ng/cm²)")
ad.legend(loc="upper left", bbox_to_anchor=(0.0, 0.84), frameon=False, fontsize=6.6)
ad.text(0.97, 0.05, "η = %.2f (true 0.6)\nβ$_{wall}$ = %.1e (true 2e-3)" % (f0["eta"], f0["beta_wall"]), transform=ad.transAxes, ha="right", va="bottom", fontsize=6.9, color=INK2)
tag(ad, "e", 4, "Calibrate twin")

# ---------------- (f) control ----------------
ae = fig.add_subplot(gr[1, 1])
lines = ((A5["check_A"], GR, "-", "A, tuned in A"), (A5["check_same recipe"], C2, "--", "B, same recipe"), (A6["check"], C1, "-", "B, twin-corrected"))
for d, col, ls, lab in lines:
    ae.plot(d["x"], d["theta"], ls, color=col, lw=1.5, label=f"{lab}\n{d['tp']:.2f} s → {d['front']:.0f} µm")
ae.axvline(100, color=INK, lw=0.6, ls=":"); ae.text(100, 1.04, "target", fontsize=6.9, color=INK2, ha="center", va="bottom")
ae.set_xlim(0, 200); ae.set_ylim(-0.03, 1.12); ae.set_xlabel("depth in 500 nm gap (µm)"); ae.set_ylabel("coverage θ after one pulse")
ae.legend(loc="upper left", bbox_to_anchor=(0.53, 0.97), frameon=False, fontsize=6.6, handlelength=1.3, handletextpad=0.4, labelspacing=0.5)
tag(ae, "f", 4, "Correct recipe")

# ---------------- (g) prior quality ----------------
af = fig.add_subplot(gr[1, 2])
fs = sorted(A6["fits"], key=lambda f: f["c_assumed"]); xs = np.arange(len(fs))
af.bar(xs, [f["front_full"] for f in fs], color=[GR, C2, GR], width=0.62)
verdict = ["near target" if abs(f["front_full"] - 100) <= 10 else ("too shallow" if f["front_full"] < 100 else "too deep") for f in fs]
for i, f in enumerate(fs):
    af.text(i, f["front_full"] + 3, f"{f['front_full']:.0f} µm", ha="center", va="bottom", fontsize=7.2, color=INK)
    af.text(i, f["front_full"] / 2, verdict[i].replace(" ", "\n"), ha="center", va="center", fontsize=7.0, color="white", weight="bold", linespacing=1.0)
af.axhline(100, color=INK, lw=0.6, ls=":"); af.set_xticks(xs, [f"c = ½×\n{fs[0]['tp']:.2f} s", f"c true\n{fs[1]['tp']:.2f} s", f"c = 2×\n{fs[2]['tp']:.2f} s"])
af.set_xlabel("c given to the twin → recipe (pulse)"); af.set_ylabel("front reached in B (µm)"); af.set_ylim(0, 1.15 * max(f["front_full"] for f in fs))
tag(af, "g", 5, "Prior sets accuracy")

for ext in ("pdf", "png"): fig.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)), f"fig_dt_kb_control.{ext}"), dpi=220)
print("saved")
