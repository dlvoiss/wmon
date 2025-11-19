import gb
import math

import an
import co
import db

myname = ""

# High speed polling to avoid missing an anemometer rotation
SLEEP_INTERVAL = 0.05


INTERVAL_5_SEC = 5 # 5 seconds

# One minute is 12 5-second measurement intervals
READINGS_1_MIN = 12
# 5 minutes is 60 5-second measurement intervals
READINGS_5_MIN = 60
# 10 minutes is 120 measurement intervals (max array size)
READINGS_10_MIN = 120

SECONDS_IN_HOUR = 3600

# 10 minutes worth of readings
# This allows taking running averages
WIND_READING = [0.0] * READINGS_10_MIN

AVG_1_MIN = 0.0
AVG_5_MIN = 0.0
HAVE_5_MIN = False

current_date = gb.datetime.now()

MAX_1_HOUR = 0.0
MAX_1_HOUR_TS = gb.datetime(1900, 1, 1, 11, 00, 00)
MAX_TODAY = 0.0
MAX_TODAY_TS = gb.datetime(1900, 1, 1, 11, 00, 00)
CUR_DAY = current_date.today().day

# Gusts are winds at least 10 mph greater than the average
# windspeed that last 20 seconds or less

GUST_INCREASE = 1.4  # 40% higher than 5 minute average
GUST_MIN = 2.0       # minimum mph for a gust

MAX_GUST_1_HOUR = 0.0
MAX_GUST_TODAY = 0.0

MONITOR_INTERVALS = 16  # 80 seconds, or 16 5-second intervals
INTERVAL_20_SEC = 4   # 20 seconds, or 4 5-second intervals
INTERVAL_1_MIN = 12   # 60 seconds, or 12 5-second intervals

# Potentially up to 6 gusts in one minute period, given 5-second intervals
# i.e., a maximum of 2 gusts in each 20-second interval
MAX_GUSTS_IN_20_SEC = 6

GUST = [0.0] * MONITOR_INTERVALS
GUST_MPH = [0.0] * MAX_GUSTS_IN_20_SEC
GUST_INTERVALS = [0] * MAX_GUSTS_IN_20_SEC
GUST_TS = [gb.datetime(1900, 1, 1, 11, 00, 00)] * MAX_GUSTS_IN_20_SEC

###########################################################
# Anemometer process
###########################################################
def log_windspeed(spd, spin, interval):
    tm_str = gb.get_date_with_seconds(gb.get_localdate_str())
    
    #spd = spd + 0.05
    if (gb.DIAG_LEVEL & gb.WIND_AVG_DETAIL):
        gb.logging.info("%s: WINDSPEED: %0.3f MPH; %d times in %s seconds" %
                        (tm_str, spd, spin, interval))

#########################################
# Get windspeed based on rotations of anemometer
# within a 5-second interval
#########################################
def get_windspeed(cnt, interval):
    if (cnt == 0):
        speed = 0.0
    else:
        speed = (cnt * 1.492) / interval
        
    return speed

#########################################
# Report max information
#########################################
def report_max(nm, pd, co_mp_q, msgType, date_time, mph):
    msg = []
    msg.append(msgType)
    msg.append(date_time)
    msg.append(mph)
    if (gb.DIAG_LEVEL & gb.GUSTS_MSG):
        gb.logging.info("%s(%d) sending %s(%d)" %
            (nm, pd, co.get_co_msg_str(msgType), msgType))
    co_mp_q.put(msg)

