# Desorption: WALDO 7/02 evidence, proposed model terms, identifiability

Status (2026-10-27):
- This is analysis and a proposal. `reaction_model.py` is unchanged.
- The proposed terms S1–S3 (section 5) are not implemented. They wait for the user's approval.
- When they are implemented, each will be one CHANGELOG row and one commit, on top of Larry's model.

Motivation: the WALDO QCM is to be used for real-time control, and the current model has no desorption.
Larry's FlatModel and the reactor walls are irreversible, and the C11 wall reservoir is linear and off by default.

## 1. Data and scripts

The collaborator data are not in the repository. Each script reads paths from environment variables:

| variable | file | columns |
|---|---|---|
| `WALDO_PRESSURE` | 7/02 pressure log | time s, exhaust pressure Torr |
| `WALDO_QCM` | 7/02 QCM log | time s, areal mass ng/cm² |
| `WALDO_TEMP` | 7/02 temperature log | time s, setpoint, reading °C |
| `WALDO_PERCYCLE_REF` (optional) | per-cycle Δm from another analysis, one value per line | ng/cm² |

| script | CHANGELOG | what it does | outputs |
|---|---|---|---|
| `fitting/waldo_cycles.py` | A12 | Finds the doses from the pressure spikes and computes the per-cycle QCM Δm; optional comparison with a reference list. | prints only |
| `fitting/waldo_purge_decay.py` | A13 | Cycle shape, fits of each purge, per-block losses, artifact checks, exhaust tail. | `waldo_purge_decay.json/.png` (git-ignored: collaborator data) |
| `fitting/qcm_sticky_identifiability.py` | A14 | Fisher identifiability of the QCM model with the sticky-precursor term. No data needed. | `qcm_sticky_identifiability.json` |

Run WALDO 7/02: 50 cycles of TMA 0.1 s, purge 60 s, H2O 1 s, purge 60 s at 100 °C (1.41 Torr, 120 sccm),
followed by 200 pump/hold/purge cycles.

## 2. Per-cycle Δm check (A12)

This checks the per-cycle verification summary (`Summary_PerCycle_Verification.pdf`, not in the repository) against the raw data.

Method:
- The doses are the pressure spikes: 50 TMA spikes of about 160 mTorr and 50 H2O spikes of about 70 mTorr.
  The first TMA onset is at 30.6 s; the period is 121.2 s (range 121.0–121.4).
- The QCM rises 1.0 s before the exhaust-gauge onset. The gauge is downstream of the sample, and there may also be a clock offset.
- A cycle boundary is the QCM value 2.8 s before the TMA onset, on the flat end of the H2O purge.

Result:
- Mean Δm 73.3 ng/cm² vs 73.1 ng/cm² in the summary.
- Mean |difference| 1.6 ng/cm² over cycles 1–49 (maximum 6.2). The QCM step is 2.1 ng/cm².
- Cycle 50: +4.3 ng/cm². This script ends the last cycle at the end of its purge.
- Boundaries at nominal times (30 + k·121.1 s) do not reproduce cycles 1–3 and 6. The summary's boundaries follow the pressure spikes.
- Δm per cycle roughly doubles over the run: mean 42 ng/cm² for cycles 1–10, 86 ng/cm² for cycles 21–50.

## 3. The QCM during the purges (A13)

Each cycle is aligned on the QCM rise of its TMA dose. The tables use the mean of cycles 21–49. Each purge is fitted
from the peak to 1 s before the next dose with m(t) = m_inf + A_fast·e^(−t/τ_fast) + A_slow·e^(−t/τ_slow).

| purge | peak | end | A_fast | τ_fast | A_slow | τ_slow | m_inf | rms |
|---|---|---|---|---|---|---|---|---|
| TMA (60 s) | 81.3 | 70.0 | 3.2 | 1.2 s | 13.6 | 58 s | 65.0 | 0.16 |
| H2O (60 s) | 98.7 | 85.4 | 6.7 | 1.0 s | 8.0 | 24 s | 84.8 | 0.11 |

Masses in ng/cm², relative to the QCM value before the TMA dose. The TMA-side slow decay has not finished at 60 s,
so its τ is poorly bounded (35–90 s across blocks).

Per block of 10 cycles. The fast amplitude is fitted with τ_slow fixed at the value above.

| cycles | Δm per cycle | lost in TMA purge | TMA A_fast | lost in H2O purge | H2O A_fast |
|---|---|---|---|---|---|
| 1–10 | 41.9 | 6.4 | 1.5 | 4.5 | 1.1 |
| 11–20 | 66.7 | 2.5 | fit failed | 6.9 | 2.7 |
| 21–30 | 80.8 | 6.6 | 1.7 | 9.1 | 5.7 |
| 31–40 | 86.2 | 14.1 | 2.9 | 15.8 | 7.3 |
| 41–49 | 89.5 | 13.6 | 6.4 | 15.3 | 7.6 |

