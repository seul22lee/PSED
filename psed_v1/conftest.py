"""Put the psed_v1 root on sys.path for every test run.

Tests import `pipeline.*`, `ontology.*`, `twin.*` and `paths` as ordinary
packages; this is what makes that work from any working directory without a
single `sys.path.append("../..")` in a test file.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