#########################################
# Check for max windspeed and update as needed
#########################################
def check_max(nm, pd, co_mp_q, mph, date_time):

    global MAX_1_HOUR
    global MAX_1_HOUR_TS
    global MAX_TODAY
    global MAX_TODAY_TS
    global CUR_DAY

    if (date_time.time() > MAX_1_HOUR_TS.time()):
        MAX_1_HOUR_TS = date_time + gb.timedelta(hours=1)
        MAX_1_HOUR = 0.0
        if (gb.DIAG_LEVEL & gb.WIND_MAX):
            gb.logging.info("%s(%d): Wind max next hour: %s" %
                            (nm, pd, str(MAX_1_HOUR_TS)))
        report_max(nm, pd, co_mp_q, co.CO_MP_MAX_1_HOUR, date_time, MAX_1_HOUR)

    if (mph > MAX_1_HOUR):
        MAX_1_HOUR = mph
        if (gb.DIAG_LEVEL & gb.WIND_MAX):
            gb.logging.info("%s(%d): 1-hour max windspeed: %0.1f" %
                            (nm, pd, MAX_1_HOUR))
        report_max(nm, pd, co_mp_q, co.CO_MP_MAX_1_HOUR, date_time, MAX_1_HOUR)

    if (CUR_DAY != date_time.today().day):
        if (gb.DIAG_LEVEL & gb.WIND_MAX):
            gb.logging.info("%s(%d): Wind max day change: was %d, not %d" %
                (nm, pd, CUR_DAY, date_time.today().day))
        CUR_DAY = date_time.today().day
        MAX_TODAY = 0.0
        report_max(nm, pd, co_mp_q, co.CO_MP_MAX_TODAY, date_time, MAX_TODAY)

    if (mph > MAX_TODAY):
        MAX_TODAY = mph
        if (gb.DIAG_LEVEL & gb.WIND_MAX):
            gb.logging.info("%s(%d): Today's max windspeed: %0.1f" %
                            (nm, pd, MAX_TODAY))
        report_max(nm, pd, co_mp_q, co.CO_MP_MAX_TODAY, date_time, MAX_TODAY)

#########################################
# Get subset over which to calculate average and standard deviation.
# The subset is generally "interval" in size (except during first
# 5 minutes after startup.)  "max" is maximum array size of windspeed
# readings array.  The current index into the windspeed array is "index"
#########################################
def get_reading_subset(index, interval, max):

    global WIND_READING
    global HAVE_5_MIN

    start_index = -1

    subset = [0.0] * READINGS_5_MIN

    # A full 5-minute reading requires 60 readings.  During first 5 minutes
    # after startup, fewer than 60 readings available, so limit 5 minute
    # average calculation to the number of readings available

    if (HAVE_5_MIN == False):
        if (interval == READINGS_5_MIN):
            if (index >= READINGS_5_MIN):
                HAVE_5_MIN = True
            else:
                interval = index + 1

    # Determine subset needed to calculate the average for either
    # a 1-minute or 5-minute interval

    end_index = index + 1

    if (end_index >= interval):
        # Able to use indexes in contiguous range
        start_index = end_index - interval
        subset = WIND_READING[start_index:end_index]
    else:  # start_index < interval
        # Low part of range
        start_index = max - (interval - end_index)
        subset = WIND_READING[start_index:] + WIND_READING[:end_index]

    return subset


#########################################
# Get windspeed average over the period "interval" when the
# maximum array size of windspeed readings is "max".  The
# current index into the windspeed array is "index"
#########################################
def get_avg(subset, index, interval, max):

    mean = 0.0
    calc_5_min = True
    minutes = 5

    if (interval == READINGS_1_MIN):
        calc_5_min = False
        minutes = 1

    # Get the average based on the selected subset
    mean = sum(subset) / len(subset)

    if (gb.DIAG_LEVEL & gb.WIND_AVG):
        gb.logging.info("%d-minute avg: %0.3f mph" % (minutes, mean))

    if (gb.DIAG_LEVEL & gb.WIND_AVG_DETAIL):
        if (calc_5_min == True):
            gb.logging.info("5-MINUTE AVERAGE Info")
        gb.logging.info("A: get_avg: subset len %d interval %d" %
                    (len(subset), interval))
        gb.logging.info("B: AVG: %0.3f" % (mean))
        if (gb.DIAG_LEVEL & gb.WIND_AVG5_DETAIL):
            print(subset)
            print()

    return mean

