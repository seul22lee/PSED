"""
0706_pipeline/config.py  —  ontology-first ALD KG pipeline config
=================================================================
Reorganization of 0604_kg around the ontology backbone (0706_ontology).

Two design changes vs 0604_kg:
  1. The ONTOLOGY is stage 0. Schema, normalization, and the KG all instantiate
     against it (no ad-hoc node/variable minting).
  2. INPUT SCOPE is a PER-STAGE knob, not one global choice. Different stages
     need different amounts of the paper (see INPUT_SCOPE below). Equations are
     promoted to their own first-class stage.
"""

from pathlib import Path

ROOT       = Path(__file__).parent
ONTOLOGY_DIR = ROOT.parent / "01_ontology"     # the ontology module (reused, not duplicated)
PDF_DIR    = ROOT / "pdf"
OUTPUT_DIR = ROOT / "output"

# ============================================================================
# INPUT SCOPE  — how much of each paper a stage sees.
#
# Recommendation (grounded in what the parser already isolates in sections.json:
# abstract / conclusion / full document.md):
#   - Light "profiling" stages (what is this paper, what does it claim) only need
#     the abstract + conclusion. Cheaper, less noise, fewer hallucinated details.
#   - Quantitative extraction (per-experiment conditions, figure data, equations)
#     REQUIRES the full manuscript — abstracts never contain GPC values, per-run
#     conditions, or governing equations.
#
# So do NOT pick one global scope. This map is the default; benchmark it with
# `pipeline.py --benchmark-scope` (abstract-only vs abstract+conclusion vs full)
# on the 3-paper set to confirm before scaling.
#
# Allowed values: "abstract" | "abstract+conclusion" | "full"
# ============================================================================
# Set from benchmark/RESULTS.md (evidence, not intuition). The winner is an
# "evidence" scope = abstract + conclusion + figure/table captions + the
# paragraphs discussing them: 2.1x abstract's recall, quantitative at 69%, HIGHER
# precision than full text (excludes intro/background), at ~1/4 the tokens.
INPUT_SCOPE = {
    "triage":            "abstract",   # coarse material+process classification only
    "study_profile":     "evidence",   # precursors/conditions/structures at high precision
    "experiment_schema": "evidence",   # per-experiment conditions & outputs (quant recall 69%)
    "figure_data":       "evidence",   # figure-anchored; caption+context is exactly this scope
    "equations":         "full",       # governing equations live in theory/methods, not captions
    "claims":            "full",       # evidence recovers only ~19% of claims
}
# "evidence" scope = abstract + conclusion + captions + figure/table contexts,
# assembled by benchmark/slice_scopes.py (read_evidence). Enriching it with full
# tables + results paragraphs should lift quant recall further.

# Benchmark also surfaced an extractor PRECISION issue (independent of scope):
# full-text extraction over-collects background/intro entities (e.g. TiN/TaN
# mentioned in an intro, instruments listed as structures). The ported extractor
# needs a paper-scope RELEVANCE filter, and records should carry entity
# provenance/role (studied-experimental vs background-mentioned).
RELEVANCE_FILTER = True

# ============================================================================
# EQUATIONS  — now first-class (was buried in 04_formula_to_data).
# Each equation is parsed to {latex, symbols, lhs, rhs, described_variables} and
# its symbols/variables are linked to ontology QuantityKinds. This is the hook
# the v2 model-aware layer attaches to (equation -> model -> assumptions/priors).
# ============================================================================
EQUATIONS = {
    "enabled": True,
    "source": "formulas",          # docling formulas/ (images + formulas.json) + inline md
    "link_to_ontology": True,      # map equation symbols -> QuantityKind IRIs
}

# ============================================================================
# Per-paper output layout (stage dirs)
# ============================================================================
STAGES = {
    "s00": "s00_ontology",       # build+validate ontology (module-level, not per-paper)
    "s01": "s01_parse",          # docling: text, sections, tables, figures, formulas
    "s02": "s02_figure_filter",
    "s03": "s03_plot_to_data",
    "s04": "s04_equations",      # NEW first-class equation extraction + ontology linking
    "s05": "s05_scope_select",   # slice text per INPUT_SCOPE for each consumer stage
    "s06": "s06_schema_extract", # ontology-typed experiment schema
    "s07": "s07_normalize",      # canonicalize units (QUDT) + names (dictionary)
    "s08": "s08_link",           # resolve entities -> ontology individuals
    "s09": "s09_kg",             # ontology-grounded KG  (09_kg_onto.py logic)
    "s10": "s10_visualize",
}

# Map new stages -> existing 0604_kg scripts to port (migration aid)
PORT_FROM = {
    "s01": "0604_kg/01_docling_extract.py",
    "s02": "0604_kg/02_figure_filter.py",
    "s03": "0604_kg/03_plot_to_data.py",
    "s04": "0604_kg/04_formula_to_data.py (promote + add ontology linking)",
    "s06": "0604_kg/06_experiment_schema.py",
    "s07": "0604_kg/07_normalize.py",
    "s08": "0604_kg/08_match.py (reframe as ontology entity resolution)",
    "s09": "0604_kg/09_kg_onto.py (DONE — ontology-grounded)",
    "s10": "0604_kg/10_visualize_matches.py",
}


def paper_dir(stem: str) -> Path:
    return OUTPUT_DIR / stem

def step_dir(stem: str, step_key: str) -> Path:
    return OUTPUT_DIR / stem / STAGES[step_key]
