"""Locate project files from a test, without directory-relative guessing.

The regression tests were written when every script sat beside its test, so
they loaded siblings with `HERE / "06_to_kb.py"`. After the responsibility-based
move those names and locations changed, and a test that guesses a path breaks on
every reorganisation. Tests ask this module instead.
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

#: logical name -> module path, so a test never spells a location
MODULES = {
    "to_kb":      ROOT / "pipeline" / "resolve" / "to_kb.py",
    "pressure":   ROOT / "pipeline" / "text" / "pressure.py",
    "geometry":   ROOT / "pipeline" / "text" / "geometry.py",
    "scout":      ROOT / "pipeline" / "scout" / "scout.py",
    "figures":    ROOT / "pipeline" / "figures" / "figure_extract.py",
    "canonical_audit": ROOT / "scripts" / "canonical_audit.py",
    "build_ontology":  ROOT / "ontology" / "build_ontology.py",
    "visualize_ontology": ROOT / "ontology" / "visualize_ontology.py",
}


def load(name):
    """Import a project script by logical name."""
    path = MODULES[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def path(*parts):
    return ROOT.joinpath(*parts)
