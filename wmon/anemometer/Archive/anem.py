import gb

import signal


end_script = False

READINGS_10_MIN = 120

# 10 minutes worth of windspeed readings
WIND_READING = [0.0] * READINGS_10_MIN

######################################
# GPIO Pins
######################################
ANEMOMETER_GPIO = 4

##############################################
# Setup
##############################################
def setup():
    tm_str = gb.get_date_with_seconds(gb.get_localdate_str())
    gb.logging.info("DIAG_LEVEL 0x%x" % (gb.DIAG_LEVEL))
    gb.logging.info("Setting up: %s" % (tm_str))
    gb.GPIO.setmode(gb.GPIO.BCM)
    gb.GPIO.setup(ANEMOMETER_GPIO, gb.GPIO.IN, pull_up_down=gb.GPIO.PUD_UP)

##############################################
# Destroy
##############################################
def destroy():
    print("Cleaning up")
    gb.GPIO.cleanup()

def get_windspeed(cnt, interval):
    if (cnt == 0):
        speed = 0.0
    else:
        speed = (cnt * 1.492) / interval

    return speed

def get_avg(index, interval, max):

    global WIND_READING

    ws = 0.0

    # Able to use indexes in contiguous range
    if ((index >= interval) and (index < (max - interval))):
        start_index = (index - interval) + 1
        end_index = index + 1
        for ix in range(start_index, end_index):
            ws = ws + WIND_READING[ix]

    # non-contiguous range -- readings start at end of the
    # readings array and finish at the beginning of the array
    elif (index < interval):
        gb.logging.debug("Non-contiguous average")
        end_index = index + 1
        # Low part of range
        for ix in range(end_index):
            ws = ws + WIND_READING[ix]
        # High part of range
        start_index = max - end_index
        for ix in range(start_index, max):
            ws = ws + WIND_READING[ix]

    avg = ws / interval
    gb.logging.debug("get_avg: %0.3f" % (avg))

    return avg

#import math
#
#def calculate_standard_deviation(arr):
#    # Calculate the mean of the array
#    mean = sum(arr) / len(arr)
#    
#    # Calculate the variance
#    variance = sum((x - mean) ** 2 for x in arr) / len(arr)
#    
#    # Calculate the standard deviation
#    standard_deviation = math.sqrt(variance)
#    
#    return standard_deviation
#
## Example usage
#arr = [10, 12, 23, 23, 16, 23, 21, 16]
#std_dev = calculate_standard_deviation(arr)
#print(f"The standard deviation of the array is: {std_dev}")


#import math
#
#def calculate_standard_deviation_subset(arr, start, end):
#    # Extract the subset of the array
#    subset = arr[start:end+1]
#    
#    # Calculate the mean of the subset
#    mean = sum(subset) / len(subset)
#    
#    # Calculate the variance
#    variance = sum((x - mean) ** 2 for x in subset) / len(subset)
#    
#    # Calculate the standard deviation
#    standard_deviation = math.sqrt(variance)
#    
#    return standard_deviation
#
## Example usage
#arr = [10, 12, 23, 23, 16, 23, 21, 16]
#start_index = 2
#end_index = 5
#std_dev_subset = calculate_standard_deviation_subset(arr, start_index, end_index)
#print(f"The standard deviation of the subset of the array from index {start_index} to {end_index} is: {std_dev_subset}")


#import math
#
#def calculate_standard_deviation_wrapped_subset(arr, start, end):
#    # Extract the subset of the array with wrapping around
#    if start <= end:
#        subset = arr[start:end+1]
#    else:
#        subset = arr[start:] + arr[:end+1]
#    
#    # Calculate the mean of the subset
#    mean = sum(subset) / len(subset)
#    
#    # Calculate the variance
#    variance = sum((x - mean) ** 2 for x in subset) / len(subset)
#    
#    # Calculate the standard deviation
#    standard_deviation = math.sqrt(variance)
#    
#    return standard_deviation
#
## Example usage
#arr = [10, 12, 23, 23, 16, 23, 21, 16]
#start_index = 5
#end_index = 2
#std_dev_wrapped_subset = calculate_standard_deviation_wrapped_subset(arr, start_index, end_index)
#print(f"The standard deviation of the wrapped subset of the array from index {start_index} to {end_index} is: {std_dev_wrapped_subset}")

