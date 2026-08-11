"""Unit-model tests (spec §14 items 1-8, 13.1)."""
import sys as _sys
from pathlib import Path as _Path
_PSED_ROOT = _Path(__file__).resolve().parents[2]
_sys.path.insert(0, str(_PSED_ROOT))
import unittest

from pipeline.canonical import units as U


class TestDirectUnitConversion(unittest.TestCase):
    def test_01_nm_to_um(self):
        self.assertAlmostEqual(U.convert(1000.0, "nm", "µm"), 1.0, places=12)
        self.assertAlmostEqual(U.convert(1.0, "µm", "nm"), 1000.0, places=9)

    def test_02_angstrom_to_nm(self):
        self.assertAlmostEqual(U.convert(10.0, "Å", "nm"), 1.0, places=12)
        self.assertAlmostEqual(U.convert(10.0, "angstrom", "nm"), 1.0, places=12)
        self.assertAlmostEqual(U.convert(10.0, "A", "nm"), 1.0, places=12)

    def test_03_angstrom_per_cycle_to_nm_per_cycle(self):
        self.assertAlmostEqual(U.convert(10.0, "Å/cycle", "nm/cycle"), 1.0, places=12)
        self.assertAlmostEqual(U.convert(1.0, "Å/cyc", "nm/cycle"), 0.1, places=12)

    def test_04_torr_to_pa(self):
        self.assertAlmostEqual(U.convert(1.0, "Torr", "Pa"), 133.32236842105263, places=9)
        self.assertAlmostEqual(U.convert(1.0, "mbar", "Pa"), 100.0, places=9)
        self.assertAlmostEqual(U.convert(1.0, "atm", "Pa"), 101325.0, places=6)

    def test_05_minutes_to_seconds(self):
        self.assertAlmostEqual(U.convert(5.0, "min", "s"), 300.0, places=9)
        self.assertAlmostEqual(U.convert(1.0, "h", "s"), 3600.0, places=9)

    def test_06_celsius_to_kelvin_is_affine(self):
        self.assertAlmostEqual(U.convert(25.0, "°C", "K"), 298.15, places=9)
        self.assertAlmostEqual(U.convert(0.0, "°C", "K"), 273.15, places=9)
        self.assertAlmostEqual(U.convert(298.15, "K", "°C"), 25.0, places=9)
        # a pure scale factor would give 25*1 = 25, not 298.15
        self.assertNotAlmostEqual(U.convert(25.0, "°C", "K"), 25.0, places=3)

    def test_07_percent_to_fraction(self):
        self.assertAlmostEqual(U.convert(50.0, "%", "1"), 0.5, places=12)
        self.assertAlmostEqual(U.convert(0.5, "1", "%"), 50.0, places=12)


class TestCycleDimension(unittest.TestCase):
    def test_08_cycle_is_not_interchangeable_with_dimensionless(self):
        with self.assertRaises(U.IncompatibleDimensions):
            U.convert(10.0, "cycle", "1")
        with self.assertRaises(U.IncompatibleDimensions):
            U.convert(10.0, "1", "cycle")

    def test_08b_gpc_never_degrades_to_length(self):
        """Å/cycle -> nm must be refused; only Å/cycle -> nm/cycle is legal."""
        with self.assertRaises(U.IncompatibleDimensions):
            U.convert(10.0, "Å/cycle", "nm")
        with self.assertRaises(U.IncompatibleDimensions):
            U.convert(1.0, "nm", "nm/cycle")

    def test_08c_cycle_dimension_is_its_own_base(self):
        self.assertEqual(U.dimension_name("cycle"), "cycle")
        self.assertEqual(U.dimension_name("nm/cycle"), "length_per_cycle")
        self.assertEqual(U.dimension_name("nm"), "length")
        self.assertEqual(U.dimension_name("1"), "dimensionless")
        self.assertEqual(len({U.dimension_of("cycle"), U.dimension_of("nm/cycle"),
                              U.dimension_of("nm"), U.dimension_of("1")}), 4)


class TestUnknownVsDimensionless(unittest.TestCase):
    def test_empty_unit_is_not_automatically_dimensionless(self):
        with self.assertRaises(U.UnknownUnit):
            U.parse("")
        with self.assertRaises(U.UnknownUnit):
            U.parse(None)
        # only with explicit semantic permission
        self.assertEqual(U.parse("", allow_empty_as_dimensionless=True).symbol, "1")

    def test_arbitrary_units_are_unknown_not_dimensionless(self):
        for token in ("a.u.", "arb. units", "cps", "counts"):
            with self.assertRaises(U.UnknownUnit):
                U.parse(token)

    def test_unrecognised_unit_raises(self):
        with self.assertRaises(U.UnknownUnit):
            U.parse("bananas")


class TestOffsetUnits(unittest.TestCase):
    def test_offset_unit_rejected_as_ratio_unit(self):
        self.assertFalse(U.is_ratio_safe("°C"))
        self.assertTrue(U.is_ratio_safe("K"))
        self.assertTrue(U.is_ratio_safe("nm"))
        with self.assertRaises(U.OffsetUnitMisuse):
            U.require_ratio_safe("°C", "denominator")


class TestConverterGuards(unittest.TestCase):
    def test_convert_refuses_none_value(self):
        """The historical live-pipeline bug: normalisation called with value=None
        silently returned without rescaling. It must raise instead."""
        with self.assertRaises(ValueError):
            U.convert(None, "Å", "nm")

    def test_series_conversion_preserves_length(self):
        out = U.convert_series([10.0, None, 20.0], "Å", "nm")
        self.assertEqual(len(out), 3)
        self.assertAlmostEqual(out[0], 1.0, places=12)
        self.assertIsNone(out[1])
        self.assertAlmostEqual(out[2], 2.0, places=12)

    def test_micro_sign_variants_unify(self):
        for v in ("um", "µm", "μm", "micron"):
            self.assertEqual(U.canonical_symbol(v), "µm")

    def test_qudt_bridge(self):
        self.assertEqual(U.from_qudt("http://qudt.org/vocab/unit/NanoM"), "nm")
        self.assertEqual(U.from_qudt("http://qudt.org/vocab/unit/UNITLESS"), "1")


if __name__ == "__main__":
    unittest.main()
