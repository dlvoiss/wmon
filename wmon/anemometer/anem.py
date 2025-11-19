import gb
import signal

end_script = False

SLEEP_TIME = 0.05

MPH_1_RPS = 1.492  # 1 rotation per second (RPS) equals 1.492 MPH 

# Windspeed is calculated every 5 seconds, so 12 counts are
# one minute of data.  60 counts are 5-minutes of data 
READINGS_1_MIN = 12
READINGS_5_MIN = 60

MIN_5 = 5

# Wind readings are stored as counts.  The 5-second count is
# used to calculate the 5 second windspeed.  Likewise the
# counts in the READINGS_1_MIN rows in the wind_readings matrix
# are used to calculate the average windspeed over 1-minute and
# the entire matrix is used to calculate the 5-minute average

wind_readings = [[0.0 for _ in range(READINGS_1_MIN)] for _ in range(MIN_5)]

##############################################
# Setup
##############################################
def setup():
    tm_str = gb.get_date_with_seconds(gb.get_localdate_str())
    gb.logging.info("DIAG_LEVEL 0x%x" % (gb.DIAG_LEVEL))
    gb.logging.info("Setting up: %s" % (tm_str))
    gb.GPIO.setmode(gb.GPIO.BCM)
    gb.GPIO.setup(gb.ANEMOMETER_GPIO, gb.GPIO.IN, pull_up_down=gb.GPIO.PUD_UP)

##############################################
# Destroy
##############################################
def destroy():
    print("Cleaning up")
    gb.GPIO.cleanup()

#------------------------------------------
# Get count of anemometer rotations
# This check occurs at frequency SLEEP_TIME
#------------------------------------------
def get_spin_count(spun, spin_count, spin_total):

    # When rotation passes reed switch, pin is LOW
    if not gb.GPIO.input(gb.ANEMOMETER_GPIO):
        if not spun:
            spun = True
            spin_count = spin_count + 1
            spin_total = spin_total + 1
            if (gb.DIAG_LEVEL & gb.WIND_CNT) != 0:
                gb.logging.info("One rotation: %d, %d" %
                                (spin_count, spin_total))
            if (spin_total > 16000):
                spin_total = 0
    # Anemometer not spun
    else:
        spun = False

    return spun, spin_count, spin_total

#------------------------------------------
# Calculate windspeed in MPH for the specified
# interval.  This is used to calculate
# the 5-second windspeed
#------------------------------------------
def get_windspeed_from_count(cnt, interval):
    if (cnt == 0):
        speed = 0.0
    else:
        speed = (cnt * MPH_1_RPS) / interval

    return speed

#------------------------------------------
# Calculate 1-minute average in MPH
#------------------------------------------
def get_1_min_avg(wind_array):
    wind_avg = 0.0
    for mm in range(len(wind_array)):
        wind_avg += wind_array[mm]
    if (gb.DIAG_LEVEL & gb.WIND_DIR_DETAIL) != 0:
        gb.logging.info("wind cnt tally %.0f" % (wind_avg))
    wind_avg = (wind_avg * MPH_1_RPS) / (len(wind_array) * 5)

    return wind_avg

#------------------------------------------
# Calculate 5-minute average in MPH
#------------------------------------------
def get_5_min_avg(wind_matrix, all_data, indx):
    global MIN_5
    global READINGS_1_MIN

    wind_avg = 0.0
    mx = 0
    all_done = False
    denom = MIN_5 * READINGS_1_MIN * 5
    for mm in range(MIN_5):
        for nn in range(READINGS_1_MIN):
            if all_data or mx < (indx + 1):
                wind_avg += wind_matrix[mm][nn]
                mx += 1
            else:
                # Use data collected so far if less than 5 minutes worth
                # of data (this occurs at start up only)
                all_done = True
                denom = mx * 5
                break;
        if all_done:
            break;
           
    if (gb.DIAG_LEVEL & gb.WIND_DIR_DETAIL) != 0:
        gb.logging.info("wind cnt tally %.0f, denom: %d, mx: %d" %
                        (wind_avg, denom, mx))
    wind_avg = (wind_avg * MPH_1_RPS) / denom

    return wind_avg
    
