#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
SERVICE_NAME=$(basename $SCRIPT_DIR)

sed -i "/$SERVICE_NAME/d" /data/rc.local
if command -v svc >/dev/null 2>&1; then
    svc -d /service/$SERVICE_NAME 2>/dev/null || true
fi
rm -f /service/$SERVICE_NAME

echo "Do you want to remove the dbus entries added by this driver? (y/N)"
read -r confirm
if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
    dbus -y com.victronenergy.settings /Settings RemoveSettings "%[ '/Alarm/System/GridLost', '/CanBms/SocketcanCan0/CustomName', '/CanBms/SocketcanCan0/ProductId', '/Canbus/can0/Profile', '/SystemSetup/AcInput1', '/SystemSetup/AcInput2' ]"
fi
