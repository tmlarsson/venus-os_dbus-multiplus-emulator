#!/usr/bin/env python

from gi.repository import GLib
import platform
import logging
import sys
import os
from time import time
import json

# import Victron Energy packages
sys.path.insert(1, os.path.join(os.path.dirname(__file__), "ext", "velib_python"))
from vedbus import VeDbusService
from dbusmonitor import DbusMonitor
from ac_power import (
    as_number,
    calculate_multi_ac_power,
    energy_flows,
    multi_dc_power,
    phase_power_or_total,
    pv_power_on_input_and_output,
)

logging.basicConfig(
    format="%(asctime)s,%(msecs)d %(name)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
    handlers=[logging.StreamHandler()],
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

# phases present on the grid meter / Multi
# e.g. ["L1"] or ["L1", "L2", "L3"]
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
def _load_energy_json(path):
    try:
        with open(path, "r") as handle:
            return json.load(handle)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        logging.warning("Could not load %s: %s", path, error)
        return {}


def _atomic_write_json(path, payload):
    directory = os.path.dirname(path)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w") as handle:
        json.dump(payload, handle)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp_path, path)


timestamp_storage_file = (
    os.path.getmtime(data_watt_hours_storage_file)
    if os.path.isfile(data_watt_hours_storage_file)
    else 0
)

if os.path.isfile(data_watt_hours_working_file):
    json_data = _load_energy_json(data_watt_hours_working_file)
    logging.info("Loaded JSON energy counters from volatile storage")
