# Changelog

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