Checks on what else could move the QCM:
- **Pressure.**
  - In the pump/hold/purge cycles after the run, pressure swings between 0.07 and 4.2 Torr.
  - The QCM against pressure has a slope of −0.6 ng/cm² per Torr. A TMA spike of 0.16 Torr would give 0.1 ng/cm².
  - The QCM range within each 60 s cycle has a median of 4.2 ng/cm², two resolution steps.
  - The QCM does not read pressure.
- **Reactor temperature.** The logged reactor temperature varies by 0.014 °C over a mean cycle. The crystal's own temperature is not logged.
- **Instrument speed.** In a single cycle the QCM jumps by about 73 ng/cm² within one 0.3 s interval, so the 1 s and 58 s decays are not the instrument's response time.
- **Visibility.** Per cycle, the fast part is about one QCM step, so it shows only in cycle averages.

Exhaust pressure after the TMA dose (mean of cycles 4–48; the gauge reads in 10 mTorr steps):
- Δp is 18.7 mTorr at 10 s, 9.2 at 20 s, 7.4 at 30 s, 5.8 at 40 s and 4.3 at 50 s.
- The late tail (15–55 s) decays with τ = 31 s (with a constant offset of 1.7 mTorr) or 42 s (without).
  Earlier windows give 7–31 s.
- This is consistent with the slow QCM decay (35–60 s). Given the baseline ambiguity, the tail is a cross-check, not a fit.
- The earlier A10 fit gave 1/k_des ≈ 20 s with a linear wall reservoir and a 2.5 s gauge lag.
- The H2O exhaust spike has no tail (A10). So the QCM loss in the H2O purge is not seen at the gauge, and its origin is open.

Desorption does not explain the drift of Δm per cycle (42 → 90 ng/cm²) over the run.

## 4. What Yanguas-Gil, Libera, Elam (2021) provides

Reference: J. Vac. Sci. Technol. A 39, 062404 (2021), doi:10.1116/6.0001212.

- **Eq. 6, wall boundary condition:** −D ∂c_i/∂n = ¼ β_i v_th c_i − F_i.
  F_i is the desorption flux from the wall into the gas. β_i includes reversible and irreversible uptake.
- **Eqs. 21–22, "sticky precursors":** monolayer reversible adsorption on reacted sites.
  - Θ is the fraction of reacted sites without adsorbed precursor; Θa is the fraction with adsorbed precursor.
  - Printed form:
    - dΘ/dt = s0 β10 J1 (1 − Θ − Θa) + k0 Θa
    - dΘa/dt = s0 βa0 J1 Θ − kd Θa
  - kd is the desorption rate; βa0 is the sticking probability for reversible adsorption.
  - Stated consequence: growth per cycle exceeds the nominal value when the coreactant reacts with reversibly adsorbed precursor.
- **The printed Eq. 21 does not conserve sites.** k0 is not defined, and the −s0 βa0 J1 Θ term is missing. The conserving form is:
  dΘ/dt = s0 β10 J1 (1 − Θ − Θa) − s0 βa0 J1 Θ + kd Θa.
- **No parameter values.** The paper formulates the sticky-precursor model but does not simulate it. Its results cover ideal ALD, soft
  saturation (Eqs. 13–14) and by-product site blocking (Eqs. 15–19).
  - The discussion notes that a soft-saturating precursor with a slow reversible intermediate needs at least four parameters per precursor.
- Code: github.com/aldsim/aldFoam (OpenFOAM, GPL v3).

## 5. Proposed model terms (TMA only; not implemented)

Named S1–S3 to avoid confusion with the D rows (user decisions) in CHANGELOG.md.

**S1, FlatModel (QCM sample).** States: θ = reacted sites with nothing on top; θa = reacted sites with one reversibly adsorbed TMA.
θ + θa is the total reacted coverage, which is Larry's θ. 1 − θ − θa is the fraction of open (unreacted) sites.

```
dθ/dt  = k1·p(t)·(1 − θ − θa) − ka·p(t)·θ + kd·θa
dθa/dt = ka·p(t)·θ − kd·θa
k1 = ¼·s0·v_th·β10/(RT)   (Larry's coefficient, β10 = c);   ka = same with βa0
```

- p(t) is the TMA pressure at the sample from the reactor model, so it includes η.
- H2O reacts with θa as with θ, which gives the extra growth the paper describes.
- With βa0 = 0, θa stays 0 and the model is Larry's.

QCM mass. Each surface state carries a fixed mass per area. The zero is the hydroxylated surface before the dose.

| state | fraction | mass if every site were in it |
|---|---|---|
| not reacted | 1 − θ − θa | 0 |
| reacted | θ | M_c = n_s (72 − 16x)/N_A (TMA attaches, x CH4 leave) |
| reacted + adsorbed TMA | θa | M_c + M_a, with M_a = n_s·72/N_A |

```
m = M_c (θ + θa) + M_a θa
```

During a purge (p = 0), d(θ + θa)/dt = 0, so the reacted total stays constant: desorption removes only the molecule on top.
Then θa(t) = θa(t_d)·e^(−kd (t − t_d)), and

```
m(t) = M_c θ_total + M_a θa(t_d) e^(−kd (t − t_d))  [+ A_fast e^(−(t − t_d)/τ_fast)]
```

