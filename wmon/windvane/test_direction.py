import gb
import time
import sys
import re
import logging
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from datetime import datetime

logging_time_next = gb.DFLT_TIME

EAST_START       =     1
EAST_END         =  4000
SOUTH_EAST_START =  4500
SOUTH_EAST_END   =  7800
SOUTH_START      =  9100
SOUTH_END        = 12600
NORTH_EAST_START = 15900
NORTH_EAST_END   = 20000
SOUTH_WEST_START = 24700
SOUTH_WEST_END   = 27000
NORTH_START      = 27001
NORTH_END        = 32650
WEST_START       = 32651
WEST_END         = 32768  # 2^15 = 32768
NORTH_WEST_START = 32651
NORTH_WEST_END   = 32768  # 2^15 = 32768

EAST = "East"
SOUTH_EAST = "South-East"
SOUTH = "South"
NORTH_EAST = "North-East"
SOUTH_WEST = "South-West"
NORTH = "North"
WEST = "West"
NORTH_WEST = "North-West"

# Get date/time for local timezone
def get_localdate_str():
    tm_str = str(datetime.now())
    return tm_str

def get_date_with_seconds(date_str):
    tm_str = re.sub('\.......$', "", date_str)
    return tm_str

logging.basicConfig(level=logging.INFO,
                    format='(%(threadName)-10s) %(message)s',
                    )

# ADS115 is 16-bit ADC

i2c = busio.I2C(board.SCL, board.SDA)

# Create the ADS object and specify the gain
ads = ADS.ADS1115(i2c)
# Can change based on the voltage signal - Gain of 1 is typically
# enough for a log of sensors
ads.gain = 1
#ads.gain = 2.0/3.0
#chan = AnalogIn(ads, ADS.P0)
chan0 = AnalogIn(ads, ADS.P0)
chan1 = AnalogIn(ads, ADS.P1)
chan2 = AnalogIn(ads, ADS.P2)
chan3 = AnalogIn(ads, ADS.P3)

prior_wv_dir = ""

# Continuously print the values
idx = 0
while True:
    #if ((idx % 12) == 0):
    if ((idx % 3) == 0):
        # Print once a minute (5 second sleep * 12 = 60 seconds
        tm_str = get_date_with_seconds(get_localdate_str())
        logging.info(" %s" % (tm_str))
        logging.info("READINGS from WIND VANE")
        logging.info("    Analog Voltages    Digital Values")
        logging.info("    A0                 A0")
    idx = idx + 1
    #logging.info("%.5f V %.5f V %.5f V %.5f V" %
    #    (chan0.voltage,chan1.voltage, chan2.voltage, chan3.voltage))
    #logging.info("%5d %5d %5d %5d" %
    #    (chan0.value,chan1.value, chan2.value, chan3.value))
    #logging.info("%.5f   %.5f   %.5f   %.5f   %5d %5d %5d %5d" %
    #    (chan0.voltage,chan1.voltage, chan2.voltage, chan3.voltage,
    #    chan0.value,chan1.value, chan2.value, chan3.value))
    
    wv_dir = ""
    wv_volts = chan0.voltage
    wv_value = chan0.value

    if ((wv_value >= EAST_START) and (wv_value < EAST_END)):
        wv_dir = EAST
    elif ((wv_value >= SOUTH_EAST_START) and (wv_value <= SOUTH_EAST_END)):
        wv_dir = SOUTH_EAST
    elif ((wv_value >= SOUTH_START) and (wv_value <= SOUTH_END)):
        wv_dir = SOUTH
    elif ((wv_value >= NORTH_EAST_START) and (wv_value <= NORTH_EAST_END)):
        wv_dir = NORTH_EAST
    elif ((wv_value >= SOUTH_WEST_START) and (wv_value <= SOUTH_WEST_END)):
        wv_dir = SOUTH_WEST
    elif ((wv_value >= NORTH_START) and (wv_value <= NORTH_END)):
        wv_dir = NORTH
    elif ((wv_value >= WEST_START) and (wv_value <= WEST_END)):
        if (prior_wv_dir == NORTH):
            wv_dir = NORTH_WEST
        else:
            wv_dir = WEST
        logging.info("prior_wv_dir: %s" % (prior_wv_dir))
    else:
        wv_dir = "Invalid"
        logging_now = gb.datetime.now()
        if logging_now > logging_time_next:
            logging_time_next =  logging_now + gb.timedelta(seconds=60)
            gb.logging.error("ERROR: Wind direction: %s, %d, %0.5f" %
                             (wv_dir, wv_value, wv_volts))

    prior_wv_dir = wv_dir
    logging.info("    %.5f            %5d  %s" % (wv_volts, wv_value, wv_dir))
  
    print(f"ADS1115 A0 Voltage: {chan0.voltage}V")
    print(f"ADS1115 A0 Value:   {chan0.value}")
    print(f"ADS1115 A1 Voltage: {chan1.voltage}V")
    print(f"ADS1115 A1 Value:   {chan1.value}")
    #print(f"ADS1115 A2 Voltage: {chan2.voltage}V")
    #print(f"ADS1115 A3 Voltage: {chan3.voltage}V")
    #logging.info("ADS1115 A0 Voltage=%3f V TDS" % (chan0.voltage))
    #logging.info("ADS1115 A1 Voltage=%3f V pH" % (chan1.voltage))
    #logging.info("ADS1115 A2 Voltage=%3f V Temperature" % (chan2.voltage))
    #logging.info("ADS1115 A3 Voltage=%3f V Unused" % (chan3.voltage))
    #print("-------------")
    time.sleep(5)
