import os, sys, json, numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(__file__))
from fit_lateral import load, plateau_gpc, model_curve
D = os.path.dirname(__file__); KB = os.environ.get("PSED_KB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "kb"))
SURF='#fcfcfb'; INK='#0b0b0b'; INK2='#52514e'; MUTED='#898781'; GRID='#e1e0d9'; AX='#c3c2b7'; BLUE='#2a78d6'; ORANGE='#eb6834'; AQUA='#1baf7a'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.edgecolor':AX,'axes.labelcolor':INK2,'xtick.color':MUTED,'ytick.color':MUTED,
  'axes.grid':True,'grid.color':GRID,'grid.linewidth':0.6,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':SURF,'axes.facecolor':SURF,
  'axes.titlesize':9.5,'axes.titleweight':'bold','axes.titlecolor':INK,'axes.titlelocation':'left','legend.frameon':False,'legend.fontsize':8.5})
# ---------- yim20 ----------
C = load(f"{KB}/10.1039_d0cp03358h.figures.json")
common = dict(L=1e-3, W=0.1e-3, T=573.15, K=219.0, rho=3100.0, M_film=101.96, b_film=2, MA=72.09, dA=591e-12, MB=28.0, dB=374e-12, pB=300.0)
fr = json.load(open(f"{D}/yim20_fit.json"))
sets = [("blind fit: c=%.4f, pA0=%.0f Pa" % (fr["c"], fr["pA0"]), fr["c"], fr["pA0"], BLUE),
        ("yim20 own inputs: c=0.012, pA0=65 Pa", 0.012, 65.0, ORANGE)]
cur = [("yim20:fig9a#c1", 100e-9, 500, 0.1, "Fig. 9a  H 100 nm"), ("yim20:fig9a#c2", 500e-9, 500, 0.1, "Fig. 9a  H 500 nm"),
       ("yim20:fig9a#c3", 2000e-9, 500, 0.1, "Fig. 9a  H 2000 nm"), ("yim20:fig9d#c1", 500e-9, 250, 0.1, "Fig. 9d  250 cycles"),
       ("yim20:fig9d#c3", 500e-9, 1000, 0.1, "Fig. 9d  1000 cycles"), ("yim20:fig9d#c2", 500e-9, 500, 0.1, "Fig. 9d  500 cycles"),
       ("yim20:fig11a#c2", 500e-9, 500, 0.2, "HELD OUT  Fig. 11a pulse 0.2 s"), ("yim20:fig11a#c3", 500e-9, 500, 0.4, "HELD OUT  Fig. 11a pulse 0.4 s")]
fig, axs = plt.subplots(2, 4, figsize=(15, 6.4), constrained_layout=True)
xx = np.linspace(0, 400, 801)
for ax, (cid, H, N, tp, title) in zip(axs.flat, cur):
    P = np.array(C[cid]["points"]); P = P[P[:, 0] >= 0]
    gpc = 0.107e-9 if P[:, 0].min() > 25 else plateau_gpc(P, N)
    s = dict(id=cid, H=H, N=N, t_pulse=tp, gpc=gpc)
    ax.plot(P[:, 0], P[:, 1], 'o', ms=4, color=MUTED, label='measured (KB)')
    rm = []
    for lab, c, p, col in sets:
        ax.plot(xx, model_curve(s, c, p, common, xx), color=col, lw=1.8, label=lab)
        rm.append(np.sqrt(np.mean((model_curve(s, c, p, common, P[:, 0]) - P[:, 1]) ** 2)))
    ax.set_title(f"{title}\nRMSE  blind {rm[0]:.1f} nm · yim20 {rm[1]:.1f} nm", color=INK if 'HELD' not in title else ORANGE)
    ax.set(xlim=(0, 400 if H > 1e-6 or tp > 0.3 else 220), ylim=(0, 1.15 * max(P[:, 1].max(), 10)), xlabel='x (µm)', ylabel='thickness (nm)')
