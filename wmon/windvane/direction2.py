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

logging.basicConfig(level=logging.INFO,
                    format='(%(threadName)-10s) %(message)s',
                    )

logging_time_next = gb.DFLT_TIME

# Directions and ranges for resistor-based windvane
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

MAX_VOLTAGE = 5.336
MIN_VOLTAGE = 0.005

MAX_COUNT = 28456
MIN_COUNT = 28

MNT_VIEW_DECLINATION = -11.31

# Get date/time for local timezone
def get_localdate_str():
    tm_str = str(datetime.now())
    return tm_str

def get_date_with_seconds(date_str):
    tm_str = re.sub('\.......$', "", date_str)
    return tm_str

def usage():
    print("Usage:")
    print("  pyhon3 directions.py <1|2>")
    print("    1 = use ads.gain 1.0")
    print("    2 = use ads.gain 2.0/3.0")

def get_resistor_dir(count, prior_wv_dir_str):

    global logging_time_next

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
        if (prior_wv_dir_str == NORTH):
            wv_dir = NORTH_WEST
        else:
            wv_dir = WEST
        logging.info("prior_wv_dir_str: %s" % (prior_wv_dir_str))
    else:
        wv_dir = "Invalid"
        logging_now = gb.datetime.now()
        if logging_now > logging_time_next:
            logging_time_next =  logging_now + gb.timedelta(seconds=60)
            gb.logging.error("ERROR: Wind direction: %s, %d, %0.5f" %
                             (wv_dir, wv_value, wv_volts))

    return wv_dir

#---------------------------------------------------------
# Confirm voltage is within expected range
#---------------------------------------------------------
def check_max_v(volts):

    global MAX_VOLTAGE

    new_max = False
    if volts > MAX_VOLTAGE and volts < 6.0:
        MAX_VOLTAGE = volts
        new_max = True

    return new_max

#---------------------------------------------------------
# Confirm voltage is within expected range
#---------------------------------------------------------
def check_min_v(volts):

    global MIN_VOLTAGE

    new_min = False
    if volts < MIN_VOLTAGE and volts > 0.0:
        MIN_VOLTAGE = volts
        new_min = True

    return new_min

#---------------------------------------------------------
# Confirm count is within expected range
#---------------------------------------------------------
def check_max_c(count):

    global MAX_COUNT

    new_max = False
    if count > MAX_COUNT and count < 35000:
        MAX_COUNT = count
        new_max = True

    return new_max

#---------------------------------------------------------
# Confirm count is within expected range
#---------------------------------------------------------
def check_min_c(count):

    global MIN_COUNT

    new_min = False
    if count < MIN_COUNT and count >= 0:
        MIN_COUNT = count
        new_min = True

    return new_min

#---------------------------------------------------------
# Calculate degrees / volt
#---------------------------------------------------------
def calc_step_v(min_volts, max_volts):

    # degrees/volt == 360.0 / voltage range

     range = max_volts - min_volts
     deg_step = range / 360.0

     #if gb.DIAG_LEVEL & gb.WV_RANGE:
     gb.logging.info(
              "degrees/volt: %.3f MIN: %.3f v, MAX %.3f v, range: %.3f v" %
              (deg_step, min_volts, max_volts, range))

     return deg_step

#---------------------------------------------------------
# Calculate degrees / count
#---------------------------------------------------------
def calc_step_c(min_count, max_count):

    # degrees/count == 360.0 / counter range

     range = max_count - min_count
     deg_step = float(range) / 360.0

     #if gb.DIAG_LEVEL & gb.WV_RANGE:
     gb.logging.info("degrees/count: %.3f MIN: %d, MAX %d, range %d" %
                      (deg_step, min_count, max_count, range))

     return deg_step

#---------------------------------------------------------
# Use inverse if shaft points downward
#---------------------------------------------------------
def adjust_shaft_down(dir):
    if dir > 180.0:
        dir = 180.0 - (dir - 180.0)
    elif dir < 180.0:
        dir = 180.0 + (180.0 - dir)
    return dir

#---------------------------------------------------------
# Voltage corresponds to inverse direction if shaft points downward
# i.e., 270 degrees is due East, 90 degrees is due West
# 180 degrees is still South and 0 degrees is North
#---------------------------------------------------------
def calc_dir_v(volts, min_v, max_v):
    # degrees/volt == 360.0 / voltage range
    # degrees = volts * degrees/volt
    dir = (volts * 360.0) / (max_v - min_v)
    dir_in_degrees = adjust_shaft_down(dir)
    return dir_in_degrees

#---------------------------------------------------------
# Count corresponds to inverse direction if shaft points downward
#---------------------------------------------------------
def calc_dir_c(count, min_c, max_c):
    # degrees/count == 360.0 / counter range
    # degrees = count * degrees/count
    dir = (float(count) * 360.0) / (float(max_c) - float(min_c))
    dir_in_degrees = adjust_shaft_down(dir)
    return dir_in_degrees

#---------------------------------------------------------
# Process magfet readings from ADS1115
#---------------------------------------------------------
def get_degrees(volts, raw):

    if check_min_v(volts) or check_max_v(volts):
        degree_step = calc_step_v(MIN_VOLTAGE, MAX_VOLTAGE)
    if check_min_c(raw) or check_max_c(raw):
        count_step = calc_step_c(MIN_COUNT, MAX_COUNT)

    direction_v = calc_dir_v(volts, MIN_VOLTAGE, MAX_VOLTAGE)
    direction_v = round(direction_v + 0.05, 1)

    direction_c = calc_dir_c(raw, MIN_COUNT, MAX_COUNT)
    direction_c = round(direction_c + 0.05, 1)

    return direction_v, direction_c

