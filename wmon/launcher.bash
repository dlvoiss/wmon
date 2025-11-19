#!/bin/bash
# launcher.bash
# navigate to Monitor, then execute weather and fan control python script

cd /home/pi/Mon2
date
echo "Starting Weather Monitor Script"
python3 main.py
echo "Stopped Weather & Fan Control Script"
date
cp /home/pi/logs/weatherlog /home/pi/logs/weatherlog\.`date +%w`
cd

