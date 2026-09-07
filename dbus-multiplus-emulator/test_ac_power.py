#!/usr/bin/env python
import unittest

from ac_power import (
    PV_POSITION_AC_IN1,
    PV_POSITION_AC_IN2,
    PV_POSITION_AC_OUTPUT,
    calculate_multi_ac_power,
    energy_flows,
    multi_dc_power,
    phase_power_or_total,
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

    def test_position_two_is_not_folded_into_ac_in1(self):
        on_input, on_output = pv_power_on_input_and_output(
            [{"position": PV_POSITION_AC_IN2, "L1": 50, "L2": 0, "L3": 0}],
            PHASES,
        )
        self.assertEqual(on_input["L1"], 0)
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
        self.assertEqual(on_input["L1"], 100)
        self.assertEqual(on_output["L1"], 25)


class PhasePowerFallbackTests(unittest.TestCase):
    def test_uses_total_on_first_phase_when_all_phases_missing(self):
        resolved = phase_power_or_total(
            {"L1": None, "L2": None, "L3": None}, 1200, PHASES
        )
        self.assertEqual(resolved["L1"], 1200)
        self.assertIsNone(resolved["L2"])
        self.assertIsNone(resolved["L3"])

    def test_keeps_zero_phase_powers(self):
        resolved = phase_power_or_total(
            {"L1": 0, "L2": 0, "L3": 0}, 999, PHASES
        )
        self.assertEqual(resolved, {"L1": 0, "L2": 0, "L3": 0})


class ConsumptionAccountingTests(unittest.TestCase):
    def test_pv_on_input_export_is_not_counted_as_consumption(self):
        grid = _single(-15000)
        pv_in = _single(40000)
        consumption = _consumption(grid, pv_in, _single(0), 0)
        self.assertAlmostEqual(consumption, 25000, places=4)

    def test_pv_on_input_import_plus_solar(self):
        grid = _single(20000)
        pv_in = _single(40000)
        consumption = _consumption(grid, pv_in, _single(0), 0)
        self.assertAlmostEqual(consumption, 60000, places=4)

    def test_legacy_copy_grid_to_ac_in_counts_export_as_consumption(self):
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

    def test_mixed_sign_phases_do_not_explode_dc_split(self):
        grid = {"L1": 100, "L2": -50, "L3": -49}
        ac_in, ac_out = calculate_multi_ac_power(grid, _single(0), 3000, PHASES)
        self.assertAlmostEqual(sum(ac_out.values()), sum(ac_in.values()) - 3000, places=4)
        for phase in PHASES:
            self.assertLess(abs(ac_out[phase]), 4000)

    def test_mppt_is_removed_from_battery_before_ac_out(self):
        # 5 kW MPPT, 3 kW into battery, 2 kW AC load, no grid/AC-PV.
        dc = multi_dc_power(battery_power=3000, mppt_power=5000, dc_load_power=0)
        self.assertAlmostEqual(dc, -2000)
        consumption = _consumption(_single(0), _single(0), _single(0), dc)
        self.assertAlmostEqual(consumption, 2000, places=4)


class EnergyFlowTests(unittest.TestCase):
    def test_charging_splits_passthrough_and_ac_in_to_inverter(self):
        flows = energy_flows(ac_in_total=10000, ac_out_total=5000, dc_power=5000)
        self.assertAlmostEqual(flows["ac_in1_to_ac_out"], 5000)
        self.assertAlmostEqual(flows["ac_in1_to_inverter"], 5000)
        self.assertAlmostEqual(flows["out_to_inverter"], 0)
        self.assertAlmostEqual(flows["inverter_to_ac_out"], 0)
        self.assertAlmostEqual(flows["ac_out_to_ac_in1"], 0)

    def test_export_is_feed_in_not_passthrough(self):
        flows = energy_flows(ac_in_total=-15000, ac_out_total=-15000, dc_power=0)
        self.assertAlmostEqual(flows["ac_out_to_ac_in1"], 15000)
        self.assertAlmostEqual(flows["ac_in1_to_ac_out"], 0)

    def test_pv_on_output_charging_uses_out_to_inverter(self):
        flows = energy_flows(ac_in_total=-1000, ac_out_total=-4000, dc_power=3000)
        self.assertAlmostEqual(flows["ac_in1_to_inverter"], 0)
        self.assertAlmostEqual(flows["out_to_inverter"], 3000)
        self.assertAlmostEqual(flows["ac_out_to_ac_in1"], 1000)


if __name__ == "__main__":
    unittest.main()
