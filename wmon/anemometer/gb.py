import threading
import multiprocessing as MP
import os
import re
import time
from datetime import datetime
from datetime import timedelta
import logging
from queue import Queue
import board
import digitalio
import RPi.GPIO as GPIO

###########################################################
# DIAG_LEVEL:
# - 0x0: normal info/debug logging
# - 0x1: display local readings
# - 0x2: display remote readings
# - 0x4: display current reading information
# - 0x8: display weather message send information
# - 0x10: display DB operation invocations
# - 0x20: count database operations
# - 0x40: display SELECT/UPDATE details
# - 0x80: display SQL string data
# - 0x100: display fan and CPU temperature operations
# - 0x200: display BMP/DHT reconcilation details
# - 0x400: display monthly average statistics send information
# - 0x800: display monthly average statistics thread informtion
# - 0x1000: weather current month data
# - 0x2000: weather all-time month data
###########################################################
TPH_CUR_MO_AVG          =      0x1000

WIND_DIR                =      0x4000
WIND_DIR_DETAIL         =      0x8000
WIND_DIR_MSG            =     0x10000
WIND_AVG                =     0x20000
WIND_AVG_DETAIL         =     0x40000
WIND_AVG_MSG            =     0x80000
GUSTS                   =    0x100000
GUSTS_DETAIL            =    0x200000
GUSTS_MSG               =    0x400000
RAIN                    =    0x800000
RAIN_CNT                =   0x1000000
RAIN_DETAIL             =   0x2000000
RAIN_MSG                =   0x4000000
COOR                    =   0x8000000
COOR_DETAIL             =  0x10000000
COOR_MSG                =  0x20000000
DB                      =  0x40000000
DB_DETAIL               =  0x80000000
DB_MSG                  = 0x100000000
WIND_MAX                = 0x200000000
WIND_CNT                = 0x400000000
WIND_AVG5_DETAIL        = 0x800000000

#DIAG_LEVEL = WIND_DIR|WIND_DIR_DETAIL|WIND_DIR_MSG|WIND_AVG|WIND_AVG_DETAIL|WIND_AVG_MSG|RAIN_CNT
#DIAG_LEVEL = WIND_DIR|WIND_DIR_DETAIL|WIND_AVG|WIND_AVG_DETAIL
#DIAG_LEVEL = DB|DB_MSG
#DIAG_LEVEL = WIND_AVG
DIAG_LEVEL = WIND_DIR_DETAIL
#DIAG_LEVEL = 0x0

#DISABLE_RMT = False
DISABLE_RMT = True   # disable access to remote weather remote
                      # Used primarily during testing to avoid
                      # exceeding allowed number of calls to
                      # external weather site

PRIOR_TEMP_DFLT = -50.0
NO_CHANGE = -50.0

DFLT_TIME = datetime(1900, 1, 1, 11, 00, 00)

###########################################################
#
# GPIO PINs
#
###########################################################
ANEMOMETER_GPIO = 4
FAN_PIN = 17 # GPIO used to control fan on/off
#DHT_PIN = board.D25
RAIN_GAUGE_GPIO = 26

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

def cvt_epoch_date_str_to_local_str(date):
    date_str = datetime.fromtimestamp(int(date))
    return(date_str)

######################################
# Executables
######################################

logging.basicConfig(level=logging.INFO,
                    format='(%(threadName)-10s) %(message)s',
                    )