So the slow exponential follows from the equations: m_inf = M_c θ_total, A_slow = M_a θa(t_d), τ_slow = 1/kd.
The fast term is not derived. It is an empirical correction added because the data show it (section 7).
M_a/M_c = 72/(72 − 16x) is 1.3 for x = 1 and 1.8 for x = 2, if M_a is to be fixed rather than fitted.

**S2, reactor walls.**
- The same θa state at every wall node.
- The desorbed flux F = kd·θa·n_s is returned to the gas (Eq. 6).
- This replaces the linear C11 reservoir with a site-limited one.
- The same kd is used as on the QCM (same coated surface, same temperature) unless the data say otherwise.

**S3, fit to WALDO.**
- kd and M_a θa come from the TMA-purge decays.
- The same kd should reproduce the exhaust tail.

**Use in real-time control.**
- Each cycle, the twin splits the QCM TMA step into the reacted part (θ) and the reversible part (θa).
- It predicts θa left when H2O arrives, and therefore the extra growth.
- The control knob is the TMA purge time: end the purge when the predicted θa falls below a threshold.

## 6. Identifiability (A14)

Local Fisher analysis of the S1 QCM model, from `fitting/qcm_sticky_identifiability.py`.
- Noise: 1 ng/cm² per 1 s sample.
- Truth: kd = 1/50 s; 14 ng/cm² desorbs after a saturating 0.1 s dose.
- Regimes: R1, the reversible layer fills during the dose; R2, it stays far from full.
- The QCM only sees k1·η (∝ c·η) and ka·η (∝ βa0·η).

Relative standard errors:

| parameter | 7/02 as run, one cycle | 30 cycles pooled | dose series, 60 s purges | dose series, 180 s purges, + 3 full-source doses |
|---|---|---|---|---|
| M_c | 5 % | 1 % | 1 % | ≤1 % |
| kd | 39–49 % | 7–9 % | 11–13 % | 1–2 % |
| M_a θa (what desorbs) | yes | yes | yes | yes |
| M_a alone | no | no (R1 23 %) | R1 4 %, R2 no | 1–3 % |
| ka·η | no | no | R1 9 %, R2 no | 3–4 % |
| k1·η | no | no | 3 % | 1 % |
| fast term (nuisance) | no | no | 36–48 % | 31–40 % |

"Dose series" = TMA pulses of 0.1–3.2 s at 1/10 source flow.

Conclusions:
- **The 7/02 run determines only M_c, kd (roughly) and the amount that desorbs.** Its doses saturate, so they carry no rate
  information: k1·η, ka·η and M_a trade against each other with correlations of ±1.
- **Pooling cycles assumes constant parameters.** Δm per cycle doubles over the run, so the pooled numbers are optimistic.
- **From QCM alone, c is never separable from η, and βa0 is never separable from η.** They need c from the KB or from a test chip (README,
  Identifiability). βa0 then inherits the uncertainty of c.
- **β_wall and the wall desorption terms (S2) were not part of this analysis.** They need the reactor model with the exhaust tail.
- **These are local results at assumed true values.** They show which parameters can be told apart, not global uniqueness.

Suggested test run on WALDO:
- TMA pulses of 0.1–3.2 s at about 1/10 source flow.
- Purges of at least 180 s (about 3/kd).
- Two or three doses at full source flow.

## 7. Physical meaning of the slow and fast terms

**Slow term (τ ≈ 58 s TMA, 24 s H2O).**
- TMA held reversibly on reacted sites (Eq. 22) leaving at rate kd. No film is lost.
- Whatever is still adsorbed when H2O arrives adds growth.
- The QCM does not read pressure, and the exhaust tail decays on a similar time scale.
- The H2O-side slow term would need its own state. The TMA-only proposal leaves it out.

**Fast term (about 1 s; 3 ng/cm² TMA, 7 ng/cm² H2O in cycles 21–49).** Not settled. Two candidates:
1. **A weakly bound state that leaves within about a second.** The gas at the sample clears in about 0.5 s in the WALDO reactor model.
   In the model it would be a second θa-type state with kd ≈ 1/s.
2. **A crystal temperature transient read as mass.** This could come from a gas pulse at a different temperature
   (Rocklein & George, Anal. Chem. 75, 4975 (2003)) or from the heat of reaction.

The fast amplitude grows about 4× over the run while the gas pulse is unchanged (section 3 table). This argues against a pure
gas-temperature effect and points to something on the surface, but the block fits are noisy.

Tests:
- A dummy pulse with the TMA source isolated (carrier gas only): a temperature artifact would still appear.
- A second TMA dose on the saturated surface (TMA, purge, TMA): the slow term should reappear without new chemisorption.

The fast term is gone about 3 s after the dose, long before the coreactant. It does not affect growth, purge time or the channel
prediction. It matters only for fitting the QCM: either keep the nuisance term or drop the first ~3 s after each dose.

## 8. Open items

- User approval for S1–S3 (TMA only).
- A WALDO test run: the dose series with long purges, plus the dummy-pulse and double-dose checks.
- The origin of the H2O-side QCM loss, and the doubling of Δm per cycle over the run.
