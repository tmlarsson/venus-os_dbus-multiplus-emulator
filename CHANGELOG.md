# Changelog

## v0.0.5
* Changed: Only publish live AC/DC/energy/SoC values every second; static Multi paths stay at their initial values
* Changed: PV `/Ac/Power` is used when per-phase powers are missing; PV on AC-in 2 is not folded into AC-in 1
* Changed: `/Energy/*` paths use kWh text format
* Changed: `install.sh` / `restart.sh` / `uninstall.sh` / `service/run` use `ln -sfn`, `svc -t`, and `python3 -u`
* Changed: Grid and battery are read with `get_value()` every tick (no longer change-only caches)
* Changed: Multi DC is `battery - MPPT + DC loads` so MPPT charge is not treated as Multi AC-out
* Changed: DC is spread by `|AC-In|` so mixed-sign phases cannot explode
* Changed: Energy counters split passthrough, AC-in-to-inverter, out-to-inverter, and feed-in
* Fixed: Corrupt energy JSON no longer restart-loops the service; writes are atomic
* Fixed: `ChargeMode` and `Power/Current==0` no longer abort the rest of `_update()`
* Fixed: `/Ac/NumberOfPhases` follows the configured `phases` list

## v0.0.4
* Fixed: Solar export was counted as consumption because Multi AC-In copied the grid meter and ignored PV on AC-in
* Added: Read PV inverter position and power, and subtract battery DC power from AC-Out
* Added: Energy counters for feed-in (`AcOutToAcIn1`) and passthrough (`AcIn1ToAcOut`)

## v0.0.3
* Added: Energy sum of power from `Out to Inverter` and `Inverter to Out`
* Added: LED display
* Added: Units to the values

## v0.0.2
* Added: Get automatically the grid and battery meter, if there is only one
* Added: Select on which phase the PV Inverter is connected to
* Changed: Fixed caluclations for AC-Out

## v0.0.1
Initial release
