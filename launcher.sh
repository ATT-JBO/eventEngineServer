#!/bin/sh
# launcher.sh
# navigate to home directory, then to this directory, then execute python script, then back home


LOGFILE=/home/pi/eventEngine/logs/restart.log

writelog() {
  now=`date`
  echo "$now $*" >> $LOGFILE
}


while true ; do
  #check for network connectivity
  wget -q --tries=10 --timeout=99 --spider http://google.com
  sleep 1
  if [ $? -eq 0 ]; then
        cd /home/pi/eventEngine
        # pause a little, if we don't then the zwave stack crashes cause it's started too fast. With the delay, everything is ok.
        sleep 1
        writelog "Starting"
        sudo python rules.py
        writelog "Exited with status $?"
  else
        writelog "No network connection, retrying..."
  fi
done
cd /



