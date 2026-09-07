"""AC power split for the MultiPlus emulator.

Venus OS systemcalc computes:

  ConsumptionOnInput  = max(0, Grid - Multi AC-In + PV on AC-in)
  ConsumptionOnOutput = max(0, Multi AC-Out + PV on AC-out)

A real Multi measures AC-In *after* PV on the input side, so:

  AC-In  = Grid + PV on AC-in
  AC-Out = AC-In - DC          (DC > 0 means charging)

Copying the grid meter onto both AC-In and AC-Out makes ConsumptionOnInput
collapse to all PV on AC-in, so exported solar is counted as consumption.

PV on AC-out is added back by Venus, so it must not be included in AC-Out.
"""

# com.victronenergy.pvinverter /Position
PV_POSITION_AC_IN1 = 0
PV_POSITION_AC_OUTPUT = 1
PV_POSITION_AC_IN2 = 2


def as_number(value, default=0.0):
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def pv_power_on_input_and_output(inverters, phase_list):
    """Split PV inverter power by /Position.

    inverters: iterable of dicts with 'position' and per-phase power keys.
    """
    on_input = {phase: 0.0 for phase in phase_list}
    on_output = {phase: 0.0 for phase in phase_list}
    for inverter in inverters:
        position = int(as_number(inverter.get("position"), PV_POSITION_AC_IN1))
        target = on_output if position == PV_POSITION_AC_OUTPUT else on_input
        for phase in phase_list:
            target[phase] += as_number(inverter.get(phase))
    return on_input, on_output


def calculate_multi_ac_power(grid_power, pv_on_input, dc_power, phase_list):
    """Return (ac_in, ac_out) power dicts per phase.

    AC-In  = Grid + PV on AC-in
    AC-Out = AC-In - DC  (DC > 0 means charging)

    DC is spread across phases in proportion to AC-In. PV on AC-out is omitted
    on purpose: Venus adds /Ac/PvOnOutput back onto Multi AC-Out.
    """
    ac_in = {}
    for phase in phase_list:
        ac_in[phase] = as_number(grid_power.get(phase)) + as_number(
            (pv_on_input or {}).get(phase)
        )

    total_ac_in = sum(ac_in.values())
    dc = as_number(dc_power)
    phase_count = len(phase_list) or 1
    ac_out = {}
    for phase in phase_list:
        ratio = (ac_in[phase] / total_ac_in) if total_ac_in != 0 else (1.0 / phase_count)
        ac_out[phase] = ac_in[phase] - dc * ratio
    return ac_in, ac_out


def venus_consumption(grid_power, ac_in, ac_out, pv_on_input, pv_on_output, phase_list):
    """dbus-systemcalc consumption, used by tests to lock the accounting."""
    total = 0.0
    for phase in phase_list:
        on_input = (
            as_number((grid_power or {}).get(phase))
            - as_number((ac_in or {}).get(phase))
            + as_number((pv_on_input or {}).get(phase))
        )
        on_output = as_number((ac_out or {}).get(phase)) + as_number(
            (pv_on_output or {}).get(phase)
        )
        total += max(0.0, on_input) + max(0.0, on_output)
    return total
