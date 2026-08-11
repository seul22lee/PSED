# yim2020_control

Read-only semantic control study of Yim et al. 2020 (DOI 10.1039/d0cp03358h), used to test
the Experiment semantics diagnosed in `_diagnostics/experiment_identity_3papers/`.

**0 API calls. The paper was NOT enrolled by this task** - it was already corpus member
`papers/10.1039_d0cp03358h`, and its production artifacts were read, never regenerated.

Order of work: PDF ground truth first (`ground_truth/`), then analysis (`analysis/`), then
comparison against observed PSED behaviour (`comparison/`).

Headline: this paper explicitly distinguishes DepositionRun, Sample, DepositionConditionCase,
Measurement, MeasurementCondition, Representation, StudySeries and ModelRun. Current PSED
collapses the first three and multiplies the rest - 6 measurements in Fig. 9 become 18
Experiments, and 6 author-defined Series become 0.