elif os.path.isfile(data_watt_hours_storage_file):
    json_data = _load_energy_json(data_watt_hours_storage_file)
    logging.info("Loaded JSON energy counters from persistent storage")
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
            "Unknown version, and running on Python " + platform.python_version(),
        )  # ok
        self._dbusservice.add_path("/Mgmt/Connection", connection)  # ok

        # Create the mandatory objects
        self._dbusservice.add_path("/DeviceInstance", deviceinstance)  # ok
        self._dbusservice.add_path("/ProductId", 2623)  # ok
        self._dbusservice.add_path("/ProductName", productname)  # ok
        self._dbusservice.add_path("/CustomName", "")  # ok
        self._dbusservice.add_path("/FirmwareVersion", 1175)  # ok
        self._dbusservice.add_path("/HardwareVersion", "0.0.5 (20260907)")
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
        dbus_tree.update(
            {
                "com.victronenergy.pvinverter": {
                    "/Position": dummy,
                    "/Ac/L1/Power": dummy,
                    "/Ac/L2/Power": dummy,
                    "/Ac/L3/Power": dummy,
                    "/Ac/Power": dummy,
                }
            }
        )
        dbus_tree.update(
            {
                "com.victronenergy.solarcharger": {
                    "/Dc/0/Voltage": dummy,
                    "/Dc/0/Current": dummy,
                }
            }
        )
        dbus_tree.update(
            {
                "com.victronenergy.dcsystem": {
                    "/Dc/0/Power": dummy,
                }
            }
        )

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

    def _device_added(self, service, instance, do_service_change=True):
        pass

    def _device_removed(self, service, instance):
        pass

    def _pick_service(self, class_name, configured_name=""):
        services = self._dbusmonitor.get_service_list(class_name)
        if configured_name:
            return configured_name if configured_name in services else None
        if not services:
            return None
        return sorted(services.items(), key=lambda item: item[1])[0][0]

    def _read_grid(self):
        service = self._pick_service("com.victronenergy.grid", dbusServiceNameGrid)
        power = {}
        voltage = {}
        for phase in phases:
            if service:
                power[phase] = self._dbusmonitor.get_value(
                    service, "/Ac/%s/Power" % phase
                )
                voltage[phase] = self._dbusmonitor.get_value(
                    service, "/Ac/%s/Voltage" % phase
                )
            else:
                power[phase] = None
                voltage[phase] = None
        return power, voltage

    def _read_battery(self):
        service = self._pick_service("com.victronenergy.battery", dbusServiceNameBattery)
        paths = (
            "/Dc/0/Current",
            "/Dc/0/Power",
            "/Dc/0/Temperature",
            "/Dc/0/Voltage",
            "/Soc",
            "/Info/ChargeMode",
            "/Info/MaxChargeCurrent",
            "/Info/MaxChargeVoltage",
            "/Info/MaxDischargeCurrent",
        )
        values = {}
        for path in paths:
            values[path] = (
                self._dbusmonitor.get_value(service, path) if service else None
            )
        return values

    def _mppt_power(self):
        total = 0.0
        for service in self._dbusmonitor.get_service_list("com.victronenergy.solarcharger"):
            voltage = self._dbusmonitor.get_value(service, "/Dc/0/Voltage")
            current = self._dbusmonitor.get_value(service, "/Dc/0/Current")
            if voltage is not None and current is not None:
                total += voltage * current
        return total

    def _dc_load_power(self):
        total = 0.0
        for service in self._dbusmonitor.get_service_list("com.victronenergy.dcsystem"):
            total += as_number(self._dbusmonitor.get_value(service, "/Dc/0/Power"))
        return total

    def _pv_inverters(self):
        inverters = []
        for service in self._dbusmonitor.get_service_list("com.victronenergy.pvinverter"):
            phase_powers = {
                phase: self._dbusmonitor.get_value(service, "/Ac/%s/Power" % phase)
                for phase in phases
            }
            resolved = phase_power_or_total(
                phase_powers,
                self._dbusmonitor.get_value(service, "/Ac/Power"),
                phases,
            )
            inverter = {"position": self._dbusmonitor.get_value(service, "/Position", 0)}
            inverter.update(resolved)
            inverters.append(inverter)
        return inverters

    def _empty_energy_sample(self):
        return {
            "dc": {"charging": 0, "discharging": 0},
            "ac": {
                "ac_in1_to_ac_out": 0,
                "ac_in1_to_inverter": 0,
                "out_to_inverter": 0,
                "inverter_to_ac_out": 0,
                "ac_out_to_ac_in1": 0,
            },
        }

    def _normalize_energy(self, payload):
        sample = self._empty_energy_sample()
        payload = payload or {}
        dc = payload.get("dc") or {}
        ac = payload.get("ac") or {}
        sample["dc"]["charging"] = as_number(dc.get("charging"))
        sample["dc"]["discharging"] = as_number(dc.get("discharging"))
        sample["ac"]["ac_in1_to_ac_out"] = as_number(
            ac.get("ac_in1_to_ac_out", ac.get("from_grid"))
        )
        sample["ac"]["ac_in1_to_inverter"] = as_number(ac.get("ac_in1_to_inverter"))
        sample["ac"]["out_to_inverter"] = as_number(ac.get("out_to_inverter"))
        sample["ac"]["inverter_to_ac_out"] = as_number(ac.get("inverter_to_ac_out"))
        sample["ac"]["ac_out_to_ac_in1"] = as_number(
            ac.get("ac_out_to_ac_in1", ac.get("feed_in"))
        )
        return sample

    def _add_energy_sample(self, flows):
        sample = self._empty_energy_sample()
        existing = data_watt_hours if "dc" in data_watt_hours else self._empty_energy_sample()
        sample["dc"]["charging"] = existing["dc"].get("charging", 0) + flows["charging"]
        sample["dc"]["discharging"] = existing["dc"].get("discharging", 0) + flows["discharging"]
        for key in sample["ac"]:
            sample["ac"][key] = existing["ac"].get(key, 0) + flows["ac"].get(key, 0)
        return sample

    def _accumulate_energy(self, dc_power, ac_in_total, ac_out_total):
        global data_watt_hours, json_data, timestamp_storage_file

        timestamp = int(time())
        flows = energy_flows(ac_in_total, ac_out_total, dc_power)
        sample_add = {
            "charging": max(0.0, dc_power),
            "discharging": max(0.0, -dc_power),
            "ac": flows,
        }

        if data_watt_hours["time_creation"] + data_watt_hours_timespan > timestamp:
            added = self._add_energy_sample(sample_add)
            data_watt_hours["dc"] = added["dc"]
            data_watt_hours["ac"] = added["ac"]
            data_watt_hours["count"] = data_watt_hours.get("count", 0) + 1
            return

        if os.path.isfile(data_watt_hours_working_file):
            data_watt_hours_old = self._normalize_energy(
                _load_energy_json(data_watt_hours_working_file)
            )
        elif os.path.isfile(data_watt_hours_storage_file):
            data_watt_hours_old = self._normalize_energy(
                _load_energy_json(data_watt_hours_storage_file)
            )
        else:
            data_watt_hours_old = self._empty_energy_sample()

        factor = (timestamp - data_watt_hours["time_creation"]) / 3600
        count = data_watt_hours.get("count") or 1
        acc = self._normalize_energy(data_watt_hours)

        json_data = {"dc": {}, "ac": {}}
        for key in ("charging", "discharging"):
            json_data["dc"][key] = round(
                data_watt_hours_old["dc"][key]
                + (acc["dc"][key] / count * factor) / 1000,
                3,
            )
        for key in acc["ac"]:
            json_data["ac"][key] = round(
                data_watt_hours_old["ac"][key]
                + (acc["ac"][key] / count * factor) / 1000,
                3,
            )

        try:
            _atomic_write_json(data_watt_hours_working_file, json_data)
            if timestamp_storage_file + data_watt_hours_save < timestamp:
                _atomic_write_json(data_watt_hours_storage_file, json_data)
                timestamp_storage_file = timestamp
                logging.info("Written JSON for energy counters to persistent storage.")
        except OSError as error:
            logging.warning("Could not persist energy counters: %s", error)
            data_watt_hours["time_creation"] = timestamp
            data_watt_hours["count"] = 0
            return

        data_watt_hours = {
            "time_creation": timestamp,
            "dc": {
                "charging": round(sample_add["charging"], 3),
                "discharging": round(sample_add["discharging"], 3),
            },
            "ac": {key: round(value, 3) for key, value in flows.items()},
            "count": 1,
        }

    def _phase_vi(self, power, voltage):
        if power is None and voltage is None:
            return {"current": None, "power": None, "voltage": None}
        voltage = as_number(voltage)
        power = as_number(power)
        current = round(power / voltage, 2) if voltage > 0 else 0
        return {"current": current, "power": power, "voltage": voltage}

    def _battery_voltage(self, battery):
        voltage = battery.get("/Dc/0/Voltage")
        if voltage is not None:
            return voltage
        power = battery.get("/Dc/0/Power")
        current = battery.get("/Dc/0/Current")
        if power is None or current in (None, 0):
            return None
        try:
            return round(power / current, 2)
        except (TypeError, ZeroDivisionError):
            return None

    def _update(self):
        try:
            grid_power, grid_voltage = self._read_grid()
            battery = self._read_battery()
            pv_on_input, _pv_on_output = pv_power_on_input_and_output(
                self._pv_inverters(), phases
            )
            dc_power = multi_dc_power(
                battery.get("/Dc/0/Power"),
                self._mppt_power(),
                self._dc_load_power(),
            )
            ac_in_power, ac_out_power = calculate_multi_ac_power(
                grid_power, pv_on_input, dc_power, phases
            )
            self._accumulate_energy(
                dc_power, sum(ac_in_power.values()), sum(ac_out_power.values())
            )

            ac_in = {
                phase: self._phase_vi(ac_in_power[phase], grid_voltage[phase])
                for phase in phases
            }
            ac_out = {
                phase: self._phase_vi(ac_out_power[phase], grid_voltage[phase])
                for phase in phases
            }

            self._dbusservice["/Ac/NumberOfPhases"] = len(phases)
            for phase in phases:
                self._dbusservice["/Ac/ActiveIn/%s/F" % phase] = grid_frequency
                self._dbusservice["/Ac/ActiveIn/%s/I" % phase] = ac_in[phase]["current"]
                self._dbusservice["/Ac/ActiveIn/%s/P" % phase] = ac_in[phase]["power"]
                self._dbusservice["/Ac/ActiveIn/%s/S" % phase] = ac_in[phase]["power"]
                self._dbusservice["/Ac/ActiveIn/%s/V" % phase] = ac_in[phase]["voltage"]
                self._dbusservice["/Ac/Out/%s/F" % phase] = grid_frequency
                self._dbusservice["/Ac/Out/%s/I" % phase] = ac_out[phase]["current"]
                self._dbusservice["/Ac/Out/%s/P" % phase] = ac_out[phase]["power"]
                self._dbusservice["/Ac/Out/%s/S" % phase] = ac_out[phase]["power"]
                self._dbusservice["/Ac/Out/%s/V" % phase] = ac_out[phase]["voltage"]

            self._dbusservice["/Ac/ActiveIn/P"] = sum(ac_in_power.values())
            self._dbusservice["/Ac/ActiveIn/S"] = sum(ac_in_power.values())
            self._dbusservice["/Ac/Out/P"] = sum(ac_out_power.values())
            self._dbusservice["/Ac/Out/S"] = sum(ac_out_power.values())

            self._dbusservice["/BatteryOperationalLimits/MaxChargeCurrent"] = battery[
                "/Info/MaxChargeCurrent"
            ]
            self._dbusservice["/BatteryOperationalLimits/MaxChargeVoltage"] = battery[
                "/Info/MaxChargeVoltage"
            ]
            self._dbusservice["/BatteryOperationalLimits/MaxDischargeCurrent"] = battery[
                "/Info/MaxDischargeCurrent"
            ]

            self._dbusservice["/Dc/0/Current"] = battery["/Dc/0/Current"]
            self._dbusservice["/Dc/0/MaxChargeCurrent"] = battery["/Info/MaxChargeCurrent"]
            self._dbusservice["/Dc/0/Power"] = battery["/Dc/0/Power"]
            self._dbusservice["/Dc/0/Temperature"] = battery["/Dc/0/Temperature"]
            self._dbusservice["/Dc/0/Voltage"] = self._battery_voltage(battery)

            energy = self._normalize_energy(json_data)
            self._dbusservice["/Energy/AcIn1ToAcOut"] = energy["ac"]["ac_in1_to_ac_out"]
            self._dbusservice["/Energy/AcIn1ToInverter"] = energy["ac"]["ac_in1_to_inverter"]
            self._dbusservice["/Energy/AcOutToAcIn1"] = energy["ac"]["ac_out_to_ac_in1"]
            self._dbusservice["/Energy/InverterToAcOut"] = energy["ac"]["inverter_to_ac_out"]
            self._dbusservice["/Energy/OutToInverter"] = energy["ac"]["out_to_inverter"]

            charge_mode = battery.get("/Info/ChargeMode")
            if not isinstance(charge_mode, str):
                charge_mode = ""
            self._dbusservice["/Leds/Absorption"] = int(charge_mode.startswith("Absorption"))
            self._dbusservice["/Leds/Bulk"] = int(charge_mode.startswith("Bulk"))
            self._dbusservice["/Leds/Float"] = int(charge_mode.startswith("Float"))
            self._dbusservice["/Soc"] = battery["/Soc"]

            index = self._dbusservice["/UpdateIndex"] + 1
            if index > 255:
                index = 0
            self._dbusservice["/UpdateIndex"] = index
            return True
        except Exception:
            logging.exception("Error in _update method")
            return True


    def _handlechangedvalue(self, path, value):
        logging.debug("someone else updated %s to %s" % (path, value))
        return True  # accept the change