#########################################
# Calculate variance and standard deviation for windspeed
#########################################
def get_std_deviation(subset, mean, interval):

    minutes = 5

    # Calculate the variance
    variance = sum((x - mean) ** 2 for x in subset) / len(subset)

    # Calculate the standard deviation
    standard_deviation = math.sqrt(variance)

    if (interval == READINGS_1_MIN):
        minutes = 1
    if (gb.DIAG_LEVEL & gb.WIND_AVG):
        gb.logging.info("%d-minute avg standard deviation: %0.2f mph" %
                    (minutes, standard_deviation))

    return standard_deviation

#########################################
# Report gust information
#########################################
def report_gust(name, an_pid, co_mp_q, tm_str, wind_avg,
                gust_mph, gust_intervals):
    msg = []
    msgType = co.CO_MP_GUST
    msg.append(msgType)
    msg.append(tm_str)
    msg.append(wind_avg)
    msg.append(gust_mph)
    msg.append(gust_intervals)
    if (gb.DIAG_LEVEL & gb.GUSTS_MSG):
        gb.logging.info("%s(%d) sending %s(%d)" %
            (name, an_pid, co.get_co_msg_str(msgType), msgType))
    co_mp_q.put(msg)


########################################################
# Check if any gusts have occurred within last 80 seconds
########################################################
def check_gusts(name, an_pid, co_mp_q, index, wavg5, tm):

    global WIND_READING
    global INTERVAL_5_SEC

    # tm is gb.datetime

    if (gb.DIAG_LEVEL & gb.GUSTS_DETAIL):
        gb.logging.info("check_gusts(index: %d, 5-min avg: %0.1f, "
                        "gust min: %0.1f)" %
                        (index, wavg5, (wavg5 * GUST_INCREASE)))

    # grab windspeeds for last 60 seconds, i.e., 12 intervals
    # i.e., examine the last 80 seconds of data, or 16 5-second intervals

    gust_idx = 0

    wind_idx = index - INTERVAL_1_MIN
    if (wind_idx < 0):
        wind_idx = READINGS_10_MIN + wind_idx # gx is negative number here

    # Copy windspeeds (WIND_READING) for last 60 seconds to
    # gust array (GUST) to simplify processing
    # Wind speeds for 20-second period prior to the last 60  seconds
    # are already in the gust array

    for gx in range(INTERVAL_1_MIN):
        GUST[gx + INTERVAL_20_SEC] = WIND_READING[wind_idx]
        wind_idx = wind_idx + 1
        if (wind_idx >= (READINGS_10_MIN)):
            wind_idx = 0

    if (gb.DIAG_LEVEL & gb.GUSTS_DETAIL):
        gb.logging.info("Wind Speeds:")
        gb.logging.info("  %0.1f %0.1f %0.1f %0.1f %0.1f %0.1f %0.1f %0.1f" %
                    (GUST[0], GUST[1], GUST[2], GUST[3], GUST[4], GUST[5],
                     GUST[6], GUST[7]))
        gb.logging.info("  %0.1f %0.1f %0.1f %0.1f %0.1f %0.1f %0.1f %0.1f" %
                    (GUST[8], GUST[9], GUST[10], GUST[11], GUST[12], GUST[13],
                     GUST[14], GUST[15]))

    # Zero out mph readings for gusts
    for gx in range(MAX_GUSTS_IN_20_SEC):
        GUST_MPH[gx] = 0.0
        GUST_INTERVALS[gx] = 0
        GUST_TS[gx] = gb.datetime(1900, 1, 1, 11, 00, 00)

    zero_start = MONITOR_INTERVALS
    zero_end = MONITOR_INTERVALS
    gust_start = MONITOR_INTERVALS

    # Check gust array windspeeds to see if they are a gust
    # The checking starts at wind speeds from 80 seconds ago
    # (i.e., starts with 20 seconds already in the array)
    # Normally gusts are checked for time period starting
    # from 80 seconds ago, through 20 seconds ago. However,
    # if a potential gust is in-progress, there can be a need
    # to check the period starting 20 seconds ago, to see if
    # a valid gust termination occurs

    for gx in range(MONITOR_INTERVALS):
        # GUST is 40% higher than 5-minute average
        # and windspeed must be greater than GUST_MIN
        if wavg5 > 0.0 and GUST[gx] >= (wavg5 * GUST_INCREASE) and \
           GUST[gx] > GUST_MIN:
            gust_start = gx   # Potential start of gust
            if (gb.DIAG_LEVEL & gb.GUSTS_DETAIL):
                gb.logging.info("Potential start of gust: "
                                "gx: %d GUST[gx]: %.1f" % (gx, GUST[gx]))
        else: # Non-gust found, terminating any current gust
            if (gust_start != MONITOR_INTERVALS):
                # A gust is in progress, this reading terminated it
                # gust_duration is duration in 5-second intervals
                gust_duration = gx - gust_start
                if (zero_start != MONITOR_INTERVALS):
                    zero_end = gx

                if (gust_duration > INTERVAL_20_SEC):
                    # elevated windspeed, but lasted too long to be a gust
                    gust_start = MONITOR_INTERVALS
                    if (zero_start != MONITOR_INTERVALS):
                        # Gust did not intrude into most recent 20 seconds,
                        # so no need to zero as part of later copy
                        zero_start = MONITOR_INTERVALS
                        zero_end = MONITOR_INTERVALS
                else:
                    # Have a valid gust; calculate average gust windspeed
                    for gy in range(gust_start, gx):
                        GUST_MPH[gust_idx] = GUST_MPH[gust_idx] + GUST[gy]
                    GUST_MPH[gust_idx] = GUST_MPH[gust_idx] / gust_duration
                    GUST_INTERVALS[gust_idx] = gust_duration
                    gust_seconds = INTERVAL_5_SEC * gust_start
                    GUST_TS[gust_idx] = tm + gb.timedelta(seconds=(gust_seconds))

                    gust_start = MONITOR_INTERVALS
                    gust_idx = gust_idx + 1

            #else not a gust and no gust in progress

        if (gx >= (MONITOR_INTERVALS - INTERVAL_20_SEC)):
              if (gust_start == MONITOR_INTERVALS):
                  # No gust in progress, no need for further checks
                  # i.e., can skip remainder of range for the for-loop
                  break
              else:
                   # Zero these entries as part of later copy
                   # where lastest 20 seconds is copied to start of
                   # the 80-second interval array, GUST
                   zero_start = gx

    # Now copy the lastest 20 seconds (4 intervals) to the start of
    # the 80-second GUST array.  These will be processed when next
    # check for gusts occurs (i.e., in 60 seconds from now)

    if (gb.DIAG_LEVEL & gb.GUSTS_DETAIL):
        gb.logging.info("Windspeeds to copy:") 
        gb.logging.info("  %0.1f %0.1f %0.1f %0.1f" %
                         (GUST[12], GUST[13], GUST[14], GUST[15]))

    for gx in range(INTERVAL_20_SEC):
        if (((gx + INTERVAL_1_MIN) >= zero_start) and
            ((gx + INTERVAL_1_MIN) < zero_end)):
            if (gb.DIAG_LEVEL & gb.GUSTS_DETAIL):
                gb.logging.info("Zero on copy: index %d, %0.1f mph" %
                                (gx, GUST[gx]))
            GUST[gx] = 0.0
        else:
            #if (gb.DIAG_LEVEL & gb.GUSTS_DETAIL):
            #    gb.logging.info("Copying %d %0.1f" %
            #                    (gx, GUST[gx + INTERVAL_1_MIN]))
            GUST[gx] = GUST[gx + INTERVAL_1_MIN]

    if (gb.DIAG_LEVEL & gb.GUSTS_DETAIL):
        gb.logging.info("Number of gusts found: %d" % (gust_idx))
    if (gust_idx > 0):
        for gx in range(gust_idx):
            date_tm = gb.get_date_with_seconds(str(GUST_TS[gx]))
            if (gb.DIAG_LEVEL & gb.GUSTS):
                gb.logging.info("GUST %d: %s: %0.1f, %d intervals" %
                                (gx, date_tm, GUST_MPH[gx],
                                 GUST_INTERVALS[gx]))
            report_gust(name, an_pid, co_mp_q, date_tm, wavg5,
                        GUST_MPH[gx], GUST_INTERVALS[gx])

