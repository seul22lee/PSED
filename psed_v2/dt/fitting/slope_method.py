"""ADDED (A3): Arts et al. slope method on KB profiles: |d theta / d x~| at the front, x~ = x/H, theta = s/s_plateau;
c = 13.9 * slope^2 (Arts 2019 eq. 3, as used by yim20). Slope = linear fit through points with 0.2 <= theta <= 0.8."""
import json, os, numpy as np
KB = os.environ.get("PSED_KB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "kb"))
def slope_c(P, H, plateau=None):
    P = P[P[:, 0] >= 0]
    pl = plateau if plateau else float(np.mean(P[P[:, 0] <= 25, 1])) if (P[:, 0] <= 25).sum() else float(P[:, 1].max())
    th = P[:, 1] / pl; xt = P[:, 0] * 1e-6 / H
    i_front = np.argmax(th < 0.5)                          # first crossing of 0.5
    m = (th >= 0.2) & (th <= 0.8) & (np.abs(np.arange(len(th)) - i_front) <= 6)
    if m.sum() < 2: return np.nan, int(m.sum())
    k = np.polyfit(xt[m], th[m], 1)[0]
    return 13.9 * k ** 2, int(m.sum())
rows = [("yim20", "10.1039_d0cp03358h", cid, H, pl) for cid, H, pl in [
        ("yim20:fig8b#c1", 500e-9, None), ("yim20:fig8b#c2", 500e-9, None), ("yim20:fig8b#c3", 500e-9, None), ("yim20:fig8b#c4", 500e-9, None),
        ("yim20:fig9a#c1", 100e-9, None), ("yim20:fig9a#c2", 500e-9, None), ("yim20:fig9a#c3", 2000e-9, None),
        ("yim20:fig9d#c1", 500e-9, None), ("yim20:fig9d#c2", 500e-9, None), ("yim20:fig9d#c3", 500e-9, None),
        ("yim20:fig11a#c1", 500e-9, 53.5), ("yim20:fig11a#c2", 500e-9, 53.5), ("yim20:fig11a#c3", 500e-9, None)]] + \
       [("gao15", "10.1116_1.4903941", "gao15:fig5a#c1", 500e-9, 108.0), ("yli18", "10.1063_1.5028178", "yli18:fig6#c2", 500e-9, None)]
cache = {}
for paper, doi, cid, H, pl in rows:
    if doi not in cache: cache[doi] = {c["id"]: np.array(c["points"]) for c in json.load(open(f"{KB}/{doi}.figures.json"))["curves"]}
    c, n = slope_c(cache[doi][cid], H, pl)
    print(f"{cid:18s} H={H*1e9:5.0f} nm  points in front fit: {n:2d}  ->  c = {c:.2e}")
print("yim20 Table 1 slopes (paper, raw data): s2 0.011, s4 0.019, s8 0.019, s12 0.021 -> c = 13.9*slope^2 =",
      [f"{13.9*s*s:.1e}" for s in (0.011, 0.019, 0.019, 0.021)], "; paper mean 4e-3")
