"""
saturation_model.py  (M4 — executable form of ontology model `yanguas_gil_saturation`)
--------------------------------------------------------------------------------------
The 0-D ALD saturation model from Yanguas-Gil 2026 (JVST A, doi 10.1116/6.0005313) —
the "simulated ALD tool" its reasoning-LLM agent optimizes. Growth-per-cycle as a
function of the precursor / coreactant dose times, for one or more first-order
Langmuir pathways, with an optional non-self-limited (CVD) component.

  self-limited (Eq. 7):
     GPC(t1,t2) = GPC0 · Σ_i f_i (1−e^{−k1_i t1})(1−e^{−k2_i t2}) / (1 − e^{−(k1_i+k2_i)})

  with a CVD background rate GR0 (Eq. 8): GPC keeps rising ~linearly with t1 and
  never saturates → the process is NOT self-limited.

Matches the ontology object's equations; this is to the saturation branch what
channel_model.py is to the conformality branch.
"""
import math
from dataclasses import dataclass, field


@dataclass
class Pathway:
    f: float            # weight (Σ f = 1)
    k1: float           # precursor uptake rate constant (1/s)
    k2: float           # coreactant uptake rate constant (1/s)


@dataclass
class SaturationModel:
    pathways: list = field(default_factory=lambda: [Pathway(1.0, 5.0, 4.0)])
    gpc0: float = 1.0                  # saturated growth per cycle (Å/cycle)
    gr0: float = 0.0                   # CVD (non-self-limited) asymptotic growth rate (Å/s); 0 = self-limited
    name: str = "fast/fast"
    model_id: str = "yanguas_gil_saturation"

    def gpc(self, t1, t2=1.0):
        """Growth per cycle at precursor dose t1, coreactant dose t2 (Eq. 7 + optional CVD)."""
        g = 0.0
        for p in self.pathways:
            num = (1 - math.exp(-p.k1 * t1)) * (1 - math.exp(-p.k2 * t2))
            den = 1 - math.exp(-(p.k1 + p.k2))
            g += p.f * num / den
        g *= self.gpc0
        if self.gr0 > 0:               # non-self-limited: a CVD term linear in dose
            g += self.gr0 * t1
        return g

    @property
    def self_limited(self):
        return self.gr0 <= 0

    @property
    def gpc_sat(self):
        """The saturated GPC: the self-limited asymptote at long doses (Eq. 7 with
        t1,t2→∞ gives gpc0·Σ f_i/(1−e^{−(k1_i+k2_i)}), NOT simply gpc0)."""
        return self.gpc0 * sum(p.f / (1 - math.exp(-(p.k1 + p.k2))) for p in self.pathways)


# the benchmark processes (Yanguas-Gil 2026, Table I)
BENCHMARK = {
    "fast/fast":      SaturationModel([Pathway(1.0, 5.0, 4.0)], 1.0, name="fast/fast"),
    "slow/slow":      SaturationModel([Pathway(1.0, 1.0, 1.2)], 1.0, name="slow/slow"),
    "slow/fast":      SaturationModel([Pathway(1.0, 1.0, 4.0)], 1.0, name="slow/fast"),
    "fast/fast thin": SaturationModel([Pathway(1.0, 5.0, 4.0)], 0.3, name="fast/fast thin"),
    "soft/fast":      SaturationModel([Pathway(0.8, 5.0, 4.0), Pathway(0.2, 1.0, 4.0)], 1.0, name="soft/fast"),
    # a non-self-limited variant (CVD component) — what the agent must FLAG, not optimize
    "fast/fast +CVD": SaturationModel([Pathway(1.0, 5.0, 4.0)], 1.0, gr0=0.05, name="fast/fast +CVD"),
}


if __name__ == "__main__":
    print("Yanguas-Gil saturation model — GPC(t1, t2=1s) for the benchmark processes:")
    for name, m in BENCHMARK.items():
        curve = "  ".join(f"{m.gpc(t):.2f}" for t in (0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 4.0))
        print(f"  {name:16} self_limited={str(m.self_limited):5}  GPC@[.05,.1,.2,.5,1,2,4]s = {curve}")
