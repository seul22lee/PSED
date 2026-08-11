# experiment_identity_3papers

Read-only forensic audit of what `Experiment` means in PSED, using three papers:
`10.1038_am.2016.182`, `10.1149_2.067203jes`, `10.1039_c7ta03257a`.

**0 API calls.** No repository file outside this directory was created, modified or deleted.

Method: PDF ground truth first (Phase A deposition cases, Phase B measurements), then the
current PSED representation (Phase C), then comparison (Phase D). Per paper:
`source/` (snapshots + SHA256), `pdf_ground_truth/`, `tables/`, `notes/diagnosis.md`.
Cross-paper conclusions are in `comparison/`.

Headline: `Experiment` is currently a **result curve plus inferred conditions**, keyed by
figure/panel. There is no sample, specimen or deposition-run identity, so multiple
measurements of one deposited film become multiple Experiments.