def receive_TERM(signalNumber, frame):
    gb.logging.info("Received SIGTERM(%d)" % (signalNumber))
    end_script = True

##############################################
# main function
##############################################
if __name__ == '__main__':

    #global READINGS_10_MIN
    #global WIND_READING

    my_pid = gb.os.getpid()
    gb.logging.info("PID: %d" % (my_pid))
    signal.signal(signal.SIGTERM,receive_TERM)

    setup()

    spun = True
    spin_count = 0
    spin_total = 0

    SLEEP_INTERVAL_STEP = 0
    INTERVAL_MAX = 100 # 5 seconds

    INTERVAL_5_SEC = 5  # 5 seconds
    READINGS_1_MIN = 12
    READINGS_5_MIN = 60

    ix = 0
    iz = 0 # index into WIND_READING array

    AVG_1_MIN = 0.0
    AVG_5_MIN = 0.0

    interval_end = gb.datetime.now() + gb.timedelta(seconds=INTERVAL_5_SEC)

    try:

        while (end_script == False):

            # When rotation passes reed switch, pin is LOW
            if not gb.GPIO.input(ANEMOMETER_GPIO):
                if not spun:
                    spun = True
                    spin_count = spin_count + 1
                    spin_total = spin_total + 1
                    gb.logging.debug("One rotation: %d, %d" %
                                        (spin_count, spin_total))
                    if (spin_total > 16000):
                        spin_total = 0
            # Anemometer not spun
            else:
                spun = False

            SLEEP_INTERVAL_STEP = SLEEP_INTERVAL_STEP + 1

            #--------------------------------------------
            # 5-second spin-count interval processing
            #--------------------------------------------
            if (SLEEP_INTERVAL_STEP >= INTERVAL_MAX):
                SLEEP_INTERVAL_STEP = 0
                current_date = gb.datetime.now()
                if (current_date.time() > interval_end.time()):
                    wind_speed = get_windspeed(spin_count, INTERVAL_5_SEC)
                    gb.logging.debug("rotations: %d, %d" %
                                        (spin_count, spin_total))
                    gb.logging.info("5-sec windspeed: %0.1f mph" % (wind_speed))
                    WIND_READING[iz] = wind_speed

                ix = ix + 1
                #--------------------------------------------
                # Process 1-minute and 5-minute averages
                #--------------------------------------------
                if (ix >= READINGS_1_MIN):
                    AVG_1_MIN = get_avg(iz, READINGS_1_MIN, READINGS_10_MIN)
                    AVG_5_MIN = get_avg(iz, READINGS_5_MIN, READINGS_10_MIN)
                    gb.logging.info("1-Min Avg: %0.1f mph, 5-min Avg: %0.1f mph" % (AVG_1_MIN, AVG_5_MIN))
                    ix = 0

                iz = iz + 1
                if (iz >= READINGS_10_MIN):
                    iz = 0
                interval_end = current_date + gb.timedelta(seconds=INTERVAL_5_SEC)
                spin_count = 0

            gb.time.sleep(0.05)

    except KeyboardInterrupt:
        tm_str = gb.get_date_with_seconds(gb.get_localdate_str())
        gb.logging.info("%s: Keyboard Interrrupt, stopping script" % (tm_str))
        end_script = True

    tm_str = gb.get_date_with_seconds(gb.get_localdate_str())
    gb.time.sleep(1)
    destroy()
    gb.logging.info("%s: MAIN EXIT" % (tm_str))