#########################################
# Report 1-minute and 5-minute wind speed averages
#########################################
def report_1_min_cnt(co_mp_q, avg1, sdev1, avg5, sdev5, windspeed):
    tm_str = gb.get_date_with_seconds(gb.get_localdate_str())
    msg = []
    msgType = co.CO_MP_SHORT_WINDSPEED
    msg.append(msgType)
    msg.append(avg1)
    msg.append(sdev1)
    msg.append(avg5)
    msg.append(sdev5)
    msg.append(windspeed)  # latest windspeed reading (non-averaged)
    if (gb.DIAG_LEVEL & gb.WIND_AVG_MSG):
        gb.logging.info("%s(%d) sending %s(%d)" %
            (myname, an_pid, co.get_co_msg_str(msgType), msgType))
    co_mp_q.put(msg)

#########################################
# Report 5-minute wind speed average
#########################################
def report_5_min_cnt(co_mp_q, avg5, sdev5):
    msg = []
    msgType = co.CO_MP_LONG_WINDSPEED
    msg.append(msgType)
    msg.append(avg5)
    msg.append(sdev5)
    if (gb.DIAG_LEVEL & gb.WIND_AVG_MSG):
        gb.logging.info("%s(%d) sending %s(%d)" %
            (myname, an_pid, co.get_co_msg_str(msgType), msgType))
    co_mp_q.put(msg)

