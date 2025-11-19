import threading
import multiprocessing as MP
import os
import re
import time
from datetime import datetime
from datetime import timedelta
from datetime import date
import logging
from queue import Queue
import board
import digitalio
import RPi.GPIO as GPIO

###########################################################
# DIAG_LEVEL:
# - 0x0: normal info logging
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

SENSOR_BME               = 0x1
SENSOR_DHT               = 0x2
SENSOR_SND               = 0x4
SENSOR_RCV               = 0x8

WTHR_SND                 = 0x10
WTHR_RCV                 = 0x20
WTHR_CUR                 = 0x40
WTHR_24HR                = 0x80
WTHR_TIME_DETAIL         = 0x100

WTHR30_SND               = 0x200
WTHR30_RCV               = 0x400
WTHR30_ALL_TIME          = 0x800
WTHR30_30DAY             = 0x1000
WTHR30_TIME_DETAIL       = 0x2000

WAVG_RCV                 = 0x4000
WAVG_SUNTIMES            = 0x8000
WAVG_MIN_MAX             = 0x10000
WAVG_DAY_NIGHT           = 0x20000
WAVG_END_DAY             = 0x40000
WAVG_END_MONTH           = 0x80000

SEND_TO_DB               = 0x100000

DB_SENSOR_DATA           = 0x200000
DB_SEND_TO_WTHR          = 0x400000
WTHR_DAY_INIT            = 0x800000
DB_MSG_DETAIL            = 0x1000000

WTHR_DETAIL              = 0x2000000
DB_REPLACE               = 0x4000000
WTHR30_DETAIL            = 0x8000000
WTHR30_MO_INIT           = 0x10000000
WTHR30_MO_YEAR           = 0x20000000
SEND_TO_WAVG             = 0x40000000
TPH_CUR_MO_AVG           = 0x80000000

WIND_DIR                = 0x100000000
WIND_DIR_DETAIL         = 0x200000000
WIND_DIR_MSG            = 0x400000000
WIND_AVG                = 0x800000000
WIND_AVG_DETAIL         = 0x1000000000
WIND_AVG_MSG            = 0x2000000000
GUSTS                   = 0x4000000000
GUSTS_DETAIL            = 0x8000000000
GUSTS_MSG               = 0x10000000000
RAIN                    = 0x20000000000
RAIN_CNT                = 0x40000000000
RAIN_DETAIL             = 0x80000000000
RAIN_MSG                = 0x100000000000
COOR                    = 0x200000000000
COOR_DETAIL             = 0x400000000000
COOR_MSG                = 0x800000000000
DB                      = 0x1000000000000
DB_DETAIL               = 0x2000000000000
DB_MSG                  = 0x4000000000000
WIND_MAX                = 0x8000000000000
WIND_CNT                = 0x10000000000000
WIND_AVG5_DETAIL        = 0x20000000000000
DB_KEEP_ALIVE_UPDATE    = 0x40000000000000
WTHR_SIMULATE_NEW_DAY   = 0x80000000000000

DIAG_LEVEL = 0x0
#DIAG_LEVEL = DB_REPLACE
#DIAG_LEVEL = WTHR_SIMULATE_NEW_DAY
#DIAG_LEVEL = GUSTS_DETAIL

PRIOR_TEMP_DFLT = -50.0
#NO_CHANGE = -50.0

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

def cvt_datetime_to_str(tm_val):
    tm_str = tm_val.strftime("%Y-%m-%d %H:%M:%S")
    return tm_str

def month_to_id(str_month):
    switcher={
        'January'  : 1,
        'February' : 2,
        'March'    : 3,
        'April'    : 4,
        'May'      : 5,
        'June'     : 6,
        'July'     : 7,
        'August'   : 8,
        'September': 9,
        'October'  : 10,
        'November' : 11,
        'December' : 12,
    }
    return switcher.get(str_month, "ID INVALID")

def id_to_month(id):
    switcher={
        1: 'January',
        2: 'February',
        3: 'March',
        4: 'April',
        5: 'May',
        6: 'June',
        7: 'July',
        8: 'August',
        9: 'September',
       10: 'October',
       11: 'November',
       12: 'December',
    }
    return switcher.get(id, "ID INVALID")

def get_current_month():
    dt = datetime.now()
    mo_id = dt.month
    mo_str = id_to_month(mo_id)
    return mo_id, mo_str

######################################
# Executables
######################################

logging.basicConfig(level=logging.INFO,
                    format='(%(threadName)-10s) %(message)s',
                    )
