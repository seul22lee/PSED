"""The ontology vocabulary was PORTED, not rewritten.

`ontology/vocab.py` was lifted out of the pre-psed_v1 `stages/lib.py`, which
also carried a paper registry and a Gemini client that resolved paths into a
historical tree. Only the vocabulary survived the move; this pins that the
surviving half behaves identically, so the port cannot silently drift.
"""
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from ontology import vocab                                        # noqa: E402


class VocabPort(unittest.TestCase):

    def test_canonicalisation_surface_is_complete(self):
        for fn in ("canon_material", "canon_structure", "canon_precursor",
                   "canon_coreactant", "canon_process", "canon_quantity",
                   "axis_role", "family", "recipe_role", "species_prop",
                   "resolve_axis_label", "vocab", "norm"):
            self.assertTrue(callable(getattr(vocab, fn, None)), fn)

    def test_tables_are_populated_from_the_ontology(self):
        for t in ("MAT", "PREC", "CORE", "PROC", "QK", "FAMILY", "RECIPE_ROLE"):
            self.assertTrue(getattr(vocab, t), "%s is empty" % t)

    def test_known_canonicalisations(self):
        self.assertEqual(vocab.canon_material("Al2O3"), "Al2O3")
        self.assertEqual(vocab.canon_precursor("Al(CH3)3"), "TMA")
        self.assertEqual(vocab.canon_quantity("deposition temperature"),
                         "deposition_temperature")

    def test_no_historical_paths_or_llm_client(self):
        src = (_ROOT / "ontology" / "vocab.py").read_text()
        for banned in ("0604_kg", "0706_pipeline", "run_llm", "load_dotenv",
                       "KG0604", "enrich_dir"):
            self.assertNotIn(banned, src.replace("`0604_kg/`", ""),
                             "the port dragged %s across" % banned)

    def test_ontology_is_read_from_the_project(self):
        self.assertTrue(str(vocab.ONTOLOGY_JSON).endswith(
            "psed_v1/ontology/ald_ontology.json"), vocab.ONTOLOGY_JSON)


if __name__ == "__main__":
    unittest.main(verbosity=1)
