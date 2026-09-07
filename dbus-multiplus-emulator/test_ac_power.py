#!/usr/bin/env python
import unittest

from ac_power import (
    PV_POSITION_AC_IN1,
    PV_POSITION_AC_OUTPUT,
    calculate_multi_ac_power,
    pv_power_on_input_and_output,
    venus_consumption,
)


PHASES = ["L1", "L2", "L3"]


def _single(watts):
    share = watts / 3.0
    return {phase: share for phase in PHASES}


def _consumption(grid, pv_in, pv_out, dc):
    ac_in, ac_out = calculate_multi_ac_power(grid, pv_in, dc, PHASES)
    return venus_consumption(grid, ac_in, ac_out, pv_in, pv_out, PHASES)


class PvSplitTests(unittest.TestCase):
    def test_position_zero_is_ac_input(self):
        on_input, on_output = pv_power_on_input_and_output(
            [{"position": PV_POSITION_AC_IN1, "L1": 1000, "L2": 2000, "L3": 3000}],
            PHASES,
        )
        self.assertEqual(on_input, {"L1": 1000, "L2": 2000, "L3": 3000})
        self.assertEqual(on_output, {"L1": 0, "L2": 0, "L3": 0})

    def test_position_one_is_ac_output(self):
        on_input, on_output = pv_power_on_input_and_output(
            [{"position": PV_POSITION_AC_OUTPUT, "L1": 4000, "L2": 0, "L3": 0}],
            PHASES,
        )
        self.assertEqual(on_input["L1"], 0)
        self.assertEqual(on_output["L1"], 4000)

    def test_missing_position_defaults_to_ac_input(self):
        on_input, on_output = pv_power_on_input_and_output(
            [{"L1": 500, "L2": 0, "L3": 0}],
            PHASES,
        )
        self.assertEqual(on_input["L1"], 500)
        self.assertEqual(on_output["L1"], 0)

    def test_sums_multiple_inverters(self):
        on_input, on_output = pv_power_on_input_and_output(
            [
                {"position": 0, "L1": 100, "L2": 0, "L3": 0},
                {"position": 2, "L1": 50, "L2": 0, "L3": 0},
                {"position": 1, "L1": 25, "L2": 0, "L3": 0},
            ],
            PHASES,
        )
        self.assertEqual(on_input["L1"], 150)
        self.assertEqual(on_output["L1"], 25)


class ConsumptionAccountingTests(unittest.TestCase):
    def test_pv_on_input_export_is_not_counted_as_consumption(self):
        # 40 kW solar on AC-in, 15 kW export, 25 kW house load
        grid = _single(-15000)
        pv_in = _single(40000)
        consumption = _consumption(grid, pv_in, _single(0), 0)
        self.assertAlmostEqual(consumption, 25000, places=4)

    def test_pv_on_input_import_plus_solar(self):
        # 40 kW solar, 20 kW import -> 60 kW load
        grid = _single(20000)
        pv_in = _single(40000)
        consumption = _consumption(grid, pv_in, _single(0), 0)
        self.assertAlmostEqual(consumption, 60000, places=4)

    def test_legacy_copy_grid_to_ac_in_counts_export_as_consumption(self):
        # Documents the bug: AC-In = Grid, PV on AC-in, exporting.
        grid = _single(-15000)
        pv_in = _single(40000)
        ac_in = dict(grid)
        ac_out = dict(grid)
        consumption = venus_consumption(grid, ac_in, ac_out, pv_in, _single(0), PHASES)
        self.assertAlmostEqual(consumption, 40000, places=4)

    def test_pv_on_output_export_is_not_counted_as_consumption(self):
        grid = _single(-15000)
        pv_out = _single(40000)
        consumption = _consumption(grid, _single(0), pv_out, 0)
        self.assertAlmostEqual(consumption, 25000, places=4)

    def test_battery_charging_is_not_counted_as_consumption(self):
        grid = _single(-15000)
        pv_in = _single(40000)
        dc_charging = 5000
        consumption = _consumption(grid, pv_in, _single(0), dc_charging)
        self.assertAlmostEqual(consumption, 20000, places=4)

    def test_battery_discharging_covers_load(self):
        grid = _single(0)
        pv_in = _single(0)
        dc_discharging = -3000
        consumption = _consumption(grid, pv_in, _single(0), dc_discharging)
        self.assertAlmostEqual(consumption, 3000, places=4)

    def test_none_values_are_treated_as_zero(self):
        ac_in, ac_out = calculate_multi_ac_power(
            {"L1": None, "L2": None, "L3": None},
            {"L1": None, "L2": None, "L3": None},
            None,
            PHASES,
        )
        self.assertEqual(sum(ac_in.values()), 0)
        self.assertEqual(sum(ac_out.values()), 0)


if __name__ == "__main__":
    unittest.main()
