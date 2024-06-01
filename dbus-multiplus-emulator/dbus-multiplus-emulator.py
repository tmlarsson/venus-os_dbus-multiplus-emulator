#!/usr/bin/env python

from gi.repository import GLib
import platform
import logging
import sys
import os
import _thread
from time import time
import json
from paths import paths_dbus

# import Victron Energy packages
sys.path.insert(1, os.path.join(os.path.dirname(__file__), "ext", "velib_python"))
from vedbus import VeDbusService
from dbusmonitor import DbusMonitor
from dbus import Error

# Configure logging
log_dir = os.path.dirname(os.path.realpath(__file__))
log_file = os.path.join(log_dir, "current.log")

logging.basicConfig(
    format='%(asctime)s,%(msecs)d %(name)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)


# ------------------ USER CHANGABLE VALUES | START ------------------

# enter grid frequency
grid_frequency = 50.0000

# enter the dbusServiceName from which the battery data should be fetched, if there is more than one
# e.g. com.victronenergy.battery.mqtt_battery_41
dbusServiceNameBattery = ""

# enter the dbusServiceName from which the grid meter data should be fetched, if there is more than one
# e.g. com.victronenergy.grid.mqtt_grid_31
dbusServiceNameGrid = ""

# specify on which phase the AC PV Inverter is connected
# e.g. L1, L2 or L3
# default: L1
phases = ["L1", "L2", "L3"]

# ------------------ USER CHANGABLE VALUES | END --------------------


# create dictionary for later to count watt hours
data_watt_hours = {"time_creation": int(time()), "count": 0}
# calculate and save watthours after every x seconds
data_watt_hours_timespan = 60
# save file to non volatile storage after x seconds
data_watt_hours_save = 900
# file to save watt hours on persistent storage
data_watt_hours_storage_file = "/data/etc/dbus-multiplus-emulator/data_watt_hours.json"
# file to save many writing operations (best on ramdisk to not wear SD card)
data_watt_hours_working_file = (
    "/var/volatile/tmp/dbus-multiplus-emulator_data_watt_hours.json"
)
# get last modification timestamp
timestamp_storage_file = (
    os.path.getmtime(data_watt_hours_storage_file)
    if os.path.isfile(data_watt_hours_storage_file)
    else 0
)

# load data to prevent sending 0 watthours for OutToInverter (charging)/InverterToOut (discharging) before the first loop
# check if file in volatile storage exists
if os.path.isfile(data_watt_hours_working_file):
    with open(data_watt_hours_working_file, "r") as file:
        file = open(data_watt_hours_working_file, "r")
        json_data = json.load(file)
        logging.info(
            "Loaded JSON for OutToInverter (charging)/InverterToOut (discharging) once"
        )
        logging.debug(json.dumps(json_data))
# if not, check if file in persistent storage exists
elif os.path.isfile(data_watt_hours_storage_file):
    with open(data_watt_hours_storage_file, "r") as file:
        file = open(data_watt_hours_storage_file, "r")
        json_data = json.load(file)
        logging.info(
            "Loaded JSON for OutToInverter (charging)/InverterToOut (discharging) once from persistent storage"
        )
        logging.debug(json.dumps(json_data))
else:
    json_data = {}


class DbusMultiPlusEmulator:
    def __init__(
        self,
        servicename,
        deviceinstance,
        paths,
        productname="MultiPlus-II xx/5000/xx-xx (emulated)",
        connection="VE.Bus",
    ):
        self._dbusservice = VeDbusService(servicename)
        self._paths = paths

        logging.debug("%s /DeviceInstance = %d" % (servicename, deviceinstance))

        # Create the management objects, as specified in the ccgx dbus-api document
        self._dbusservice.add_path("/Mgmt/ProcessName", __file__)  # ok
        self._dbusservice.add_path(
            "/Mgmt/ProcessVersion",
            "Unkown version, and running on Python " + platform.python_version(),
        )  # ok
        self._dbusservice.add_path("/Mgmt/Connection", connection)  # ok

        # Create the mandatory objects
        self._dbusservice.add_path("/DeviceInstance", deviceinstance)  # ok
        self._dbusservice.add_path("/ProductId", 2623)  # ok
        self._dbusservice.add_path("/ProductName", productname)  # ok
        self._dbusservice.add_path("/CustomName", "")  # ok
        self._dbusservice.add_path("/FirmwareVersion", 1175)  # ok
        self._dbusservice.add_path("/HardwareVersion", "0.0.3 (20230821)")
        self._dbusservice.add_path("/Connected", 1)  # ok

        # self._dbusservice.add_path('/Latency', None)
        # self._dbusservice.add_path('/ErrorCode', 0)
        # self._dbusservice.add_path('/Position', 0)
        # self._dbusservice.add_path('/StatusCode', 0)

        for path, settings in self._paths.items():
            self._dbusservice.add_path(
                path,
                settings["initial"],
                gettextcallback=settings["textformat"],
                writeable=True,
                onchangecallback=self._handlechangedvalue,
            )

        # ### read values from battery
        # Why this dummy? Because DbusMonitor expects these values to be there, even though we don't
        # need them. So just add some dummy data. This can go away when DbusMonitor is more generic.
        dummy = {"code": None, "whenToLog": "configChange", "accessLevel": None}
        dbus_tree = {}

        dbus_tree.update(
            {
                "com.victronenergy.battery": {
                    # "/Connected": dummy,
                    # "/ProductName": dummy,
                    # "/Mgmt/Connection": dummy,
                    # "/DeviceInstance": dummy,
                    "/Dc/0/Current": dummy,
                    "/Dc/0/Power": dummy,
                    "/Dc/0/Temperature": dummy,
                    "/Dc/0/Voltage": dummy,
                    "/Soc": dummy,
                    # '/Sense/Current': dummy,
                    # '/TimeToGo': dummy,
                    # '/ConsumedAmphours': dummy,
                    # '/ProductId': dummy,
                    # '/CustomName': dummy,
                    "/Info/ChargeMode": dummy,
                    "/Info/MaxChargeCurrent": dummy,
                    "/Info/MaxChargeVoltage": dummy,
                    "/Info/MaxDischargeCurrent": dummy,
                }
            }
        )
        # create empty dictionary will be updated later
        self.batteryValues = {
            "/Dc/0/Current": None,
            "/Dc/0/Power": None,
            "/Dc/0/Temperature": None,
            "/Dc/0/Voltage": None,
            "/Soc": None,
            "/Info/ChargeMode": "",
            "/Info/MaxChargeCurrent": None,
            "/Info/MaxChargeVoltage": None,
            "/Info/MaxDischargeCurrent": None,
        }

        dbus_tree.update(
            {
                "com.victronenergy.grid": {
                    # '/Connected': dummy,
                    # '/ProductName': dummy,
                    # '/Mgmt/Connection': dummy,
                    # '/ProductId' : dummy,
                    # '/DeviceType' : dummy,
                    "/Ac/L1/Power": dummy,
                    "/Ac/L2/Power": dummy,
                    "/Ac/L3/Power": dummy,
                    "/Ac/L1/Current": dummy,
                    "/Ac/L2/Current": dummy,
                    "/Ac/L3/Current": dummy,
                    "/Ac/L1/Voltage": dummy,
                    "/Ac/L2/Voltage": dummy,
                    "/Ac/L3/Voltage": dummy,
                    # ---
                    "/Ac/Power": dummy,
                    "/Ac/Current": dummy,
                    "/Ac/Voltage": dummy,
                }
            }
        )
       

        # create empty dictionary will be updated later
        self.gridValues = {
            "/Ac/L1/Power": None,
            "/Ac/L2/Power": None,
            "/Ac/L3/Power": None,
            "/Ac/L1/Current": None,
            "/Ac/L2/Current": None,
            "/Ac/L3/Current": None,
            "/Ac/L1/Voltage": None,
            "/Ac/L2/Voltage": None,
            "/Ac/L3/Voltage": None,
            # ---
            "/Ac/Power": None,
            "/Ac/Current": None,
            "/Ac/Voltage": None,
        }

        """
        dbus_tree.update({
            "com.victronenergy.system": {
                "/Dc/Battery/BatteryService": dummy,
                "/Dc/Battery/ConsumedAmphours": dummy,
                "/Dc/Battery/Current": dummy,
                "/Dc/Battery/Power": dummy,
                "/Dc/Battery/ProductId": dummy,
                "/Dc/Battery/Soc": dummy,
                "/Dc/Battery/State": dummy,
                "/Dc/Battery/Temperature": dummy,
                "/Dc/Battery/TemperatureService": dummy,
                "/Dc/Battery/TimeToGo": dummy,
                "/Dc/Battery/Voltage": dummy,
                "/Dc/Battery/VoltageService": dummy,
            },
        })
        """

        # self._dbusreadservice = DbusMonitor('com.victronenergy.battery.zero')
        self._dbusmonitor = self._create_dbus_monitor(
            dbus_tree,
            valueChangedCallback=self._dbus_value_changed,
            deviceAddedCallback=self._device_added,
            deviceRemovedCallback=self._device_removed,
        )

        GLib.timeout_add(1000, self._update)  # pause 1000ms before the next request

    def _create_dbus_monitor(self, *args, **kwargs):
        return DbusMonitor(*args, **kwargs)

    def _dbus_value_changed(
        self, dbusServiceName, dbusPath, dict, changes, deviceInstance
    ):
        self._changed = True

        if (
            dbusServiceNameBattery == ""
            and dbusServiceName.startswith("com.victronenergy.battery")
        ) or (
            dbusServiceNameBattery != "" and dbusServiceName == dbusServiceNameBattery
        ):
            self.batteryValues.update({str(dbusPath): changes["Value"]})

        if (
            dbusServiceNameGrid == ""
            and dbusServiceName.startswith("com.victronenergy.grid")
        ) or (dbusServiceNameGrid != "" and dbusServiceName == dbusServiceNameGrid):
            self.gridValues.update({str(dbusPath): changes["Value"]})
            

    def _device_added(self, service, instance, do_service_change=True):
        pass

    def _device_removed(self, service, instance):
        pass
            
    def _update(self):
        logging.info("Updating dbus values...")
        ac_in_power = {phase: self.gridValues.get(f"/Ac/{phase}/Power", 0) for phase in phases}
        ac_in_voltage = {phase: self.gridValues.get(f"/Ac/{phase}/Voltage", 0) for phase in phases}      

        # Ac out power is always the same a the grid power as we do not have a ac in pv inverter
        # or any battery which could be inverted to ac
        ac_out_power = {phase: ac_in_power[phase] for phase in phases}
        
        ac_in = {}
        for phase in phases:
            try:
                ac_in[phase] = {
                    "current": round(ac_in_power[phase] / ac_in_voltage[phase], 2) if ac_in_voltage[phase] > 0 else 0,
                    "power": ac_in_power[phase],
                    "voltage": ac_in_voltage[phase],
                }
            except ZeroDivisionError:
                logging.error(f"ZeroDivisionError for phase {phase}: voltage is zero")
                ac_in[phase] = {
                    "current": 0,
                    "power": ac_in_power[phase],
                    "voltage": ac_in_voltage[phase],
                }

        ac_out = {}
        for phase in phases:
            try:
                ac_out[phase] = {
                    "current": round(ac_out_power[phase] / ac_in_voltage[phase], 2) if ac_in_voltage[phase] > 0 else 0,
                    "power": ac_out_power[phase],
                    "voltage": ac_in_voltage[phase],
                }
            except ZeroDivisionError:
                logging.error(f"ZeroDivisionError for phase {phase}: voltage is zero")
                ac_out[phase] = {
                    "current": 0,
                    "power": ac_out_power[phase],
                    "voltage": ac_in_voltage[phase],
                }


        try:
            self._dbusservice["/Ac/ActiveIn/ActiveInput"] = 0
            self._dbusservice["/Ac/ActiveIn/Connected"] = 1
            self._dbusservice["/Ac/ActiveIn/CurrentLimit"] = 16
            self._dbusservice["/Ac/ActiveIn/CurrentLimitIsAdjustable"] = 1
            self._dbusservice["/Ac/NumberOfAcInputs"] = 1
            self._dbusservice["/Ac/NumberOfPhases"] = 3
            self._dbusservice["/Ac/Out/NominalInverterPower"] = 4500
        except Exception as e:
            logging.error("Error updating dbus values: %s" % str(e))

        
        logging.info("Updating dbus values...")

        for phase in phases:
            self._dbusservice[f"/Ac/ActiveIn/{phase}/F"] = grid_frequency
            self._dbusservice[f"/Ac/ActiveIn/{phase}/I"] = ac_in[phase]["current"]
            self._dbusservice[f"/Ac/ActiveIn/{phase}/P"] = ac_in[phase]["power"]
            self._dbusservice[f"/Ac/ActiveIn/{phase}/S"] = ac_in[phase]["power"]
            self._dbusservice[f"/Ac/ActiveIn/{phase}/V"] = ac_in[phase]["voltage"]

            self._dbusservice[f"/Ac/Out/{phase}/F"] = grid_frequency
            self._dbusservice[f"/Ac/Out/{phase}/I"] = ac_out[phase]["current"]
            self._dbusservice[f"/Ac/Out/{phase}/NominalInverterPower"] = 4500
            self._dbusservice[f"/Ac/Out/{phase}/P"] = ac_out[phase]["power"]
            self._dbusservice[f"/Ac/Out/{phase}/S"] = ac_out[phase]["power"]
            self._dbusservice[f"/Ac/Out/{phase}/V"] = ac_out[phase]["voltage"]
            

        # Overall values
        self._dbusservice["/Ac/ActiveIn/P"] = sum(ac_in_power.values())
        self._dbusservice["/Ac/ActiveIn/S"] = sum(ac_in_power.values())
        self._dbusservice["/Ac/Out/P"] = sum(ac_out_power.values())
        self._dbusservice["/Ac/Out/S"] = sum(ac_out_power.values())

        self._dbusservice["/Ac/PowerMeasurementType"] = 4
        self._dbusservice["/Ac/State/IgnoreAcIn1"] = 0
        self._dbusservice["/Ac/State/SplitPhaseL2Passthru"] = None

        self._dbusservice["/Alarms/HighDcCurrent"] = 0
        self._dbusservice["/Alarms/HighDcVoltage"] = 0
        self._dbusservice["/Alarms/HighTemperature"] = 0
        self._dbusservice["/Alarms/L1/HighTemperature"] = 0
        self._dbusservice["/Alarms/L1/LowBattery"] = 0
        self._dbusservice["/Alarms/L1/Overload"] = 0
        self._dbusservice["/Alarms/L1/Ripple"] = 0
        self._dbusservice["/Alarms/L2/HighTemperature"] = 0
        self._dbusservice["/Alarms/L2/LowBattery"] = 0
        self._dbusservice["/Alarms/L2/Overload"] = 0
        self._dbusservice["/Alarms/L2/Ripple"] = 0
        self._dbusservice["/Alarms/L3/HighTemperature"] = 0
        self._dbusservice["/Alarms/L3/LowBattery"] = 0
        self._dbusservice["/Alarms/L3/Overload"] = 0
        self._dbusservice["/Alarms/L3/Ripple"] = 0
        self._dbusservice["/Alarms/LowBattery"] = 0
        self._dbusservice["/Alarms/Overload"] = 0
        self._dbusservice["/Alarms/PhaseRotation"] = 0
        self._dbusservice["/Alarms/Ripple"] = 0
        self._dbusservice["/Alarms/TemperatureSensor"] = 0
        self._dbusservice["/Alarms/VoltageSensor"] = 0

        self._dbusservice["/BatteryOperationalLimits/BatteryLowVoltage"] = None
        self._dbusservice[
            "/BatteryOperationalLimits/MaxChargeCurrent"
        ] = self.batteryValues["/Info/MaxChargeCurrent"]
        self._dbusservice[
            "/BatteryOperationalLimits/MaxChargeVoltage"
        ] = self.batteryValues["/Info/MaxChargeVoltage"]
        self._dbusservice[
            "/BatteryOperationalLimits/MaxDischargeCurrent"
        ] = self.batteryValues["/Info/MaxDischargeCurrent"]
        self._dbusservice["/BatterySense/Temperature"] = None
        self._dbusservice["/BatterySense/Voltage"] = None

        self._dbusservice["/Bms/AllowToCharge"] = 1
        self._dbusservice["/Bms/AllowToChargeRate"] = 0
        self._dbusservice["/Bms/AllowToDischarge"] = 1
        self._dbusservice["/Bms/BmsExpected"] = 0
        self._dbusservice["/Bms/BmsType"] = 0
        self._dbusservice["/Bms/Error"] = 0
        self._dbusservice["/Bms/PreAlarm"] = None

        # get values from BMS
        # for bubble flow in GUI
        self._dbusservice["/Dc/0/Current"] = self.batteryValues["/Dc/0/Current"]
        self._dbusservice["/Dc/0/MaxChargeCurrent"] = self.batteryValues[
            "/Info/MaxChargeCurrent"
        ]
        self._dbusservice["/Dc/0/Power"] = self.batteryValues["/Dc/0/Power"]
        self._dbusservice["/Dc/0/Temperature"] = self.batteryValues["/Dc/0/Temperature"]
        self._dbusservice["/Dc/0/Voltage"] = (
            self.batteryValues["/Dc/0/Voltage"]
            if self.batteryValues["/Dc/0/Voltage"] is not None
            else round(
                self.batteryValues["/Dc/0/Power"] / self.batteryValues["/Dc/0/Current"],
                2,
            )
            if self.batteryValues["/Dc/0/Power"] is not None
            and self.batteryValues["/Dc/0/Current"] is not None
            else None
        )

        # self._dbusservice['/Devices/0/Assistants'] = 0

        self._dbusservice["/Devices/0/ExtendStatus/ChargeDisabledDueToLowTemp"] = 0
        self._dbusservice["/Devices/0/ExtendStatus/ChargeIsDisabled"] = None
        self._dbusservice["/Devices/0/ExtendStatus/GridRelayReport/Code"] = None
        self._dbusservice["/Devices/0/ExtendStatus/GridRelayReport/Count"] = 0
        self._dbusservice["/Devices/0/ExtendStatus/GridRelayReport/Reset"] = 0
        self._dbusservice["/Devices/0/ExtendStatus/HighDcCurrent"] = 0
        self._dbusservice["/Devices/0/ExtendStatus/HighDcVoltage"] = 0
        self._dbusservice["/Devices/0/ExtendStatus/IgnoreAcIn1"] = 0
        self._dbusservice["/Devices/0/ExtendStatus/MainsPllLocked"] = 1
        self._dbusservice["/Devices/0/ExtendStatus/PcvPotmeterOnZero"] = 0
        self._dbusservice["/Devices/0/ExtendStatus/PowerPackPreOverload"] = 0
        self._dbusservice["/Devices/0/ExtendStatus/SocTooLowToInvert"] = 0
        self._dbusservice["/Devices/0/ExtendStatus/SustainMode"] = 0
        self._dbusservice["/Devices/0/ExtendStatus/SwitchoverInfo/Connecting"] = 0
        self._dbusservice["/Devices/0/ExtendStatus/SwitchoverInfo/Delay"] = 0
        self._dbusservice["/Devices/0/ExtendStatus/SwitchoverInfo/ErrorFlags"] = 0
        self._dbusservice["/Devices/0/ExtendStatus/TemperatureHighForceBypass"] = 0
        self._dbusservice["/Devices/0/ExtendStatus/VeBusNetworkQualityCounter"] = 0
        self._dbusservice["/Devices/0/ExtendStatus/WaitingForRelayTest"] = 0

        self._dbusservice["/Devices/0/InterfaceProtectionLog/0/ErrorFlags"] = None
        self._dbusservice["/Devices/0/InterfaceProtectionLog/0/Time"] = None
        self._dbusservice["/Devices/0/InterfaceProtectionLog/1/ErrorFlags"] = None
        self._dbusservice["/Devices/0/InterfaceProtectionLog/1/Time"] = None
        self._dbusservice["/Devices/0/InterfaceProtectionLog/2/ErrorFlags"] = None
        self._dbusservice["/Devices/0/InterfaceProtectionLog/2/Time"] = None
        self._dbusservice["/Devices/0/InterfaceProtectionLog/3/ErrorFlags"] = None
        self._dbusservice["/Devices/0/InterfaceProtectionLog/3/Time"] = None
        self._dbusservice["/Devices/0/InterfaceProtectionLog/4/ErrorFlags"] = None
        self._dbusservice["/Devices/0/InterfaceProtectionLog/4/Time"] = None

        self._dbusservice["/Devices/0/SerialNumber"] = "HQ00000AA01"
        self._dbusservice["/Devices/0/Version"] = 2623497

        self._dbusservice["/Devices/Bms/Version"] = None
        self._dbusservice["/Devices/Dmc/Version"] = None
        self._dbusservice["/Devices/NumberOfMultis"] = 1

        # self._dbusservice["/Energy/AcIn1ToAcOut"] = 0
        # self._dbusservice["/Energy/AcIn1ToInverter"] = 0
        # self._dbusservice["/Energy/AcIn2ToAcOut"] = 0
        # self._dbusservice["/Energy/AcIn2ToInverter"] = 0
        # self._dbusservice["/Energy/AcOutToAcIn1"] = 0
        # self._dbusservice["/Energy/AcOutToAcIn2"] = 0
        # self._dbusservice["/Energy/InverterToAcIn1"] = 0
        # self._dbusservice["/Energy/InverterToAcIn2"] = 0
        self._dbusservice["/Energy/InverterToAcOut"] = (
            json_data["dc"]["discharging"]
            if "dc" in json_data and "discharging" in json_data["dc"]
            else 0
        )
        self._dbusservice["/Energy/OutToInverter"] = (
            json_data["dc"]["charging"]
            if "dc" in json_data and "charging" in json_data["dc"]
            else 0
        )
        # self._dbusservice["/ExtraBatteryCurrent"] = 0

        self._dbusservice["/FirmwareFeatures/BolFrame"] = 1
        self._dbusservice["/FirmwareFeatures/BolUBatAndTBatSense"] = 1
        self._dbusservice["/FirmwareFeatures/CommandWriteViaId"] = 1
        self._dbusservice["/FirmwareFeatures/IBatSOCBroadcast"] = 1
        self._dbusservice["/FirmwareFeatures/NewPanelFrame"] = 1
        self._dbusservice["/FirmwareFeatures/SetChargeState"] = 1
        self._dbusservice["/FirmwareSubVersion"] = 0

        self._dbusservice["/Hub/ChargeVoltage"] = 55.2
        self._dbusservice["/Hub4/AssistantId"] = 5
        self._dbusservice["/Hub4/DisableCharge"] = 0
        self._dbusservice["/Hub4/DisableFeedIn"] = 0
        self._dbusservice["/Hub4/DoNotFeedInOvervoltage"] = 1
        self._dbusservice["/Hub4/FixSolarOffsetTo100mV"] = 1
        self._dbusservice["/Hub4/L1/AcPowerSetpoint"] = 0
        self._dbusservice["/Hub4/L1/CurrentLimitedDueToHighTemp"] = 0
        self._dbusservice["/Hub4/L1/FrequencyVariationOccurred"] = 0
        self._dbusservice["/Hub4/L1/MaxFeedInPower"] = 32766
        self._dbusservice["/Hub4/L1/OffsetAddedToVoltageSetpoint"] = 0
        self._dbusservice["/Hub4/Sustain"] = 0
        self._dbusservice["/Hub4/TargetPowerIsMaxFeedIn"] = 0

        # '/Interfaces/Mk2/Connection'] = '/dev/ttyS3'
        # '/Interfaces/Mk2/ProductId'] = 4464
        # '/Interfaces/Mk2/ProductName'] = 'MK3'
        # '/Interfaces/Mk2/Status/BusFreeMode'] = 1
        # '/Interfaces/Mk2/Tunnel'] = None
        # '/Interfaces/Mk2/Version'] = 1170212

        self._dbusservice["/Leds/Absorption"] = (
            1 if self.batteryValues["/Info/ChargeMode"].startswith("Absorption") else 0
        )
        self._dbusservice["/Leds/Bulk"] = (
            1 if self.batteryValues["/Info/ChargeMode"].startswith("Bulk") else 0
        )
        self._dbusservice["/Leds/Float"] = (
            1 if self.batteryValues["/Info/ChargeMode"].startswith("Float") else 0
        )
        self._dbusservice["/Leds/Inverter"] = 1
        self._dbusservice["/Leds/LowBattery"] = 0
        self._dbusservice["/Leds/Mains"] = 1
        self._dbusservice["/Leds/Overload"] = 0
        self._dbusservice["/Leds/Temperature"] = 0

        self._dbusservice["/Mode"] = 3
        self._dbusservice["/ModeIsAdjustable"] = 1
        # self._dbusservice["/PvInverter/Disable"] = 0
        self._dbusservice["/Quirks"] = 0
        self._dbusservice["/RedetectSystem"] = 0
        self._dbusservice["/Settings/Alarm/System/GridLost"] = 1
        self._dbusservice["/Settings/SystemSetup/AcInput1"] = 1
        self._dbusservice["/Settings/SystemSetup/AcInput2"] = 0
        self._dbusservice["/ShortIds"] = 1
        self._dbusservice["/Soc"] = self.batteryValues["/Soc"]
        self._dbusservice["/State"] = 8
        self._dbusservice["/SystemReset"] = None
        self._dbusservice["/VebusChargeState"] = 1
        self._dbusservice["/VebusError"] = 0
        self._dbusservice["/VebusMainState"] = 9

        # increment UpdateIndex - to show that new data is available
        index = self._dbusservice["/UpdateIndex"] + 1  # increment index
        if index > 255:  # maximum value of the index
            index = 0  # overflow from 255 to 0
        self._dbusservice["/UpdateIndex"] = index

        return True

    def _handlechangedvalue(self, path, value):
        logging.debug("someone else updated %s to %s" % (path, value))
        return True  # accept the change


def main():
    _thread.daemon = True  # allow the program to quit

    from dbus.mainloop.glib import DBusGMainLoop

    # Have a mainloop, so we can send/receive asynchronous calls to and from dbus
    DBusGMainLoop(set_as_default=True)

    DbusMultiPlusEmulator(
        servicename="com.victronenergy.vebus.ttyS3",
        deviceinstance=275,
        paths=paths_dbus,
    )

    logging.info(
        "Connected to dbus and switching over to GLib.MainLoop() (= event based)"
    )
    
    try: 
        mainloop = GLib.MainLoop()
        mainloop.run()
    except Error as e:
        logging.error("Error in mainloop: %s" % str(e))
        mainloop.quit()

if __name__ == "__main__":
    main()
