from pathlib import Path

# ============================================================
# Root directories
# ============================================================

ROOT        = Path(__file__).parent   # project root
PDF_DIR     = ROOT / "pdf"            # input: all PDFs go here
OUTPUT_DIR  = ROOT / "output"         # output root

# ============================================================
# Per-paper output layout
#
#   output/
#     <paper_stem>/
#       01_docling/
#         document.md
#         document.json
#         tables/
#           table-001.csv
#           table-001.html
#           tables.json
#         figures/
#           figure-001.png
#           figures.json
#       02_figure_filter/
#         filtered/
#           figure-001.png
#           filtered_figures.json
#         rejected/
#           figure-002.png
#       03_plot_to_data/
#         figure-001.json
#         figure-003.json
#       04_build_segment/
#         segments.json
#       05_sentence_tagging/
#         transport_tags.json
#         reaction_tags.json
#         geometry_tags.json
#       06_evidence_pools/
#         transport_evidence.json
#         reaction_evidence.json
#         geometry_evidence.json
#       07_schema_extraction/
#         transport_schema.json
#         reaction_schema.json
#         geometry_schema.json
# ============================================================

def paper_dir(paper_stem: str) -> Path:
    return OUTPUT_DIR / paper_stem

def step_dir(paper_stem: str, step: str) -> Path:
    return OUTPUT_DIR / paper_stem / step

# Step directory names (referenced by multiple scripts)
STEP = {
    "01": "01_docling",
    "02": "02_figure_filter",
    "03": "03_plot_to_data",
    "04": "04_build_segment",
    "05": "05_sentence_tagging",
    "06": "06_evidence_pools",
    "07": "07_schema_extraction",
}

# ============================================================
# Static asset paths (prompts, schemas)
# ============================================================

PROMPTS_TAGGING_DIR = ROOT / "prompt_05"   # transport/reaction/geometry_tagging.md
PROMPTS_SCHEMA_DIR  = ROOT / "prompt_07"   # geometry/reaction/transport_schema.md
SCHEMA_MD_DIR       = ROOT / "schema" / "md"
SCHEMA_JSON_DIR     = ROOT / "schema" / "json"

# ============================================================
# Neo4j (08)
# ============================================================

import os

NEO4J_URI      = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
NEO4J_USER     = os.getenv("NEO4J_USER",     "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
