import os
import re
import time
from datetime import datetime
from datetime import timedelta
import logging
import RPi.GPIO as GPIO

###########################################################
# DIAG_LEVEL:
# -  0x0: normal info/debug logging
# -  0x1: Show wind direction readings
# -  0x2: Show wind direction details readings
# -  0x4: Show wind speed average
# -  0x8: Show wind speed average details
# - 0x10: Show wind speed gusts
# - 0x20: Database logging
###########################################################
SHOW_WIND_DIR           =  0x1
SHOW_WIND_DIR_DETAIL    =  0x2
SHOW_WIND_AVG           =  0x4
SHOW_WIND_AVG_DETAIL    =  0x8
SHOW_GUSTS              = 0x10
DB                      = 0x20
DB_DETAIL               = 0x40

DIAG_LEVEL=SHOW_WIND_AVG|SHOW_GUSTS

######################################
# GPIO Pins
######################################
#RAIN_GAUGE_GPIO = 10
#ANEMOMETER_GPIO = 9

######################################
# COMMON Msg Types
######################################
EXIT = "EXIT"

######################################
# GLOBAL GENERIC FUNCTIONS
######################################

# Get date/time for local timezone
def get_localdate_str():
    tm_str = str(datetime.now())
    return tm_str

def get_time_with_minutes(date_str):
    tm_str = re.sub('^....-..-.. ', "", date_str)
    tm_str = re.sub(':..\.......$', "", tm_str)
    return tm_str

def get_date_with_seconds(date_str):
    tm_str = re.sub('\.......$', "", date_str)
    return tm_str

######################################
# Executables
######################################

logging.basicConfig(level=logging.INFO,
                    format='(%(threadName)-10s) %(message)s',
                    )

