# Scope escalations

Work stopped at the pilot boundary rather than growing into production.

## E1 — case-level geometry for `10.1149_2.067203jes` could not be demonstrated

**Requirement.** §11 / §15B: planar and HAR-trench contexts must be able to coexist.

**Why the scoped implementation is insufficient.** The pilot resolves geometry per figure
scope and falls back to the paper-level value, and it reports which of the two it used.
For this paper every case reports `planar` from the paper-level default, because the
printed figures that carry the high-aspect-ratio conformality results are **not in the
extracted set at all** — the extracted figures (2, 4, 5, 6, 9, 10, 11, 12) are all
planar-substrate measurements. There is no per-case geometry evidence in the pilot's
snapshot to attach.

**Exact technical blocker.** Recovering the HAR figures would require re-running figure
extraction (Docling → inventory → Scout → vision) for this paper, which the task freezes.

**Minimum broader change apparently required.** Re-extract the missing printed figures,
then re-check. The pilot's geometry mechanism itself needs no change: it already prefers
figure-scope evidence and records `geometry_source` so a paper-level default is visible
as a default rather than as a finding.

**Independent work continued.** The multi-material half of the same requirement IS
demonstrated on this paper: the SiO2/Al2O3 stack cases from printed Figure 12 carry both
materials with `STACK_COMPONENT` roles.

## E2 — Series E's varied variable stays UNRESOLVED

**Requirement.** §16: record each series' varied variable and its role.

**Why insufficient.** The pilot derives a series' varied variable from the column of the
paper's own specimen table that differs across its members. For Series E two columns
differ (TMA pulse time *and* pillar layout, because specimen 14 uses `v2a`), so the pilot
reports the ambiguity instead of choosing. The prose names the TMA pulse time, but the
table does not single it out.

**Blocker.** Resolving it would require deciding that the prose outranks the table, which
is a semantic decision reserved outside this task.

**Recorded, not guessed.** `study_series.json` carries `varied_variable_role = UNRESOLVED`
with both candidates in `purpose`.

## E3 — Fig 7's three curves cannot each be bound to their specimen

**Requirement.** §15D: Series B's specimens are 4, 5 and 6.

**Why insufficient.** The caption names all three specimens for all three curves and never
says which curve is which; the legends give the objective (`X5 (50 µm)`), whose numbers
match two different specimens' magnification values. Binding by list order would be a
guess.

**Consequence, and why it is acceptable.** The specimens stay collectively attached and
the anchor still holds: figure 7 yields ONE deposition case carrying three measurements,
because the series' only varying tabulated column is an instrument setting.