axs[0, 0].legend(loc='upper right')
fig.suptitle('yim20 blind fit: c and pA0 fitted to 6 measured profiles (top row + bottom-left), 2 pulse-time profiles held out', x=0.005, ha='left', fontsize=11, fontweight='bold', color=INK)
fig.savefig(f"{D}/yim20_fit.png", dpi=140)
# ---------- profile scan ----------
prof = json.load(open(f"{D}/yim20_profile.json"))
cs = np.array([r["c"] for r in prof]); sse = np.array([r["sse"] for r in prof]); pp = np.array([r["pA0"] for r in prof])
fig, ax = plt.subplots(1, 2, figsize=(11, 3.8), constrained_layout=True)
ax[0].plot(cs, sse, '-o', color=BLUE, lw=1.8, ms=5); ax[0].set_xscale('log')
for v, lab, col in [(fr["c"], 'blind fit', BLUE), (0.012, 'yim20 input', ORANGE), (0.00572, 'yli18 (other paper)', MUTED)]:
    ax[0].axvline(v, color=col, ls=':', lw=1.2); ax[0].annotate(lab, (v, sse.max()), rotation=90, va='top', ha='right', fontsize=8, color=INK2)
ax[0].set(xlabel='sticking coefficient c (fixed)', ylabel='sum of per-curve MSE (nm²), pA0 re-fitted'); ax[0].set_title('(a) misfit vs c: flat over ~an order of magnitude')
ax[1].plot(cs, pp, '-o', color=BLUE, lw=1.8, ms=5); ax[1].set_xscale('log'); ax[1].axhline(65, color=ORANGE, ls=':', lw=1.2)
ax[1].annotate('yim20 input 65 Pa', (cs[0], 65), xytext=(4, 4), textcoords='offset points', fontsize=8, color=INK2)
ax[1].set(xlabel='sticking coefficient c (fixed)', ylabel='best-fit pA0 (Pa)', ylim=(0, max(pp.max() * 1.2, 100))); ax[1].set_title('(b) best pA0 for each c: stays near 60–80 Pa')
fig.savefig(f"{D}/yim20_profile.png", dpi=140)
# ---------- gao15 ----------
G = load(f"{KB}/10.1116_1.4903941.figures.json"); P = np.array(G["gao15:fig5a#c1"]["points"])
gc = dict(common, pB=150.0); gf = json.load(open(f"{D}/gao15_fit.json"))
spec = dict(id="g", H=500e-9, N=1109, t_pulse=0.1, gpc=plateau_gpc(P, 1109, x_max_um=45))
fig, ax = plt.subplots(1, 2, figsize=(12, 4.2), constrained_layout=True, gridspec_kw=dict(width_ratios=[1.3, 1]))
ax[0].plot(P[:, 0], P[:, 1], 'o', ms=4.5, color=MUTED, label='measured, Fig. 5a (KB)')
labs = {"a_all": ("fit c, pA0 (all points)", BLUE), "a_cut": ("fit c, pA0 (x ≤ 85 µm)", AQUA), "b_cut": ("pA0 copied from yim20 fit", ORANGE)}
x2 = np.linspace(0, 160, 641)
for k, (lab, col) in labs.items():
    c, p = gf[k]; ax[0].plot(x2, model_curve(spec, c, p, gc, x2), color=col, lw=1.8, label=f"{lab}: c={c:.2g}, pA0={p:.0f} Pa")
ax[0].axvline(85, color=INK2, ls=':', lw=1); ax[0].set(xlim=(0, 160), ylim=(0, 125), xlabel='x (µm)', ylabel='thickness (nm)')
ax[0].set_title('(a) gao15 Fig. 5a, Al₂O₃ 300 °C, 500 nm gap, 1109 cycles — no c reported'); ax[0].legend(loc='lower left')
obs = {200: 25, 500: 90, 1000: 155}; N50 = int(round(50e-9 / spec["gpc"])); xx = np.linspace(0, 400, 1601)
Hs = list(obs); xpos = np.arange(len(Hs)); w = 0.2
ax[1].bar(xpos - 1.5 * w, [obs[h] for h in Hs], w, color=INK2, label='observed (text, Fig. 3)')
for j, (k, (lab, col)) in enumerate(labs.items()):
    c, p = gf[k]; vals = []
    for h in Hs:
        m = model_curve(dict(id='p', H=h * 1e-9, N=N50, t_pulse=0.1, gpc=spec["gpc"]), c, p, gc, xx); vals.append(xx[np.argmax(m < 5.0)])
    ax[1].bar(xpos + (j - 0.5) * w, vals, w, color=col, label=lab)
ax[1].set_xticks(xpos, [f"{h} nm gap" for h in Hs]); ax[1].set(ylabel='film end (µm), thickness < 5 nm'); ax[1].grid(axis='x', visible=False)
ax[1].set_title(f'(b) HELD OUT: film ends of ~50 nm films ({N50} cycles)'); ax[1].legend(loc='upper left')
fig.savefig(f"{D}/gao15_fit.png", dpi=140); print("ok")
