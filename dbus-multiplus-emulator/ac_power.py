"""AC power split for the MultiPlus emulator.

Venus OS systemcalc computes:

  ConsumptionOnInput  = max(0, Grid - Multi AC-In + PV on AC-in)
  ConsumptionOnOutput = max(0, Multi AC-Out + PV on AC-out)

A real Multi measures AC-In after PV on the input side, so:

  AC-In  = Grid + PV on AC-in 1
  AC-Out = AC-In - DC          (DC > 0 means charging)

PV on AC-out is added back by Venus, so it must not be included in AC-Out.
PV on AC-in 2 is a genset-side inverter and is not part of Multi AC-In 1.
"""

# com.victronenergy.pvinverter /Position
PV_POSITION_AC_IN1 = 0
PV_POSITION_AC_OUTPUT = 1
PV_POSITION_AC_IN2 = 2

# Below this sum(|AC-In|), spread DC equally instead of by |P| share.
_DC_SPLIT_MIN_TOTAL = 1.0


def as_number(value, default=0.0):
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def phase_power_or_total(phase_powers, total_power, phase_list):
    """Use per-phase powers, or put /Ac/Power on L1 when every phase is missing."""
    resolved = {phase: phase_powers.get(phase) for phase in phase_list}
    if all(value is None for value in resolved.values()):
        if total_power is None or not phase_list:
            return {phase: None for phase in phase_list}
        fallback = {phase: None for phase in phase_list}
        fallback[phase_list[0]] = total_power
        return fallback
    return resolved


def pv_power_on_input_and_output(inverters, phase_list):
    """Split PV inverter power by /Position.

    inverters: iterable of dicts with 'position' and per-phase power keys.
    Position 2 (AC-in 2 / genset) is ignored here: this emulator has one AC input.
    """
    on_input = {phase: 0.0 for phase in phase_list}
    on_output = {phase: 0.0 for phase in phase_list}
    for inverter in inverters:
        position = int(as_number(inverter.get("position"), PV_POSITION_AC_IN1))
        if position == PV_POSITION_AC_OUTPUT:
            target = on_output
        elif position == PV_POSITION_AC_IN1:
            target = on_input
        else:
            continue
        for phase in phase_list:
            target[phase] += as_number(inverter.get(phase))
    return on_input, on_output


def charger_power(voltage, current, dc_power=None, yield_power=None):
    """One solar charger's watts: V×I, else /Dc/0/Power, else /Yield/Power."""
    if voltage is not None and current is not None:
        return as_number(voltage) * as_number(current)
    if dc_power is not None:
        return as_number(dc_power)
    return as_number(yield_power)


def multi_dc_power(battery_power, mppt_power=0.0, dc_load_power=0.0):
    """VE.Bus DC port: battery minus DC-coupled PV plus measured DC loads."""
    return as_number(battery_power) - as_number(mppt_power) + as_number(dc_load_power)


def normalize_energy(payload):
    """Map stored kWh JSON onto current /Energy/* keys.

    v0.0.4 stored inverter kWh only under dc.charging / dc.discharging and
    grid under ac.from_grid / ac.feed_in. Copy those when the new keys are
    absent so an upgrade does not publish 0 kWh.
    """
    payload = payload or {}
    dc = payload.get("dc") or {}
    ac = payload.get("ac") or {}
    charging = as_number(dc.get("charging"))
    discharging = as_number(dc.get("discharging"))
    if "out_to_inverter" in ac:
        out_to_inverter = as_number(ac.get("out_to_inverter"))
    else:
        out_to_inverter = charging
    if "inverter_to_ac_out" in ac:
        inverter_to_ac_out = as_number(ac.get("inverter_to_ac_out"))
    else:
        inverter_to_ac_out = discharging
    if "ac_in1_to_ac_out" in ac:
        ac_in1_to_ac_out = as_number(ac.get("ac_in1_to_ac_out"))
    else:
        ac_in1_to_ac_out = as_number(ac.get("from_grid"))
    if "ac_out_to_ac_in1" in ac:
        ac_out_to_ac_in1 = as_number(ac.get("ac_out_to_ac_in1"))
    else:
        ac_out_to_ac_in1 = as_number(ac.get("feed_in"))
    return {
        "dc": {"charging": charging, "discharging": discharging},
        "ac": {
            "ac_in1_to_ac_out": ac_in1_to_ac_out,
            "ac_in1_to_inverter": as_number(ac.get("ac_in1_to_inverter")),
            "out_to_inverter": out_to_inverter,
            "inverter_to_ac_out": inverter_to_ac_out,
            "ac_out_to_ac_in1": ac_out_to_ac_in1,
        },
    }


def energy_payload_usable(payload):
    """True when JSON has energy keys; empty/corrupt loads are not usable."""
    return isinstance(payload, dict) and ("dc" in payload or "ac" in payload)


def select_energy_payload(working, storage):
    """Prefer volatile JSON; skip empty/invalid working data for /data."""
    if energy_payload_usable(working):
        return working
    if energy_payload_usable(storage):
        return storage
    return {}


def calculate_multi_ac_power(grid_power, pv_on_input, dc_power, phase_list):
    """Return (ac_in, ac_out) power dicts per phase.

    AC-In  = Grid + PV on AC-in 1
    AC-Out = AC-In - DC  (DC > 0 means charging)

    DC is spread by |AC-In| so mixed-sign phases cannot explode. PV on AC-out
    is omitted on purpose: Venus adds /Ac/PvOnOutput back onto Multi AC-Out.
    """
    ac_in = {}
    for phase in phase_list:
        ac_in[phase] = as_number(grid_power.get(phase)) + as_number(
            (pv_on_input or {}).get(phase)
        )
    ac_out = _subtract_dc(ac_in, dc_power, phase_list)
    return ac_in, ac_out


def _subtract_dc(ac_in, dc_power, phase_list):
    dc = as_number(dc_power)
    phase_count = len(phase_list) or 1
    weights = {phase: abs(as_number(ac_in.get(phase))) for phase in phase_list}
    weight_total = sum(weights.values())
    ac_out = {}
    for phase in phase_list:
        if weight_total < _DC_SPLIT_MIN_TOTAL:
            share = 1.0 / phase_count
        else:
            share = weights[phase] / weight_total
        ac_out[phase] = as_number(ac_in.get(phase)) - dc * share
    return ac_out


def energy_flows(ac_in_total, ac_out_total, dc_power):
    """Instantaneous watts for VE.Bus /Energy/* counters."""
    ac_in_total = as_number(ac_in_total)
    ac_out_total = as_number(ac_out_total)
    dc = as_number(dc_power)
    charging = max(0.0, dc)
    discharging = max(0.0, -dc)
    ac_in_to_inverter = max(0.0, min(charging, ac_in_total))
    return {
        "ac_in1_to_ac_out": max(0.0, min(ac_in_total, ac_out_total)),
        "ac_in1_to_inverter": ac_in_to_inverter,
        "out_to_inverter": max(0.0, charging - ac_in_to_inverter),
        "inverter_to_ac_out": discharging,
        "ac_out_to_ac_in1": max(0.0, -ac_in_total),
    }


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
