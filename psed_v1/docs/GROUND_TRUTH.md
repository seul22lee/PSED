# Ground Truth — measured data plots per paper
# Based on actual figure/caption review. Compare against after full re-extraction.
# Verdict: DATA (measured data plot, must drill) / SIM (simulation) / IMG (SEM/AFM/schematic, do not drill)

## 10.1039_d0cp03358h  (study: both) — all images opened, confirmed
Fig1 (F5):  IMG  schematic (LHAR channel)
Fig2 (F6):  DATA saturation-profile classification example (has data points; borderline)
Fig3 (F7):  a=SIM (ideal simulated) + b=DATA (experimental scaled)   <- a,b differ in source
Fig4 (F9):  IMG  optical microscopy
Fig5 (F10): a=IMG (SEM) + b=DATA (O/Al/Si intensity curves)          <- only b is data
Fig7 (F13): DATA measured saturation profiles, 3 curves, samples 4,5,6
Fig8 (F14): DATA a: per-L curves + b: per-sample curves
Fig9 (F16): DATA 6 panels a-f, 3 samples each = 18 records
Fig10(F18): SIM  6 panels simulated
Fig11(F19): DATA a: per TMA-pulse + b: per purge
=> measured expected: Fig3b, Fig5b, Fig7, Fig8, Fig9(18), Fig11. model: Fig3a, Fig10.

## 10.1016_j.jcrysgro.2017.04.019  (experimental)
Fig2-5,7 (F3,F4,F5,F6,F8): IMG (SEM/AFM)
Fig6 (F7): DATA thickness vs cycle number (3 substrates: Al2O3/Si/SiO2)  <- only data plot
=> measured expected: Fig6 only.

## 10.1002_celc.201600139  (experimental)
Fig1 (F4):  a=IMG (schematic) + b=DATA (in situ QCM)
Fig2 (F6):  DATA Nyquist plot [caption-judged, image not opened]
Fig3 (F10): DATA AC impedance spectra [caption-judged]
Fig4 (F11): DATA CE vs cycle [caption-judged]
Fig5 (F12): IMG  SEM
=> measured expected: Fig1b, Fig2, Fig3, Fig4. Fig5=SEM.

## 10.1016_j.sse.2022.108584  (MODELING)
Mostly SIM. Fig5 (F7) a=Arrhenius (data fit). Fig6/7 "reported profiles" = other papers' data.
=> modeling paper, near-zero measured is normal.

## 10.1063_1.4867469  (experimental) — images opened, confirmed
FIG1 (F6): IMG RHEED / FIG3 (F8): IMG STEM
FIG2 (F7): DATA XRD / FIG4 (F9): DATA C-V characteristics   <- clearly data
=> measured expected: FIG2, FIG4. This is the case scout wrongly skipped via go_deeper=False.

## 10.1016_j.matt.2019.12.026  (REVIEW) — confirmed
All review/summary figures, no own measurements.
=> measured expected: 0. Skipping (drill 0) is correct.
