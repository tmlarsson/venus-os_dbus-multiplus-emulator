#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
SERVICE_NAME=$(basename $SCRIPT_DIR)

chmod 744 $SCRIPT_DIR/$SERVICE_NAME.py
chmod 744 $SCRIPT_DIR/install.sh
chmod 744 $SCRIPT_DIR/restart.sh
chmod 744 $SCRIPT_DIR/uninstall.sh
chmod 755 $SCRIPT_DIR/service/run
chmod 755 $SCRIPT_DIR/service/log/run

ln -sfn $SCRIPT_DIR/service /service/$SERVICE_NAME

filename=/data/rc.local
if [ ! -f $filename ]
then
    touch $filename
    chmod 755 $filename
    echo "#!/bin/bash" >> $filename
    echo >> $filename
fi

grep -qxF "bash $SCRIPT_DIR/install.sh" $filename || echo "bash $SCRIPT_DIR/install.sh" >> $filename

dbus -y com.victronenergy.settings /Settings AddSetting Alarm/System GridLost 1 i 0 2 > /dev/null
dbus -y com.victronenergy.settings /Settings AddSetting CanBms/SocketcanCan0 CustomName '' s 0 2 > /dev/null
dbus -y com.victronenergy.settings /Settings AddSetting CanBms/SocketcanCan0 ProductId 0 i 0 9999 > /dev/null
dbus -y com.victronenergy.settings /Settings AddSetting Canbus/can0 Profile 0 i 0 9999 > /dev/null
dbus -y com.victronenergy.settings /Settings AddSetting SystemSetup AcInput1 1 i 0 2 > /dev/null
dbus -y com.victronenergy.settings /Settings AddSetting SystemSetup AcInput2 0 i 0 2 > /dev/null