#---------------------------------------------------------
# Send keep-alive (I am alive) message to DB via Coordinator
#---------------------------------------------------------
def send_an_keep_alive(co_mp_out):
    db_msgType = db.DB_AN_ALIVE
    coInfo = []
    coInfo.append(db_msgType)

    if (gb.DIAG_LEVEL & gb.SEND_TO_DB):
        gb.logging.info("Sending %s(%d) via coordinator" %
                 (db.get_db_msg_str(db_msgType),db_msgType))
    co_mp_out.put(coInfo)

#########################################
# Anemometer main program
#########################################
def anemometer(an_in, co_mp_out):

    global READINGS_1_MIN
    global READINGS_5_MIN
    global AVG_1_MIN
    global AVG_5_MIN
    global INTERVAL_5_SEC

    myname = gb.MP.current_process().name
    an_pid = gb.os.getpid()
    gb.logging.info("Running %s process, PID: %d" % (myname, an_pid))
    
    # Gusts are elevated wind speeds that last for 20 seconds or less
    # and exceeds average wind speed by at least 9 or 10 knots

    spun = True
    SLEEP_INTERVAL_STEP = 0
    INTERVAL_MAX = 100  # 5 seconds
    spin_count = 0
    spin_total = 0
    interval_end = gb.datetime.now() + gb.timedelta(seconds=INTERVAL_5_SEC)

    alive_counter = 0

    exit_process = False

    ix = 0   # index that controls reporting for 1 minute period
    iy  = 0  # index that controls reporting for 5 minute periods
    iz = 0   # index into WIND_READING array -- for both 1 & 5 minute periods

    wind_speed = 0.0

    while(exit_process == False):
        try:
            msg = ""
            while not an_in.empty():
                msg = an_in.get()
                msgType = msg[0]
                gb.logging.info("%s(%d): Received %s(%d)" %
                        (myname, an_pid, an.get_an_msg_str(msgType), msgType))

                if (msgType == an.AN_EXIT):
                    gb.logging.info("%s(%d) Cleanup prior to exit" %
                        (myname, an_pid))
                    exit_process = True

            ######################################################
            # Remainder of loop runs at SLEEP_INTERVAL frequencey
            # once incoming messages are processed above
            ######################################################

            if (exit_process == False):
                # When rotation passes reed switch, pin is LOW
                if not gb.GPIO.input(gb.ANEMOMETER_GPIO):
                    if not spun:
                        spun = True
                        spin_count = spin_count + 1
                        spin_total = spin_total + 1
                        if (gb.DIAG_LEVEL & gb.WIND_CNT):
                            gb.logging.info("One rotation: %d, %d" %
                                            (spin_count, spin_total))
                        if (spin_total > 16000):
                            spin_total = 0
                # Anemometer not spun
                else:
                    spun = False

                SLEEP_INTERVAL_STEP = SLEEP_INTERVAL_STEP + 1

                if (SLEEP_INTERVAL_STEP >= INTERVAL_MAX):
                    # the preceding if-clause not really needed,
                    # but prevents the need to call datetime.now()
                    # too frequently while waiting for the 5 seconds
                    # to pass
                    SLEEP_INTERVAL_STEP = 0
                    current_date = gb.datetime.now()

                    ##################################
                    # 5-second spin-count intervals
                    ##################################
                    if (current_date.time() > interval_end.time()):

                        wind_speed = get_windspeed(spin_count, INTERVAL_5_SEC)
                        if wind_speed > 75:
                            alive_counter += 1
                            gb.time.sleep(SLEEP_INTERVAL)
                            continue;

                        if (gb.DIAG_LEVEL & gb.WIND_AVG_DETAIL):
                            gb.logging.debug("ix: %s; iy %d" % (ix, iy))

                        # wind_speed recorded every 5 seconds
                        WIND_READING[iz] = wind_speed
                        check_max(myname, an_pid, co_mp_out,
                                  wind_speed, current_date)
                        ix = ix + 1
                        #--------------------------------------------
                        # Find 1- and 5-minute windspeed averages, check
                        # for any gusts and then report averages
                        #--------------------------------------------
                        if (ix >= READINGS_1_MIN):
                            subset_1_min = get_reading_subset(iz,
                                                READINGS_1_MIN,
                                                READINGS_10_MIN)
                            AVG_1_MIN = get_avg(subset_1_min, iz,
                                                READINGS_1_MIN,
                                                READINGS_10_MIN)
                            SDEV_1_MIN = get_std_deviation(subset_1_min,
                                                           AVG_1_MIN,
                                                           READINGS_1_MIN)

                            subset_5_min = get_reading_subset(iz,
                                               READINGS_5_MIN,
                                               READINGS_10_MIN)
                            AVG_5_MIN = get_avg(subset_5_min, iz,
                                                READINGS_5_MIN,
                                                READINGS_10_MIN)
                            SDEV_5_MIN = get_std_deviation(subset_5_min,
                                                           AVG_5_MIN,
                                                           READINGS_5_MIN)

                            check_gusts(myname, an_pid, co_mp_out,
                                        iz, AVG_5_MIN, current_date)
                            report_1_min_cnt(co_mp_out, AVG_1_MIN,SDEV_1_MIN,
                                             AVG_5_MIN, SDEV_5_MIN, wind_speed)
                            ix = 0

                        #--------------------------------------------
                        # Report 5-minute average windspeed
                        #--------------------------------------------
                        iy = iy + 1
                        if (iy >= READINGS_5_MIN):
                            report_5_min_cnt(co_mp_out, AVG_5_MIN, SDEV_5_MIN)
                            iy = 0

                        iz = iz + 1
                        if (iz >= READINGS_10_MIN):
                            iz = 0

                        if (gb.DIAG_LEVEL & gb.WIND_AVG_DETAIL):
                            log_windspeed(wind_speed, spin_count, INTERVAL_5_SEC)
                        interval_end = current_date + gb.timedelta(seconds=INTERVAL_5_SEC)
                        spin_count = 0

                if alive_counter >= 600:
                    # Coordinator relays message to DB
                    send_an_keep_alive(co_mp_out)
                    alive_counter = 0
                alive_counter += 1

                gb.time.sleep(SLEEP_INTERVAL)

        except KeyboardInterrupt:
            gb.logging.info("%s(%d) received keyboard interrupt" %
                            (myname, an_pid))

    # Log the windspeed when exiting the process
    wind_speed = get_windspeed(spin_count, INTERVAL_5_SEC)
    log_windspeed(wind_speed, spin_count, INTERVAL_5_SEC)
    gb.logging.info("%s process exiting..." % (myname))
