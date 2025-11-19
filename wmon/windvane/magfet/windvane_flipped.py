import gb

import board
import busio

MAX_VOLTAGE = 5.336
MIN_VOLTAGE = 0.005

MAX_COUNT = 28456
MIN_COUNT = 28

MNT_VIEW_DECLINATION = -11.31

# ADS1115 channel
chan = 2

def check_max_v(volts):

    global MAX_VOLTAGE

    new_max = False
    if volts > MAX_VOLTAGE and volts < 6.0:
        MAX_VOLTAGE = volts
        new_max = True

    return new_max

def check_min_v(volts):

    global MIN_VOLTAGE

    new_min = False
    if volts < MIN_VOLTAGE and volts > 0.0:
        MIN_VOLTAGE = volts
        new_min = True

    return new_min

def check_max_c(count):

    global MAX_COUNT

    new_max = False
    if count > MAX_COUNT and count < 35000:
        MAX_COUNT = count
        new_max = True

    return new_max

def check_min_c(count):

    global MIN_COUNT

    new_min = False
    if count < MIN_COUNT and count >= 0:
        MIN_COUNT = count
        new_min = True

    return new_min

def calc_step_v(min_volts, max_volts):


    # degrees/volt == 360.0 / voltage range

     range = max_volts - min_volts
     deg_step = range / 360.0

     if gb.DIAG_LEVEL & gb.WV_RANGE:
         gb.logging.info(
              "degrees/volt: %.3f MIN: %.3f v, MAX %.3f v, range: %.3f v" %
              (deg_step, min_volts, max_volts, range))

     return deg_step

def calc_step_c(min_count, max_count):

    # degrees/count == 360.0 / counter range

     range = max_count - min_count
     deg_step = float(range) / 360.0

     if gb.DIAG_LEVEL & gb.WV_RANGE:
         gb.logging.info("degrees/count: %.3f MIN: %d, MAX %d, range %d" %
                      (deg_step, min_count, max_count, range))

     return deg_step

def calc_dir_v(volts, min_v, max_v):
    # degrees/volt == 360.0 / voltage range
    # degrees = volts * degrees/volt
    dir = (volts * 360.0) / (max_v - min_v)
    return dir

def calc_dir_c(count, min_c, max_c):
    # degrees/count == 360.0 / counter range
    # degrees = count * degrees/count
    dir = (float(count) * 360.0) / (float(max_c) - float(min_c))
    return dir

def get_direction(degrees):

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

# ADS1115
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# I2C bus and address
#port = 1  # For Raspberry Pi 2/3/4, use 1. For older models, use 0.
# 0x48  # Addr line to GND (or not connected), DEFAULT
# 0x49  # Addr line to VCC
# 0x4A  # Addr line to SDA
# 0x4B  # Addr line to SCL


# ADS115 is 16-bit ADC
i2c = busio.I2C(board.SCL, board.SDA)

# Create the ADS object
address = 0x49
ads = ADS.ADS1115(i2c, address=0x49)

# ADS gain
# Gain can change based on the voltage signal - Gain of 1
# is typically enough for a many sensors, but range
# is limited to 0-4.xv
#  - Gain of 1 results in max voltage of 4.0x and about
#    1/4 of the hall effect sensor rotation pegs at 4.096v 
#  - Need to use 2/3 gain to get full 0-5v (0-6.xv) range
#    and a varying voltage through all 360 degrees
#ads.gain = 1
ads.gain = 2.0/3.0

chan0 = AnalogIn(ads, ADS.P0)  # Unused
chan1 = AnalogIn(ads, ADS.P1)  # Hall Effect Sensor
chan2 = AnalogIn(ads, ADS.P2)  # Unused
chan3 = AnalogIn(ads, ADS.P3)  # Unused

if gb.DIAG_LEVEL & gb.WV_DETAIL:
    gb.logging.info("ADS1115 (i2c) initialized")

#SLEEP_TIME = 0.5
SLEEP_TIME = 2.0

exit = False

degree_step = calc_step_v(MIN_VOLTAGE, MAX_VOLTAGE)
count_step = calc_step_c(MIN_COUNT, MAX_COUNT)

while not exit:
    try:

        # Get data from ADS1115 (ADC)
        raw_value0 = chan0.value
        voltage0 = chan0.voltage
        raw_value1 = chan1.value
        voltage1 = chan1.voltage
        raw_value2 = chan2.value
        voltage2 = chan2.voltage
        raw_value3 = chan3.value
        voltage3 = chan3.voltage

        raw = raw_value0
        volts = voltage0

        if chan == 1:
            raw = raw_value2
            volts = voltage2
        elif chan == 2:
            raw = raw_value2
            volts = voltage2
        elif chan == 3:
            raw = raw_value3
            volts = voltage3

        if gb.DIAG_LEVEL & gb.WV_ALL_CHAN:
            gb.logging.info("ADS chan0 %d volts: %.5f v" %
                         (raw_value0, voltage0))
            gb.logging.info("ADS chan1 %d volts: %.5f v" %
                         (raw_value1, voltage1))
            gb.logging.info("ADS chan2 %d volts: %.5f v" %
                         (raw_value2, voltage2))
            gb.logging.info("ADS chan3 %d volts: %.5f v" %
                         (raw_value3, voltage3))
        if gb.DIAG_LEVEL & gb.WV_DETAIL:
            gb.logging.info("ADS chan2 %d volts: %.5f v" %
                         (raw, volts))

        if check_min_v(volts) or check_max_v(volts):
            degree_step = calc_step_v(MIN_VOLTAGE, MAX_VOLTAGE)
        if check_min_c(raw) or check_max_c(raw):
            count_step = calc_step_c(MIN_COUNT, MAX_COUNT)

        direction_v = calc_dir_v(volts, MIN_VOLTAGE, MAX_VOLTAGE)
        direction_v = round(direction_v + 0.05, 1)

        direction_c = calc_dir_c(raw, MIN_COUNT, MAX_COUNT)
        direction_c = round(direction_c + 0.05, 1)

        if gb.DIAG_LEVEL & gb.WV_DETAIL:
            gb.logging.info("direction_v: %.1f, direction_c %.1f" %
                         (direction_v, direction_c))

        # Handle magnetic North declination
        true_v = direction_v + MNT_VIEW_DECLINATION
        if true_v < 0.0:
            # When direction is slightly West of North (up to 11.24
            # degrees West of North), the true North reading is
            # negative.  While the value is correct, it is better
            # to keep this value within the positive 0-360 range
            true_v = 360.0 + true_v
        # Handle magnetic North declination
        true_c = direction_c + MNT_VIEW_DECLINATION
        if true_c < 0.0:
            # When direction is slightly West of North (up to 11.24
            # degrees West of North), the true North reading is
            # negative.  While the value is correct, it is better
            # to keep this value within the positive 0-360 range
            true_c = 360.0 + true_c


        dir_v_mag = get_direction(direction_v)
        dir_c_mag = get_direction(direction_c)

        dir_v_true = get_direction(true_v)
        dir_c_true = get_direction(true_c)

        gb.logging.info("TRUE: %s(%.1f), Magnetic: %s(%.1f)" %
                     (dir_v_true, true_v, dir_v_mag, direction_v)) 

    except KeyboardInterrupt:
        gb.logging.info("Script terminated by user.")
        exit = True
    except Exception as e:
        gb.logging.error(f"An error occurred: %s" % (e))

    gb.time.sleep(SLEEP_TIME)