def main():
    from dbus.mainloop.glib import DBusGMainLoop

    # Have a mainloop, so we can send/receive asynchronous calls to and from dbus
    DBusGMainLoop(set_as_default=True)

    # formatting
    def _kwh(p, v):
        if v is None:
            return ""
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
        "/Ac/NumberOfPhases": {"initial": len(phases), "textformat": _n},
        # ----
        "/Ac/Out/L1/F": {"initial": None, "textformat": _hz},
        "/Ac/Out/L1/I": {"initial": None, "textformat": _a},
        "/Ac/Out/L1/NominalInverterPower": {"initial": 4500, "textformat": _w},
        "/Ac/Out/L1/P": {"initial": None, "textformat": _w},
        "/Ac/Out/L1/S": {"initial": None, "textformat": _va},
        "/Ac/Out/L1/V": {"initial": None, "textformat": _v},
        # ----
        "/Ac/Out/L2/F": {"initial": None, "textformat": _hz},
        "/Ac/Out/L2/I": {"initial": None, "textformat": _a},
        "/Ac/Out/L2/NominalInverterPower": {"initial": 4500, "textformat": _w},
        "/Ac/Out/L2/P": {"initial": None, "textformat": _w},
        "/Ac/Out/L2/S": {"initial": None, "textformat": _va},
        "/Ac/Out/L2/V": {"initial": None, "textformat": _v},
        # ----
        "/Ac/Out/L3/F": {"initial": None, "textformat": _hz},
        "/Ac/Out/L3/I": {"initial": None, "textformat": _a},
        "/Ac/Out/L3/NominalInverterPower": {"initial": 4500, "textformat": _w},
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
        "/Energy/AcIn1ToAcOut": {"initial": 0, "textformat": _kwh},
        "/Energy/AcIn1ToInverter": {"initial": 0, "textformat": _kwh},
        "/Energy/AcIn2ToAcOut": {"initial": 0, "textformat": _kwh},
        "/Energy/AcIn2ToInverter": {"initial": 0, "textformat": _kwh},
        "/Energy/AcOutToAcIn1": {"initial": 0, "textformat": _kwh},
        "/Energy/AcOutToAcIn2": {"initial": 0, "textformat": _kwh},
        "/Energy/InverterToAcIn1": {"initial": 0, "textformat": _kwh},
        "/Energy/InverterToAcIn2": {"initial": 0, "textformat": _kwh},
        "/Energy/InverterToAcOut": {"initial": 0, "textformat": _kwh},
        "/Energy/OutToInverter": {"initial": 0, "textformat": _kwh},
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
        "/State": {"initial": 8, "textformat": _n},
        "/SystemReset": {"initial": None, "textformat": _n},
        "/VebusChargeState": {"initial": 1, "textformat": _n},
        "/VebusError": {"initial": 0, "textformat": _n},
        "/VebusMainState": {"initial": 9, "textformat": _n},
        # ----
        "/UpdateIndex": {"initial": 0, "textformat": _n},
    }

    DbusMultiPlusEmulator(
        servicename="com.victronenergy.vebus.ttyS3",
        deviceinstance=275,
        paths=paths_dbus,
    )

    logging.info(
        "Connected to dbus and switching over to GLib.MainLoop() (= event based)"
    )
    mainloop = GLib.MainLoop()
    mainloop.run()


if __name__ == "__main__":
    main()