#---------------------------------------------------------
# Adjust declination for hall effect sensor reading
#---------------------------------------------------------
def adjust_declination(degrees):
    # Handle magnetic North declination
    true_dir = degrees + MNT_VIEW_DECLINATION
    if true_dir < 0.0:
        # When direction is slightly West of North (up to 11.24
        # degrees West of North), the true North reading is
        # negative.  While the value is correct, it is better
        # to keep this value within the positive 0-360 range
        true_dir = 360.0 + true_dir
    return true_dir

#---------------------------------------------------------
# Get direction from magfet degree reading
#---------------------------------------------------------
def get_magfet_direction(degrees):

    N_min = 348.75
    N_max = 11.25
    range = 22.5

    dir = "North"

    if degrees > N_min or degrees <= N_max:
        dir = "North"
    elif degrees <= (N_max + (1 * range)):
        dir = "NNE"
    elif degrees <= (N_max + (2 * range)):
        dir = "NE"
    elif degrees <= (N_max + (3 * range)):
        dir = "ENE"
    elif degrees <= (N_max + (4 * range)):
        dir = "East"
    elif degrees <= (N_max + (5 * range)):
        dir = "ESE"
    elif degrees <= (N_max + (6 * range)):
        dir = "SE"
    elif degrees <= (N_max + (7 * range)):
        dir = "SSE"
    elif degrees <= (N_max + (8 * range)):
        dir = "South"
    elif degrees <= (N_max + (9 * range)):
        dir = "SSW"
    elif degrees <= (N_max + (10 * range)):
        dir = "SW"
    elif degrees <= (N_max + (11 * range)):
        dir = "WSW"
    elif degrees <= (N_max + (12 * range)):
        dir = "West"
    elif degrees <= (N_max + (13 * range)):
        dir = "WNW"
    elif degrees <= (N_max + (14 * range)):
        dir = "NW"
    elif degrees <= (N_max + (15 * range)):
        dir = "NNW"

    return dir

#print("len(sys.argv):", len(sys.argv))
if len(sys.argv) != 2:
    print(f"ERROR: Invalid number of arguments: {len(sys.argv)}")
    print("  Command invocation string: ", sys.argv)
    usage()
    exit(1)
elif (sys.argv[1] != "1") and (sys.argv[1] != "2"):
    print(f"ERROR: Invalid gain argument: {sys.argv[1]}")
    usage()
    exit(1)

# ADS115 is 16-bit ADC

i2c = busio.I2C(board.SCL, board.SDA)

# Create the ADS object and specify the gain
ads = ADS.ADS1115(i2c)
# Can change based on the voltage signal - Gain of 1 is typically
# enough for a log of sensors
#ads.gain = 2.0/3.0
#ads.gain = 0.66667
ads.gain = 2
if sys.argv[1] == "1":
    ads.gain = 1

print("ads.gain: ", ads.gain)

SOFT_GAIN_ADJUST = 347.7

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
        logging.info("    Voltage            Digital")
        #logging.info("    A0                 A0")
    idx = idx + 1
    #logging.info("%.5f V %.5f V %.5f V %.5f V" %
    #    (chan0.voltage,chan1.voltage, chan2.voltage, chan3.voltage))
    #logging.info("%5d %5d %5d %5d" %
    #    (chan0.value,chan1.value, chan2.value, chan3.value))
    #logging.info("%.5f   %.5f   %.5f   %.5f   %5d %5d %5d %5d" %
    #    (chan0.voltage,chan1.voltage, chan2.voltage, chan3.voltage,
    #    chan0.value,chan1.value, chan2.value, chan3.value))
    
    # resistor weathervane readings from ADS1115
    wv_dir = ""
    wv_volts = chan0.voltage
    wv_value = chan0.value

    # Magfet (hall sensor) weathervane readings from ADS1115
    mag_volts = chan1.voltage
    mag_value = chan1.value

    # Get resistor based wind direction
    wv_dir = get_resistor_dir(wv_value, prior_wv_dir)
    prior_wv_dir = wv_dir
    logging.info("    %.5f            %5d  %s" % (wv_volts, wv_value, wv_dir))

    # Get hall sensor based wind direction
    degrees_v, degrees_c = get_degrees(mag_volts, mag_value)
    degree_gain = degrees_v * 360.0/SOFT_GAIN_ADJUST
    if degree_gain >= 360.0:
        degree_gain = degree_gain - 360.0
    true_magfet_degrees = adjust_declination(degree_gain)
    magfet_dir = get_magfet_direction(true_magfet_degrees)

    logging.info("    %.5f            %5d  %s, true %.1f, magnetic %.1f gain %.1f" %
                 (mag_volts, mag_value, magfet_dir, true_magfet_degrees, degrees_v, degree_gain))
  
    #print(f"ADS1115 A0 Voltage: {chan0.voltage}V A0 Value:   {chan0.value}")
    #print(f"ADS1115 A1 Voltage: {chan1.voltage}V A1 Value:   {chan1.value}")
    #print(f"ADS1115 A2 Voltage: {chan2.voltage}V")
    #print(f"ADS1115 A3 Voltage: {chan3.voltage}V")
    #logging.info("ADS1115 A0 Voltage=%3f V TDS" % (chan0.voltage))
    #logging.info("ADS1115 A1 Voltage=%3f V pH" % (chan1.voltage))
    #logging.info("ADS1115 A2 Voltage=%3f V Temperature" % (chan2.voltage))
    #logging.info("ADS1115 A3 Voltage=%3f V Unused" % (chan3.voltage))
    #print("-------------")
    time.sleep(2)
