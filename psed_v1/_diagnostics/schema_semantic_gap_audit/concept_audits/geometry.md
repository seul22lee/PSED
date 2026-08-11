# Geometry

**Required**: geometry must vary between cases inside one paper. `2.067203jes` has planar
Si(100) process development **and** a trench conformality case (AR ~30, 830 cycles).

**Ontology**: `geometry_classes.yaml` defines six classes; the core KG prototype emits
`GeometryClass` nodes. The vocabulary is adequate.

**Resolver**: `classify_deterministic()` reads only title+abstract, gates HAR branches on
`GEOM_Q` quantities (which come from the separate LLM `--quantities` stage), and
`tag_experiments()` stamps **one label onto every Experiment in the paper**.
Result: `2.067203jes` = `planar` for all 32 experiments.

**Verdict**: this is gap type **C - schema represents it at the wrong level**, not missing
support. Experiments already carry a `geometry_class` field; it is simply filled from a
paper-level decision.

**Status**: KEEP_BUT_MOVE_LEVEL. Severity HIGH (it gates twin model validity).
