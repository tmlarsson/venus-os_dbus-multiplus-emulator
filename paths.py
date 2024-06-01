# formatting
def _kwh(p, v):
    return str("%.2f" % v) + "kWh"

def _a(p, v):
    return str("%.2f" % v) + "A"

def _w(p, v):
    return str("%i" % v) + "W"

def _va(p, v):
    return str("%i" % v) + "VA"

def _v(p, v):
    return str("%i" % v) + "V"

def _hz(p, v):
    return str("%.1f" % v) + "Hz"

def _c(p, v):
    return str("%i" % v) + "°C"

def _percent(p, v):
    return str("%.1f" % v) + "%"

def _n(p, v):
    return str("%i" % v)

def _s(p, v):
    return str("%s" % v)

paths_dbus = {
    "/Ac/ActiveIn/ActiveInput": {"initial": 0, "textformat": _n},
    "/Ac/ActiveIn/Connected": {"initial": 1, "textformat": _n},
    "/Ac/ActiveIn/CurrentLimit": {"initial": 16, "textformat": _a},
    "/Ac/ActiveIn/CurrentLimitIsAdjustable": {"initial": 1, "textformat": _n},
    # ----
    "/Ac/ActiveIn/L1/F": {"initial": None, "textformat": _hz},
    "/Ac/ActiveIn/L1/I": {"initial": None, "textformat": _a},
    "/Ac/ActiveIn/L1/P": {"initial": None, "textformat": _w},
    "/Ac/ActiveIn/L1/S": {"initial": None, "textformat": _va},
    "/Ac/ActiveIn/L1/V": {"initial": None, "textformat": _v},
    # ----
    "/Ac/ActiveIn/L2/F": {"initial": None, "textformat": _hz},
    "/Ac/ActiveIn/L2/I": {"initial": None, "textformat": _a},
    "/Ac/ActiveIn/L2/P": {"initial": None, "textformat": _w},
    "/Ac/ActiveIn/L2/S": {"initial": None, "textformat": _va},
    "/Ac/ActiveIn/L2/V": {"initial": None, "textformat": _v},
    # ----
    "/Ac/ActiveIn/L3/F": {"initial": None, "textformat": _hz},
    "/Ac/ActiveIn/L3/I": {"initial": None, "textformat": _a},
    "/Ac/ActiveIn/L3/P": {"initial": None, "textformat": _w},
    "/Ac/ActiveIn/L3/S": {"initial": None, "textformat": _va},
    "/Ac/ActiveIn/L3/V": {"initial": None, "textformat": _v},
    # ----
    "/Ac/ActiveIn/P": {"initial": 0, "textformat": _w},
    "/Ac/ActiveIn/S": {"initial": 0, "textformat": _va},
    # ----
    "/Ac/In/1/CurrentLimit": {"initial": 16, "textformat": _a},
    "/Ac/In/1/CurrentLimitIsAdjustable": {"initial": 1, "textformat": _n},
    # ----
    "/Ac/In/2/CurrentLimit": {"initial": None, "textformat": _a},
    "/Ac/In/2/CurrentLimitIsAdjustable": {"initial": None, "textformat": _n},
    # ----
    "/Ac/NumberOfAcInputs": {"initial": 1, "textformat": _n},
    "/Ac/NumberOfPhases": {"initial": 1, "textformat": _n},
    # ----
    "/Ac/Out/L1/F": {"initial": None, "textformat": _hz},
    "/Ac/Out/L1/I": {"initial": None, "textformat": _a},
    "/Ac/Out/L1/NominalInverterPower": {"initial": None, "textformat": _w},
    "/Ac/Out/L1/P": {"initial": None, "textformat": _w},
    "/Ac/Out/L1/S": {"initial": None, "textformat": _va},
    "/Ac/Out/L1/V": {"initial": None, "textformat": _v},
    # ----
    "/Ac/Out/L2/F": {"initial": None, "textformat": _hz},
    "/Ac/Out/L2/I": {"initial": None, "textformat": _a},
    "/Ac/Out/L2/NominalInverterPower": {"initial": None, "textformat": _w},
    "/Ac/Out/L2/P": {"initial": None, "textformat": _w},
    "/Ac/Out/L2/S": {"initial": None, "textformat": _va},
    "/Ac/Out/L2/V": {"initial": None, "textformat": _v},
    # ----
    "/Ac/Out/L3/F": {"initial": None, "textformat": _hz},
    "/Ac/Out/L3/I": {"initial": None, "textformat": _a},
    "/Ac/Out/L3/NominalInverterPower": {"initial": None, "textformat": _w},
    "/Ac/Out/L3/P": {"initial": None, "textformat": _w},
    "/Ac/Out/L3/S": {"initial": None, "textformat": _va},
    "/Ac/Out/L3/V": {"initial": None, "textformat": _v},
    # ----
    "/Ac/Out/NominalInverterPower": {"initial": 4500, "textformat": _w},
    "/Ac/Out/P": {"initial": 0, "textformat": _w},
    "/Ac/Out/S": {"initial": 0, "textformat": _va},
    # ----
    "/Ac/PowerMeasurementType": {"initial": 4, "textformat": _n},
    "/Ac/State/IgnoreAcIn1": {"initial": 0, "textformat": _n},
    "/Ac/State/SplitPhaseL2Passthru": {"initial": None, "textformat": _n},
    # ----
    "/Alarms/HighDcCurrent": {"initial": 0, "textformat": _n},
    "/Alarms/HighDcVoltage": {"initial": 0, "textformat": _n},
    "/Alarms/HighTemperature": {"initial": 0, "textformat": _n},
    "/Alarms/L1/HighTemperature": {"initial": 0, "textformat": _n},
    "/Alarms/L1/LowBattery": {"initial": 0, "textformat": _n},
    "/Alarms/L1/Overload": {"initial": 0, "textformat": _n},
    "/Alarms/L1/Ripple": {"initial": 0, "textformat": _n},
    "/Alarms/L2/HighTemperature": {"initial": 0, "textformat": _n},
    "/Alarms/L2/LowBattery": {"initial": 0, "textformat": _n},
    "/Alarms/L2/Overload": {"initial": 0, "textformat": _n},
    "/Alarms/L2/Ripple": {"initial": 0, "textformat": _n},
    "/Alarms/L3/HighTemperature": {"initial": 0, "textformat": _n},
    "/Alarms/L3/LowBattery": {"initial": 0, "textformat": _n},
    "/Alarms/L3/Overload": {"initial": 0, "textformat": _n},
    "/Alarms/L3/Ripple": {"initial": 0, "textformat": _n},
    "/Alarms/LowBattery": {"initial": 0, "textformat": _n},
    "/Alarms/Overload": {"initial": 0, "textformat": _n},
    "/Alarms/PhaseRotation": {"initial": 0, "textformat": _n},
    "/Alarms/Ripple": {"initial": 0, "textformat": _n},
    "/Alarms/TemperatureSensor": {"initial": 0, "textformat": _n},
    "/Alarms/VoltageSensor": {"initial": 0, "textformat": _n},
    # ----
    "/BatteryOperationalLimits/BatteryLowVoltage": {
        "initial": None,
        "textformat": _v,
    },
    "/BatteryOperationalLimits/MaxChargeCurrent": {
        "initial": None,
        "textformat": _a,
    },
    "/BatteryOperationalLimits/MaxChargeVoltage": {
        "initial": None,
        "textformat": _v,
    },
    "/BatteryOperationalLimits/MaxDischargeCurrent": {
        "initial": None,
        "textformat": _a,
    },
    "/BatterySense/Temperature": {"initial": None, "textformat": _c},
    "/BatterySense/Voltage": {"initial": None, "textformat": _v},
    # ----
    "/Bms/AllowToCharge": {"initial": 1, "textformat": _n},
    "/Bms/AllowToChargeRate": {"initial": 0, "textformat": _n},
    "/Bms/AllowToDischarge": {"initial": 1, "textformat": _n},
    "/Bms/BmsExpected": {"initial": 0, "textformat": _n},
    "/Bms/BmsType": {"initial": 0, "textformat": _n},
    "/Bms/Error": {"initial": 0, "textformat": _n},
    "/Bms/PreAlarm": {"initial": None, "textformat": _n},
    # ----
    "/Dc/0/Current": {"initial": None, "textformat": _a},
    "/Dc/0/MaxChargeCurrent": {"initial": None, "textformat": _a},
    "/Dc/0/Power": {"initial": None, "textformat": _w},
    "/Dc/0/Temperature": {"initial": None, "textformat": _c},
    "/Dc/0/Voltage": {"initial": None, "textformat": _v},
    # ----
    # '/Devices/0/Assistants': {'initial': 0, "textformat": _n},
    # ----
    "/Devices/0/ExtendStatus/ChargeDisabledDueToLowTemp": {
        "initial": 0,
        "textformat": _n,
    },
    "/Devices/0/ExtendStatus/ChargeIsDisabled": {"initial": None, "textformat": _n},
    "/Devices/0/ExtendStatus/GridRelayReport/Code": {
        "initial": None,
        "textformat": _n,
    },
    "/Devices/0/ExtendStatus/GridRelayReport/Count": {
        "initial": 0,
        "textformat": _n,
    },
    "/Devices/0/ExtendStatus/GridRelayReport/Reset": {
        "initial": 0,
        "textformat": _n,
    },
    "/Devices/0/ExtendStatus/HighDcCurrent": {"initial": 0, "textformat": _n},
    "/Devices/0/ExtendStatus/HighDcVoltage": {"initial": 0, "textformat": _n},
    "/Devices/0/ExtendStatus/IgnoreAcIn1": {"initial": 0, "textformat": _n},
    "/Devices/0/ExtendStatus/MainsPllLocked": {"initial": 1, "textformat": _n},
    "/Devices/0/ExtendStatus/PcvPotmeterOnZero": {"initial": 0, "textformat": _n},
    "/Devices/0/ExtendStatus/PowerPackPreOverload": {
        "initial": 0,
        "textformat": _n,
    },
    "/Devices/0/ExtendStatus/SocTooLowToInvert": {"initial": 0, "textformat": _n},
    "/Devices/0/ExtendStatus/SustainMode": {"initial": 0, "textformat": _n},
    "/Devices/0/ExtendStatus/SwitchoverInfo/Connecting": {
        "initial": 0,
        "textformat": _n,
    },
    "/Devices/0/ExtendStatus/SwitchoverInfo/Delay": {
        "initial": 0,
        "textformat": _n,
    },
    "/Devices/0/ExtendStatus/SwitchoverInfo/ErrorFlags": {
        "initial": 0,
        "textformat": _n,
    },
    "/Devices/0/ExtendStatus/TemperatureHighForceBypass": {
        "initial": 0,
        "textformat": _n,
    },
    "/Devices/0/ExtendStatus/VeBusNetworkQualityCounter": {
        "initial": 0,
        "textformat": _n,
    },
    "/Devices/0/ExtendStatus/WaitingForRelayTest": {"initial": 0, "textformat": _n},
    # ----
    "/Devices/0/InterfaceProtectionLog/0/ErrorFlags": {
        "initial": None,
        "textformat": _n,
    },
    "/Devices/0/InterfaceProtectionLog/0/Time": {"initial": None, "textformat": _n},
    "/Devices/0/InterfaceProtectionLog/1/ErrorFlags": {
        "initial": None,
        "textformat": _n,
    },
    "/Devices/0/InterfaceProtectionLog/1/Time": {"initial": None, "textformat": _n},
    "/Devices/0/InterfaceProtectionLog/2/ErrorFlags": {
        "initial": None,
        "textformat": _n,
    },
    "/Devices/0/InterfaceProtectionLog/2/Time": {"initial": None, "textformat": _n},
    "/Devices/0/InterfaceProtectionLog/3/ErrorFlags": {
        "initial": None,
        "textformat": _n,
    },
    "/Devices/0/InterfaceProtectionLog/3/Time": {"initial": None, "textformat": _n},
    "/Devices/0/InterfaceProtectionLog/4/ErrorFlags": {
        "initial": None,
        "textformat": _n,
    },
    "/Devices/0/InterfaceProtectionLog/4/Time": {"initial": None, "textformat": _n},
    # ----
    "/Devices/0/SerialNumber": {"initial": "HQ00000AA01", "textformat": _s},
    "/Devices/0/Version": {"initial": 2623497, "textformat": _s},
    # ----
    "/Devices/Bms/Version": {"initial": None, "textformat": _s},
    "/Devices/Dmc/Version": {"initial": None, "textformat": _s},
    "/Devices/NumberOfMultis": {"initial": 1, "textformat": _n},
    # ----
    "/Energy/AcIn1ToAcOut": {"initial": 0, "textformat": _n},
    "/Energy/AcIn1ToInverter": {"initial": 0, "textformat": _n},
    "/Energy/AcIn2ToAcOut": {"initial": 0, "textformat": _n},
    "/Energy/AcIn2ToInverter": {"initial": 0, "textformat": _n},
    "/Energy/AcOutToAcIn1": {"initial": 0, "textformat": _n},
    "/Energy/AcOutToAcIn2": {"initial": 0, "textformat": _n},
    "/Energy/InverterToAcIn1": {"initial": 0, "textformat": _n},
    "/Energy/InverterToAcIn2": {"initial": 0, "textformat": _n},
    "/Energy/InverterToAcOut": {"initial": 0, "textformat": _n},
    "/Energy/OutToInverter": {"initial": 0, "textformat": _n},
    "/ExtraBatteryCurrent": {"initial": 0, "textformat": _n},
    # ----
    "/FirmwareFeatures/BolFrame": {"initial": 1, "textformat": _n},
    "/FirmwareFeatures/BolUBatAndTBatSense": {"initial": 1, "textformat": _n},
    "/FirmwareFeatures/CommandWriteViaId": {"initial": 1, "textformat": _n},
    "/FirmwareFeatures/IBatSOCBroadcast": {"initial": 1, "textformat": _n},
    "/FirmwareFeatures/NewPanelFrame": {"initial": 1, "textformat": _n},
    "/FirmwareFeatures/SetChargeState": {"initial": 1, "textformat": _n},
    "/FirmwareSubVersion": {"initial": 0, "textformat": _n},
    # ----
    "/Hub/ChargeVoltage": {"initial": 55.2, "textformat": _n},
    "/Hub4/AssistantId": {"initial": 5, "textformat": _n},
    "/Hub4/DisableCharge": {"initial": 0, "textformat": _n},
    "/Hub4/DisableFeedIn": {"initial": 0, "textformat": _n},
    "/Hub4/DoNotFeedInOvervoltage": {"initial": 1, "textformat": _n},
    "/Hub4/FixSolarOffsetTo100mV": {"initial": 1, "textformat": _n},
    "/Hub4/L1/AcPowerSetpoint": {"initial": 0, "textformat": _n},
    "/Hub4/L1/CurrentLimitedDueToHighTemp": {"initial": 0, "textformat": _n},
    "/Hub4/L1/FrequencyVariationOccurred": {"initial": 0, "textformat": _n},
    "/Hub4/L1/MaxFeedInPower": {"initial": 32766, "textformat": _n},
    "/Hub4/L1/OffsetAddedToVoltageSetpoint": {"initial": 0, "textformat": _n},
    "/Hub4/Sustain": {"initial": 0, "textformat": _n},
    "/Hub4/TargetPowerIsMaxFeedIn": {"initial": 0, "textformat": _n},
    # ----
    # '/Interfaces/Mk2/Connection': {'initial': '/dev/ttyS3', "textformat": _n},
    # '/Interfaces/Mk2/ProductId': {'initial': 4464, "textformat": _n},
    # '/Interfaces/Mk2/ProductName': {'initial': 'MK3', "textformat": _n},
    # '/Interfaces/Mk2/Status/BusFreeMode': {'initial': 1, "textformat": _n},
    # '/Interfaces/Mk2/Tunnel': {'initial': None, "textformat": _n},
    # '/Interfaces/Mk2/Version': {'initial': 1170212, "textformat": _n},
    # ----
    "/Leds/Absorption": {"initial": 0, "textformat": _n},
    "/Leds/Bulk": {"initial": 0, "textformat": _n},
    "/Leds/Float": {"initial": 0, "textformat": _n},
    "/Leds/Inverter": {"initial": 1, "textformat": _n},
    "/Leds/LowBattery": {"initial": 0, "textformat": _n},
    "/Leds/Mains": {"initial": 1, "textformat": _n},
    "/Leds/Overload": {"initial": 0, "textformat": _n},
    "/Leds/Temperature": {"initial": 0, "textformat": _n},
    "/Mode": {"initial": 3, "textformat": _n},
    "/ModeIsAdjustable": {"initial": 1, "textformat": _n},
    "/PvInverter/Disable": {"initial": 1, "textformat": _n},
    "/Quirks": {"initial": 0, "textformat": _n},
    "/RedetectSystem": {"initial": 0, "textformat": _n},
    "/Settings/Alarm/System/GridLost": {"initial": 1, "textformat": _n},
    "/Settings/SystemSetup/AcInput1": {"initial": 1, "textformat": _n},
    "/Settings/SystemSetup/AcInput2": {"initial": 0, "textformat": _n},
    "/ShortIds": {"initial": 1, "textformat": _n},
    "/Soc": {"initial": None, "textformat": _percent},
    "/State": {"initial": 3, "textformat": _n},
    "/SystemReset": {"initial": None, "textformat": _n},
    "/VebusChargeState": {"initial": 1, "textformat": _n},
    "/VebusError": {"initial": 0, "textformat": _n},
    "/VebusMainState": {"initial": 9, "textformat": _n},
    # ----
    "/UpdateIndex": {"initial": 0, "textformat": _n},
}