#------------------------------------------
# Detect ctrl-C from keyboard
#------------------------------------------
def receive_TERM(signalNumber, frame):
    gb.logging.info("Received SIGTERM(%d)" % (signalNumber))
    end_script = True

##############################################
# main function
##############################################
if __name__ == '__main__':

    my_pid = gb.os.getpid()
    gb.logging.info("PID: %d" % (my_pid))
    signal.signal(signal.SIGTERM,receive_TERM)

    setup()

    INTERVAL_5_SEC = 5  # 5 seconds

    SLEEP_INTERVAL_STEP = 0
    INTERVAL_MAX = 100 # 5 seconds


    AVG_1_MIN = 0.0
    AVG_5_MIN = 0.0

    spun = True
    spin_count = 0 # reset to 0 every 5-seconds
    spin_total = 0 # reset to 0 once 16000 count (arbitrary) reached

    interval_end = gb.datetime.now() + gb.timedelta(seconds=INTERVAL_5_SEC)

    ix = 0
    have_5_min = False

    try:
        while (end_script == False):

            # count number of rotations
            spun, spin_count, spin_total = get_spin_count(spun, spin_count,
                                                       spin_total)

            SLEEP_INTERVAL_STEP = SLEEP_INTERVAL_STEP + 1
            data_logged = False

            #--------------------------------------------
            # 5-second spin-count interval processing
            #--------------------------------------------
            if (SLEEP_INTERVAL_STEP >= INTERVAL_MAX):
                SLEEP_INTERVAL_STEP = 0
                current_date = gb.datetime.now()
                if (current_date.time() > interval_end.time()):
                    tm_str = gb.get_date_with_seconds(gb.get_localdate_str())
                    wind_speed = get_windspeed_from_count(spin_count,
                                                          INTERVAL_5_SEC)
                    gb.logging.debug("%s: rotations: last 5-sec: %d, total: %d" %
                                        (tm_str, spin_count, spin_total))
                    if (gb.DIAG_LEVEL & gb.WIND_DIR_DETAIL) != 0:
                        gb.logging.info("%s: 5-sec windspeed: %0.1f mph cnt %d" %
                                    (tm_str, wind_speed, spin_count))
                    if (wind_speed < 0.0 or wind_speed > 100.0):
                        # Ignore out-of-range readings
                        continue

                    iz = ix % 12
                    iy = int(ix / 12)
                    wind_readings[iy][iz] = spin_count

                    if ix > 58 and not have_5_min:
                        # Indicate 5-minute log reporting can start
                        # This check is only needed at initial startup
                        # before initial 5-minutes worth of counts
                        # has been collected
                        have_5_min = True

                    # if the current row in the matrix is full, report 1-minute readings
                    if iz == 11:
                        AVG_1_MIN = get_1_min_avg(wind_readings[iy])
                        AVG_5_MIN = get_5_min_avg(wind_readings, have_5_min, ix)
                        print(f"{tm_str}: 1-min avg: {AVG_1_MIN:.1f}, 5-min avg: {AVG_5_MIN:.1f}")
                        #else:
                        #    # else clause only applies prior to collecting
                        #    # 5-minutes worth of data
                        #    print(f"{tm_str}: 1-min avg: {AVG_1_MIN:.1f}")

                    ix = ix + 1
                    if ix == READINGS_5_MIN:
                        ix = 0

                    # spin_count is reset every 5 seconds
                    spin_count = 0

            gb.time.sleep(SLEEP_TIME)

    except KeyboardInterrupt:
        tm_str = gb.get_date_with_seconds(gb.get_localdate_str())
        gb.logging.info("%s: Keyboard Interrrupt, stopping script" % (tm_str))
        end_script = True

    tm_str = gb.get_date_with_seconds(gb.get_localdate_str())
    gb.time.sleep(1)
    destroy()
    gb.logging.info("%s: MAIN EXIT" % (tm_str))
