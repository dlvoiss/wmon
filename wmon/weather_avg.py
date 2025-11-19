import gb

import db
import snsr
import wthr
import wavg
import lbls

# The WeatherAvgThread recieves sensor readings from the SensorThread and
# updates the month-by-month high, low and average readings based on
# the sensor data.

# avgd: Average of daily temperatures between sun-up and sundown
# avgn: Average of nightly temperatures between sundown and sun-up

# Average of daily temperature between sunrise and sunset and average
# of nightly temperature between sunset and sunrise for current month
averages_dn = {
    lbls.cur_month       : '',
    lbls.cur_day_id      : 0,

    # Counter and average for daytime hours for current day
    lbls.readingd_tally  : 0,           # Not stored in DB
    lbls.avgdF           : float(0.0),  # Not stored in DB

    # Counter for daytimes for which average temperature collected and
    # weighted daytime average for current month
    lbls.day_tally       : 0,
    lbls.mo_avgd         : float(0.0),

    # Counter for nighttimes for which average temperature collected and
    # weighted nighttime average for current month
    lbls.readingn_tally  : 0,           # Not stored in DB
    lbls.avgnF           : float(0.0),  # Not stored in DB

    # Counter for nighttimes for which avg temp collected and weighted avg
    lbls.night_tally     : 0,
    lbls.mo_avgn         : float(0.0),
}

# avgh: Average of the highest temperature reading from each day of the month
# avgl: Average of the lowest temperature reading from each day of the month

# Average of daily highs and average of daily lows for current month
averages_hl = {
    lbls.cur_month       : '',

    lbls.avghightally    : 0,
    lbls.temp_FD_avgh    : float(0.0),

    lbls.avglowtally     : 0,
    lbls.temp_FD_avgl    : float(0.0),
}

CURRENT_MONTH = 0

SUNRISE_TODAY = gb.DFLT_TIME
SUNSET_TODAY = gb.DFLT_TIME
CUR_DAY_OR_NIGHT = wavg.DAYTIME

TEST_READING_CNT = 1
TEST_READING_MOD = 2

#######################################################################
#
# WeatherAvgThread
# Process sensor data from BME280 and DHT-22 weather sensors (temperature,
# humidity and pressure.)  Check for all-time and 30-day hights and
# lows for each reading
#
#######################################################################
class WeatherAvgThread(gb.threading.Thread):

    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        gb.threading.Thread.__init__(self, group=group, target=target, name=name)
        self.args = args
        self.kwargs = kwargs
        self.name = name
        self.kill_received = False

        self.last_high_low_tm = gb.DFLT_TIME

        # Latest readings received from sensors
        self.current = {
            lbls.tmval   : gb.DFLT_TIME,
            lbls.tempF_B : 0.0,
            lbls.tempC_B : 0.0,
            lbls.tempF_D : 0.0,
            lbls.tempC_D : 0.0,
            lbls.press_mB : 0.0,
            lbls.press_sl_ft : 0.0,
            lbls.variance : 0.0,
            lbls.humidity : 0.0,
        }

        #self.day_vals = {
        #    lbls.tmval : gb.DFLT_TIME,
        #    # Track high and low temperature for the day
        #    lbls.tempF_B_min : lbls.MAXF,
        #    lbls.tempF_B_max : lbls.MINF,
        #    # Running totals of low/high temperatures for current month
        #    wavg.maxf_tally : 0.0,
        #    wavg.maxf_cnt : 0,
        #    wavg.minf_tally : 0.0,
        #    wavg.minf_cnt : 0,
        #    # Running totals for daily daytime and nighttime averages
        #    wavg.df_tally : 0.0,
        #    wavg.df_cnt : 0,
        #    wavg.nf_tally : 0.0,
        #    wavg.nf_cnt : 0,
        #    # Running totals for monthly daytime and nighttime averages
        #    wavg.df_mo_tally: 0.0,
        #    wavg.df_mo_cnt : 0,
        #    wavg.nf_mo_tally: 0.0,
        #    wavg.nf_mo_cnt : 0,
        #}

        #self.day_vals[dayf_tally] += \
        #    (self.day_vals['dayf_tally'] / self.day_vals['dayf_cnt'])

    #------------------------------------------
    # Get sunrise and sunset for current day
    # Adjust for DST as needed
    #------------------------------------------
    def rcv_sunrise_sunset(self, avg_data):

        # NOTE: listing of sunrise/sunset for Mountain View is stored
        # in the DB table "sun".  The sunrise and sunset times for the
        # current day are stored in DB table, current_stats.  The
        # sunrise and sunset times returned from the DB are adjusted
        # for daylight savings time as needed

        global SUNRISE_TODAY
        global SUNSET_TODAY

        #print("avg_data: ", avg_data)

        dt = str(avg_data[1])
        sr = str(avg_data[2])
        ss = str(avg_data[3])

        dt_sr = dt + " " + sr
        dt_ss  = dt + " " + ss
        if gb.DIAG_LEVEL & gb.WAVG_SUNTIMES:
            gb.logging.info("sunrise: %s, sunset: %s" % (dt_sr, dt_ss))

        # create datetime objects for sunrise and sunset
        format_data = "%Y-%m-%d %H:%M:%S"
        SUNRISE_TODAY = gb.datetime.strptime(dt_sr, format_data)
        SUNSET_TODAY  = gb.datetime.strptime(dt_ss, format_data)

        if gb.DIAG_LEVEL & gb.WAVG_SUNTIMES:
            gb.logging.info("Sunrise/sunset date: %s" % (dt))
            gb.logging.info("Sunrise: %s, Sunset: %s" %
                            (str(SUNRISE_TODAY), str(SUNSET_TODAY)))
        return True

    #--------------------------------------------------
    # Check if new day is starting
    #--------------------------------------------------
    def chk_new_day(self, dt_tm, day_id):

        global TEST_READING_CNT
        global averages_dn
        global CUR_DAY_OR_NIGHT

        if wavg.WAVG_DIAG_LEVEL & wavg.WAVG_PROPAGATE_NIGHT:
            if TEST_READING_CNT % TEST_READING_MOD == 0:
                tm_str = gb.get_date_with_seconds(str(dt_tm))
                gb.logging.info("------------------------------------------")
                gb.logging.info("%s: chk_new_day: NEW DAY SIMULATED: %d" %
                                (tm_str, TEST_READING_CNT))
                gb.logging.info("------------------------------------------")
                if averages_dn[lbls.readingn_tally] == 0:
                    # Simulate nighttime readings if 0
                    gb.logging.info("%s: chk_new_day: "
                                    "SIMULATE NIGHT READINGS" % (tm_str))
                    averages_dn[lbls.readingn_tally] = 2
                    averages_dn[lbls.avgnF] = averages_dn[lbls.mo_avgn]
                return True

            TEST_READING_CNT += 1

        if dt_tm.day != day_id:
            return True
        return False

    #--------------------------------------------------
    # Check if transition from daytime to nighttime
    #--------------------------------------------------
    def chk_day_to_night(self, cur_state):

        global TEST_READING_CNT
        global averages_dn

        if wavg.WAVG_DIAG_LEVEL & wavg.WAVG_PROPAGATE_DAY:
            if TEST_READING_CNT % TEST_READING_MOD == 0:
                tm_str = gb.get_date_with_seconds(gb.get_localdate_str())
                gb.logging.info("------------------------------------------")
                gb.logging.info("%s: chk_day_to_night: "
                                "NIGHTFALL SIMULATED: %d" %
                                (tm_str, TEST_READING_CNT))
                gb.logging.info("------------------------------------------")
                if averages_dn[lbls.readingd_tally] == 0:
                    # Simulate daytime readings if 0
                    gb.logging.info("%s: chk_day_to_night: "
                                    "SIMULATE DAYTIME READINGS" % (tm_str))
                    averages_dn[lbls.readingd_tally] = 2
                    averages_dn[lbls.avgdF] = averages_dn[lbls.mo_avgd]
                return True

        if cur_state != wavg.NIGHTTIME:
            return True
        return False

    #--------------------------------------------------
    # Check if current time is between sunrise aand sunset
    #--------------------------------------------------
    def chk_daytime(self, cur_time, cur_day_or_night):

        global TEST_READING_CNT
        global SUNRISE_TODAY
        global SUNSET_TODAY

        daytm = False

        tm_str = gb.get_date_with_seconds(gb.get_localdate_str())
        if wavg.WAVG_DIAG_LEVEL & wavg.WAVG_PROPAGATE_DAY:
            gb.logging.info("%s: chk_daytime: %d" %
                            (tm_str, TEST_READING_CNT))

            TEST_READING_CNT += 1

            if (TEST_READING_CNT % TEST_READING_MOD) == 0:
                gb.logging.info("%s: chk_daytime: "
                                "NIGHTFALL SIMULATED: %d" %
                                (tm_str, TEST_READING_CNT))
                gb.logging.info("%s: Switching to Nighttime" % (tm_str))
                return daytm

        if cur_time > SUNRISE_TODAY and cur_time < SUNSET_TODAY:
            daytm = True
            if gb.DIAG_LEVEL & gb.WAVG_DAY_NIGHT and \
                cur_day_or_night == wavg.NIGHTTIME:
                gb.logging.info("%s: Switching to Daytime" % (tm_str))
        else:
            if gb.DIAG_LEVEL & gb.WAVG_DAY_NIGHT and \
                cur_day_or_night == wavg.DAYTIME:
                gb.logging.info("%s: Switching to Nighttime" % (tm_str))

        return daytm

    #--------------------------------------------------
    # Initialize daytime and nighttime running averages
    # for the month
    #--------------------------------------------------
    def rcv_day_night_avg_init(self, weather_data):

        global averages_dn

        averages_dn[lbls.cur_month]      = weather_data[1]  # cur_mo_str
        averages_dn[lbls.day_tally]      = weather_data[2]
        averages_dn[lbls.mo_avgd]        = float(weather_data[3])
        averages_dn[lbls.night_tally]    = weather_data[4]
        averages_dn[lbls.mo_avgn]        = float(weather_data[5])

        if gb.DIAG_LEVEL & gb.WAVG_DAY_NIGHT:
            gb.logging.info("mo: %s: day_tally %d mo_avgd %.1f, "
                            "night_tally %d, mo_avgn %.1f" %
                (averages_dn[lbls.cur_month],
                 averages_dn[lbls.day_tally], averages_dn[lbls.mo_avgd],
                 averages_dn[lbls.night_tally], averages_dn[lbls.mo_avgn]))
            gb.logging.info("mo: %s: d_tally %d avgd %.1f, "
                            "n_tally %d, avgn %.1f" %
                             (averages_dn[lbls.cur_month],
                              averages_dn[lbls.readingd_tally],
                              averages_dn[lbls.avgdF],
                              averages_dn[lbls.readingn_tally],
                              averages_dn[lbls.avgnF]))

        return True
       
    #--------------------------------------------------
    # At start of new month, reset running tallys for
    # average of daily highs and lows to 0
    #--------------------------------------------------
    def reset_day_night_month_end(self, cur_mo_str, cur_mo_id, new_day_id):

        global averages_dn

        tm_str = gb.get_date_with_seconds(gb.get_localdate_str())

        if gb.DIAG_LEVEL & gb.WAVG_DAY_NIGHT:
            gb.logging.info( \
                "%s: reset_day_night_month_end: New month: %s(%d)" %
                (tm_str, cur_mo_str, cur_mo_id))

        averages_dn[lbls.cur_month]      = cur_mo_str
        averages_dn[lbls.cur_day]        = new_day_id

        averages_dn[lbls.readingd_tally] = 0
        averages_dn[lbls.avgdF]          = float(0.0)
        averages_dn[lbls.day_tally]      = 0
        averages_dn[lbls.mo_avgd]        = float(0.0)
        averages_dn[lbls.readingn_tally] = 0
        averages_dn[lbls.avgnF]          = float(0.0)
        averages_dn[lbls.night_tally]    = 0
        averages_dn[lbls.mo_avgn]        = float(0.0)

    #----------------------
    # Propagate day or night readings to current month
    #----------------------
    def propagate_day_or_night_to_month(self, day_or_night):

        global averages_dn

        tm_str = gb.get_date_with_seconds(gb.get_localdate_str())

        if day_or_night == wavg.DAYTIME:
            if gb.DIAG_LEVEL & gb.WAVG_DAY_NIGHT:
                gb.logging.info("%s: PRE: propagate_day_or_night_to_month"
                            "readingd_tally: %d, avgdF %.1f" %
                            (tm_str, averages_dn[lbls.readingd_tally],
                             averages_dn[lbls.avgdF]))
                gb.logging.info("%s: PRE: day_tally: %d, mo_avgd %.1f" %
                            (tm_str, averages_dn[lbls.day_tally],
                             averages_dn[lbls.mo_avgd]))
                #print("type(averages_dn[lbls.readingd_tally]): %s" %
                #      (type(averages_dn[lbls.readingd_tally])))
                #print("type(averages_dn[lbls.day_tally]): %s" %
                #      (type(averages_dn[lbls.day_tally])))
                #print("type(averages_dn[lbls.mo_avgd]): %s" %
                #      (type(averages_dn[lbls.mo_avgd])))

            # Propagate today's DAYTIME average to running month average
            if averages_dn[lbls.readingd_tally] != 0:
                if averages_dn[lbls.day_tally] != 0:
                    month_avgd = averages_dn[lbls.mo_avgd] * \
                                   averages_dn[lbls.day_tally]
                    print("type(month_avgd): %s" % (type(month_avgd)))
                    month_avgd = month_avgd + averages_dn[lbls.avgdF]
                    averages_dn[lbls.day_tally] += 1
                    averages_dn[lbls.mo_avgd] = month_avgd / \
                                   averages_dn[lbls.day_tally]
                else:
                    averages_dn[lbls.day_tally] = 1
                    averages_dn[lbls.mo_avgd] = averages_dn[lbls.avgdF]
            else:
                if gb.DIAG_LEVEL & gb.WAVG_DAY_NIGHT:
                    gb.logging.info("%s: POST: "
                                    "propagate_day_or_night_to_month: "
                                    "day tally UNCHANGED" % (tm_str))

            if gb.DIAG_LEVEL & gb.WAVG_DAY_NIGHT:
                gb.logging.info("%s: POST: propagate_day_or_night_to_month: "
                                "day_tally: %d, mo_avgd %.1f" %
                                (tm_str, averages_dn[lbls.day_tally],
                                 averages_dn[lbls.mo_avgd]))
        else:
            if gb.DIAG_LEVEL & gb.WAVG_DAY_NIGHT:
                gb.logging.info("%s: PRE: propagate_day_or_night_to_month: "
                                "readingn_tally: %d, avgnF %.1f" %
                                (tm_str, averages_dn[lbls.readingn_tally],
                                 averages_dn[lbls.avgnF]))
                gb.logging.info("%s: PRE: night_tally: %d, avgn %.1f" %
                                (tm_str, averages_dn[lbls.night_tally],
                                 averages_dn[lbls.mo_avgn]))
            # Propagate today's NIGHTTIME average to running month average
            if averages_dn[lbls.readingn_tally] != 0:
                if averages_dn[lbls.night_tally] != 0:
                    month_avgn = averages_dn[lbls.mo_avgn] * \
                                   averages_dn[lbls.night_tally]
                    month_avgn = month_avgn + averages_dn[lbls.avgnF]
                    averages_dn[lbls.night_tally] += 1
                    averages_dn[lbls.mo_avgn] = month_avgn / \
                                   averages_dn[lbls.night_tally]
                else:
                    averages_dn[lbls.night_tally] = 1
                    averages_dn[lbls.mo_avgn] = averages_dn[lbls.avgnF]
            else:
                if gb.DIAG_LEVEL & gb.WAVG_DAY_NIGHT:
                    gb.logging.info("%s: POST: "
                                    "propagate_day_or_night_to_month: "
                                    "night tally UNCHANGED" % (tm_str))

            if gb.DIAG_LEVEL & gb.WAVG_DAY_NIGHT:
                gb.logging.info("%s: POST: propagate_day_or_night_to_month: "
                                "night_tally: %d, mo_avgn %.1f" %
                                (tm_str, averages_dn[lbls.night_tally],
                                 averages_dn[lbls.mo_avgn]))

    #--------------------------------------------------
    # Reset daytime and nighttime counts for current day
    #--------------------------------------------------
    def reset_day_night_day_end(self, cur_mo_id, new_day_id):

        global averages_dn

        tm_str = gb.get_date_with_seconds(gb.get_localdate_str())
 
        if gb.DIAG_LEVEL & gb.WAVG_DAY_NIGHT:
            gb.logging.info("%s: New day for day/night avg: %d/%d" %
                            (tm_str, cur_mo_id, new_day_id))

        #print("averages_dn\n", averages_dn)

        #----------------------
        # Reset daytime and nighttime counts for current day
        #----------------------
        averages_dn[lbls.cur_day_id]     = new_day_id
        averages_dn[lbls.readingd_tally] = 0
        averages_dn[lbls.avgdF]          = float(0.0)
        averages_dn[lbls.readingn_tally] = 0
        averages_dn[lbls.avgnF]          = float(0.0)

    #----------------------
    # Send daytime and nighttime temperature averages to DB
    #----------------------
    def send_day_night_avgs_to_DB(self, day_or_night, db_q_out):

        global averages_dn

        cur_mo_str = averages_dn[lbls.cur_month]
        cur_mo_id = gb.month_to_id(cur_mo_str)

        db_msgType = db.DB_DAY_NIGHT_AVG
        dbInfo = []
        dbInfo.append(db_msgType)
        dbInfo.append(cur_mo_id)
        dbInfo.append(cur_mo_str)
        dbInfo.append(day_or_night)
        dbInfo.append(averages_dn[lbls.day_tally])
        dbInfo.append(averages_dn[lbls.mo_avgd])
        dbInfo.append(averages_dn[lbls.night_tally])
        dbInfo.append(averages_dn[lbls.mo_avgn])

        if gb.DIAG_LEVEL & gb.WAVG_DAY_NIGHT:
            gb.logging.info("send_day_night_avgs_to_DB for %s(%d)" %
                            (cur_mo_str, cur_mo_id))
            gb.logging.info("dtally: %d davg: %.1f, ntally: %d navg %.1f" %
                        (averages_dn[lbls.day_tally],
                         averages_dn[lbls.mo_avgd],
                         averages_dn[lbls.night_tally],
                         averages_dn[lbls.mo_avgn]))
        if (gb.DIAG_LEVEL & gb.SEND_TO_DB):
            gb.logging.info("Sending %s(%d)" %
                     (db.get_db_msg_str(db_msgType),db_msgType))
        db_q_out.put(dbInfo)

    #----------------------
    # Request daytime and nighttime temperature running averages
    # from the DB for the current month
    #----------------------
    def req_cur_mo_day_night(self, dt, db_q_out):
        cur_mo_id = dt.month
        cur_mo_str = gb.id_to_month(cur_mo_id)

        db_msgType = db.DB_INIT_DAY_NIGHT_AVG
        dbInfo = []
        dbInfo.append(db_msgType)
        dbInfo.append(cur_mo_str)
        dbInfo.append(cur_mo_id)

        if (gb.DIAG_LEVEL & gb.SEND_TO_DB):
            gb.logging.info("Sending %s(%d)" %
                         (db.get_db_msg_str(db_msgType),db_msgType))

        db_q_out.put(dbInfo)

    #--------------------------------------------------
    # Use sensor data to update running tally of daytime and nighttime
    # temperatures for the day.
    #--------------------------------------------------
    def process_day_night_avgs(self, db_q_out):

        global TEST_READING_CNT
        global averages_dn
        global CUR_DAY_OR_NIGHT

        # Process latest readings received from SensorThread

        # Timestamp (datetime) from latest sensor reading
        snsr_tmstamp = self.current[lbls.tmval]

        mo_str = averages_dn[lbls.cur_month]
        day_id = averages_dn[lbls.cur_day_id]
        mo_id = gb.month_to_id(mo_str)

        tm_str = gb.get_date_with_seconds(gb.get_localdate_str())
        if wavg.WAVG_DIAG_LEVEL & wavg.WAVG_PROPAGATE_NIGHT or \
            wavg.WAVG_DIAG_LEVEL & wavg.WAVG_PROPAGATE_DAY:
            gb.logging.info("%s: process_day_night_avgs: %d" %
                            (tm_str, TEST_READING_CNT))

        #--------------------
        # Handle change in DAY and change in MONTH
        #--------------------
        if self.chk_new_day(snsr_tmstamp, day_id):
            #---------------
            # END OF DAY
            #---------------

            if gb.DIAG_LEVEL & gb.WAVG_DAY_NIGHT:
                gb.logging.info("%s: process_day_night_avgs: "
                                "END OF DAY" % (tm_str))
                gb.logging.info("snsr_tmstamp: %s, mo_str: %s, "
                                "mo_id: %d, snsr_tmstamp.month %d" %
                                (gb.get_date_with_seconds(str(snsr_tmstamp)),
                                 mo_str, mo_id, snsr_tmstamp.month))
                gb.logging.info("snsr_tmstamp.day: %d, day_id: %d" %
                                (snsr_tmstamp.day, day_id))

            # End of day, propagate night readings to running
            # month average
            self.propagate_day_or_night_to_month(wavg.NIGHTTIME)

            # Send nighttime data to DB
            self.send_day_night_avgs_to_DB(wavg.NIGHTTIME, db_q_out)

            # New day starting, get sunrise and sunset times
            sun_date = snsr_tmstamp.date()
            self.request_sunrise_sunset(db_q_out, sun_date)

            #---------------
            # Is then end of this day also the end of month?
            #---------------

            if snsr_tmstamp.month != mo_id:
                #---------------
                # END OF MONTH
                #---------------

                gb.logging.info("%s: process_day_night_avgs: END OF MONTH" %
                                (tm_str))
                gb.logging.info( \
                    "snsr_tmstamp: %s, mo_str: %s, mo_id: %d, snsr_tmstamp.month %d" %
                     (gb.get_date_with_seconds(str(snsr_tmstamp)),
                      mo_str, mo_id, snsr_tmstamp.month))
                gb.logging.info("snsr_tmstamp.day: %d, day_id: %d" %
                                (snsr_tmstamp.day, day_id))
                self.reset_day_night_month_end(mo_str, mo_id, snsr_tmstamp.day)

            else:
                #---------------
                # END OF DAY
                #---------------
                self.reset_day_night_day_end(mo_id, snsr_tmstamp.day)

        #--------------------
        # Check if sensor reading is for daytime or nighttime
        #--------------------
        if self.chk_daytime(snsr_tmstamp, CUR_DAY_OR_NIGHT):

            #--------------------
            # Process DAYTIME readings
            #--------------------

            if CUR_DAY_OR_NIGHT != wavg.DAYTIME:
                #--------------------
                # Changed from NIGHTTIME to DAYTIME
                #--------------------
                CUR_DAY_OR_NIGHT = wavg.DAYTIME

            # Process daytime readings
            if averages_dn[lbls.avgdF] == 0.0 or \
                averages_dn[lbls.readingd_tally] == 0:
                averages_dn[lbls.avgdF] = self.current[lbls.tempF_D]
                averages_dn[lbls.readingd_tally] = 1
                running_avgd = float(0.0)
            else:
                running_avgd = averages_dn[lbls.avgdF] * \
                              averages_dn[lbls.readingd_tally]
                running_avgd = running_avgd + self.current[lbls.tempF_D]
                averages_dn[lbls.readingd_tally] += 1
                averages_dn[lbls.avgdF] = running_avgd / \
                                          averages_dn[lbls.readingd_tally]

            if gb.DIAG_LEVEL & gb.WAVG_DAY_NIGHT:
                gb.logging.info("%s: POST DAYTIME: tally: %d, tempF %.1f" %
                            (gb.get_date_with_seconds(str(snsr_tmstamp)),
                             averages_dn[lbls.readingd_tally],
                             averages_dn[lbls.avgdF]))

        else:

            #--------------------
            # Process NIGHTTIME readings
            #--------------------

            if self.chk_day_to_night(CUR_DAY_OR_NIGHT):
                #--------------------
                # Changed from DAYTIME to NIGHTTIME, propagate
                # day average to running month average
                #--------------------
                self.propagate_day_or_night_to_month(wavg.DAYTIME)

                # Send daytime data to DB
                self.send_day_night_avgs_to_DB(wavg.DAYTIME, db_q_out)

                CUR_DAY_OR_NIGHT = wavg.NIGHTTIME

            # Process current sensor night time reading
            if averages_dn[lbls.avgnF] == 0.0 or \
               averages_dn[lbls.readingn_tally] == 0:
                averages_dn[lbls.avgnF] = self.current[lbls.tempF_D]
                averages_dn[lbls.readingn_tally] = 1
                running_avgn = float(0.0)
            else:
                running_avgn = averages_dn[lbls.avgnF] * \
                              averages_dn[lbls.readingn_tally]
                running_avgn = running_avgn + self.current[lbls.tempF_D]
                averages_dn[lbls.readingn_tally] += 1
                averages_dn[lbls.avgnF] = running_avgn / \
                                          averages_dn[lbls.readingn_tally]

            if gb.DIAG_LEVEL & gb.WAVG_DAY_NIGHT:
                gb.logging.info("%s: POST: NIGHTTIME: tally: %d, tempF %.1f" %
                            (gb.get_date_with_seconds(str(snsr_tmstamp)),
                             averages_dn[lbls.readingn_tally],
                             averages_dn[lbls.avgnF]))

    #--------------------------------------------------
    # Store temperature, humidity and pressure readings received
    # from the sensor thread
    #--------------------------------------------------
    def rcv_sensor_data(self, wthr_data):

        # tmval aka wthr_data[1] is instance of gb.datetime()

        self.current[lbls.tmval]       = wthr_data[1]
        self.current[lbls.tempF_B]     = wthr_data[2]
        self.current[lbls.tempC_B]     = wthr_data[3]
        self.current[lbls.tempF_D]     = wthr_data[4]
        self.current[lbls.tempC_D]     = wthr_data[5]
        self.current[lbls.press_mB]    = wthr_data[6]
        self.current[lbls.press_sl_ft] = wthr_data[7]
        self.current[lbls.variance]    = wthr_data[8]
        self.current[lbls.humidity]    = wthr_data[9]

        if gb.DIAG_LEVEL & gb.WAVG_RCV:
            gb.logging.info("%s: Temp: %.1f F, Hum: %.1f%%, Press: %.1f mB" %
                            (str(self.current[lbls.tmval]),
                             self.current[lbls.tempF_B],
                             self.current[lbls.humidity],
                             self.current[lbls.press_mB]))

    #----------------------
    # Request high and low temperature running averages
    # from the DB for the current month
    #----------------------
    def req_cur_mo_high_low(self, dt, db_q_out):

        cur_mo_id = dt.month
        cur_mo_str = gb.id_to_month(cur_mo_id)

        db_msgType = db.DB_INIT_HIGH_LOW_AVG
        dbInfo = []
        dbInfo.append(db_msgType)
        dbInfo.append(cur_mo_str)
        dbInfo.append(cur_mo_id)

        #if (gb.DIAG_LEVEL & gb.SEND_TO_DB):
        gb.logging.info("Sending %s(%d)" %
                     (db.get_db_msg_str(db_msgType),db_msgType))
        db_q_out.put(dbInfo)

    #--------------------------------------------------
    # Initialize high and low running averages for the month
    #--------------------------------------------------
    def rcv_cur_mo_high_low(self, weather_data):

        global averages_hl

        averages_hl[lbls.cur_month]      = weather_data[1]  # cur_mo_str
        averages_hl[lbls.avghightally]   = weather_data[2]
        averages_hl[lbls.temp_FD_avgh]   = float(weather_data[3])
        averages_hl[lbls.avglowtally]    = weather_data[4]
        averages_hl[lbls.temp_FD_avgl]   = float(weather_data[5])

        cur_mo_id = gb.month_to_id(averages_hl[lbls.cur_month])

        gb.logging.info("weather_avg: Received high/low avg for month: %s(%d)" %
                        (averages_hl[lbls.cur_month], cur_mo_id))

        gb.logging.info("mo: %s: high tally %d high_avg %.1f, "
                        "low tally %d, low_avg %.1f" %
            (averages_hl[lbls.cur_month],
             averages_hl[lbls.avghightally], averages_hl[lbls.temp_FD_avgh],
             averages_hl[lbls.avglowtally], averages_hl[lbls.temp_FD_avgl]))

        return True

    #--------------------------------------------------
    # At start of new month, reset running tallys for
    # average of daily highs and lows to 0
    #--------------------------------------------------
    def reset_high_low_avg_data(self, tm_str, cur_mo_str, cur_mo_id):

        global averages_hl

        gb.logging.info("%s: reset_high_low_avg_data: "
                        "START OF NEW MONTH: %s(%d)" %
                        (tm_str, cur_mo_str, cur_mo_id))
        averages_hl[lbls.cur_month] = cur_mo_str
        averages_hl[lbls.avghightally] = 0
        averages_hl[lbls.temp_FD_avgh] = float(0.0)
        averages_hl[lbls.avglowtally]  = 0
        averages_hl[lbls.temp_FD_avgl] = float(0.0)

    #--------------------------------------------------
    # Send month-to-date average high/low and number of days to DB
    #--------------------------------------------------
    def send_high_low_avg_to_DB(self, db_q_out, cur_mo_id, cur_mo_str,
                                avghightally, avgh,
                                avglowtally, avgl):
        db_msgType = db.DB_DAY_HIGH_LOW_AVG
        dbInfo = []
        dbInfo.append(db_msgType)

        dbInfo.append(cur_mo_id)
        dbInfo.append(cur_mo_str)
        dbInfo.append(avghightally)
        dbInfo.append(avgh)
        dbInfo.append(avglowtally)
        dbInfo.append(avgl)

        #if (gb.DIAG_LEVEL & gb.SEND_TO_DB):
        gb.logging.info("Sending %s(%d)" %
                     (db.get_db_msg_str(db_msgType),db_msgType))
        db_q_out.put(dbInfo)

    #--------------------------------------------------
    # Calculate month high/low averages to date
    # This function is called when a day change is detected
    # by weather.py (weather.py msgs weather_avg.py, which in
    # turn msgs database.py.)  weather.py tracks the high and low
    # temperature for the current day, whereas this function tracks the
    # running average for the high and low temperatures for the month
    #
    # This function calculates a running total for the month's high
    # and low temperatures.
    #
    # The running total for the average high and low values are
    # reconstitured by multiplying the current high and low average
    # by the number of days.  The new high and new low are then added to
    # these reconstitured values.  The day tally is incremented by one and
    # reconstitured values are divided by the new day tally.
    #
    # The daytime average and nighttime average temperatures are
    # calculated separately from this function.
    #--------------------------------------------------
    def rcv_todays_high_low_from_wthr(self, db_q_out, weather_data):

        global averages_hl

        cur_mo_id    = weather_data[1]
        cur_mo_str   = weather_data[2]
        cur_day_min = float(weather_data[3])
        cur_day_max  = float(weather_data[4])

        print("weather_data", weather_data)

        tm_str = gb.get_date_with_seconds(gb.get_localdate_str())
        gb.logging.info("%s: rcv_todays_high_low_from_wthr for %s(%d)" %
                        (tm_str, cur_mo_str, cur_mo_id))
        gb.logging.info("%s: rcv_todays_high_low_from_wthr: "
                        "averages_hl[lbls.cur_month]: %s" %
                        (tm_str, averages_hl[lbls.cur_month]))
        gb.logging.info("%s: rcv_todays_high_low_from_wthr: "
                         "TODAY MIN %.1f" %
                         (tm_str, cur_day_min))
        #gb.logging.info("%s: rcv_todays_high_low_from_wthr: " %
        #                 "TODAY MAX %.1f" %
        #                 (tm_str, cur_day_max))

        if averages_hl[lbls.cur_month] != cur_mo_str:
            self.reset_high_low_avg_data(tm_str, cur_mo_str, cur_mo_id)

        gb.logging.info("%s: rcv_todays_high_low_from_wthr: "
                        "PRE: averages_hl[lbls.avghightally]: %d, "
                        "averages_hl[lbls.temp_FD_avgh]: %.1f" %
                        (tm_str, averages_hl[lbls.avghightally],
                         averages_hl[lbls.temp_FD_avgh]))
        gb.logging.info("%s: rcv_todays_high_low_from_wthr: "
                        "PRE: averages_hl[lbls.avglowtally]: %d, "
                        "averages_hl[lbls.temp_FD_avgl]: %.1f" %
                        (tm_str, averages_hl[lbls.avglowtally],
                         averages_hl[lbls.temp_FD_avgl]))

        # Keep running tally of average high temperature for the month
        if averages_hl[lbls.avghightally] > 0:
            avgh = averages_hl[lbls.temp_FD_avgh] * \
                   averages_hl[lbls.avghightally]
            avgh = avgh + cur_day_max
            averages_hl[lbls.avghightally] += 1
            averages_hl[lbls.temp_FD_avgh] = \
                       avgh / float(averages_hl[lbls.avghightally])
            gb.logging.info("%s: Updated MAX for %s(%d): tally %d max %.1f" %
                            (tm_str, cur_mo_str, cur_mo_id,
                             averages_hl[lbls.avghightally],
                             averages_hl[lbls.temp_FD_avgh]))
        else:
            # Restarting high max for month
            averages_hl[lbls.temp_FD_avgh] = cur_day_max
            averages_hl[lbls.avghightally] = 1
            gb.logging.info("%s: Restart MAX for %s(%d): tally %d max %.1f" %
                            (tm_str, cur_mo_str, cur_mo_id,
                             averages_hl[lbls.avghightally],
                             averages_hl[lbls.temp_FD_avgh]))

        # Keep running tally of average low temperature for the month
        if averages_hl[lbls.avglowtally] > 0:
            avgl = averages_hl[lbls.temp_FD_avgl] * \
                   averages_hl[lbls.avglowtally]
            avgl = avgl + cur_day_min
            averages_hl[lbls.avglowtally] += 1
            averages_hl[lbls.temp_FD_avgl] = \
                       avgl / float(averages_hl[lbls.avglowtally])
            gb.logging.info("%s: Updated MIN for %s(%d): tally %d min %.1f" %
                            (tm_str, cur_mo_str, cur_mo_id,
                             averages_hl[lbls.avglowtally],
                             averages_hl[lbls.temp_FD_avgl]))
        else:
            # Restarting low min for month
            averages_hl[lbls.temp_FD_avgl] = cur_day_min
            averages_hl[lbls.avglowtally] = 1
            gb.logging.info("%s: Restart MIN for %s(%d): tally %d min %.1f" %
                            (tm_str, cur_mo_str, cur_mo_id,
                             averages_hl[lbls.avglowtally],
                             averages_hl[lbls.temp_FD_avgl]))

        gb.logging.info("%s: rcv_todays_high_low_from_wthr: "
                        "POST: averages_hl[lbls.avghightally]: %d, "
                        "averages_hl[lbls.temp_FD_avgh]: %.1f" %
                        (tm_str, averages_hl[lbls.avghightally],
                         averages_hl[lbls.temp_FD_avgh]))
        gb.logging.info("%s: rcv_todays_high_low_from_wthr: "
                        "POST: averages_hl[lbls.avglowtally]: %d, "
                        "averages_hl[lbls.temp_FD_avgl]: %.1f" %
                        (tm_str, averages_hl[lbls.avglowtally],
                         averages_hl[lbls.temp_FD_avgl]))

        self.send_high_low_avg_to_DB(db_q_out, cur_mo_id, cur_mo_str,
                                     averages_hl[lbls.avghightally],
                                     averages_hl[lbls.temp_FD_avgh],
                                     averages_hl[lbls.avglowtally],
                                     averages_hl[lbls.temp_FD_avgl])

    #----------------------------------
    # Request sunrise and sunset times
    #----------------------------------
    def request_sunrise_sunset(self, db_q_out, sun_date):

        db_msgType = db.DB_SUNTIMES
        dbInfo = []
        dbInfo.append(db_msgType)
        dbInfo.append(sun_date)
        if (gb.DIAG_LEVEL & gb.WAVG_SUNTIMES):
            gb.logging.info("Sending %s(%d)" %
                     (db.get_db_msg_str(db_msgType),db_msgType))
        db_q_out.put(dbInfo)

    #---------------------------------------------------------
    # Send keep-alive (I am alive) message to DB
    #---------------------------------------------------------
    def send_wavg_keep_alive(self, db_q_out):
        db_msgType = db.DB_WAVG_ALIVE
        dbInfo = []
        dbInfo.append(db_msgType)

        if (gb.DIAG_LEVEL & gb.SEND_TO_DB):
            gb.logging.info("Sending %s(%d)" %
                     (db.get_db_msg_str(db_msgType),db_msgType))
        db_q_out.put(dbInfo)

    ####################################################################
    # WeatherAvgThread run function
    ####################################################################
    def run(self):

        wavg_q_in = self.args[0]
        db_q_out = self.args[1]
        end_event = self.args[2]

        gb.logging.info("Running %s" % (self.name))


        tm_str = gb.get_date_with_seconds(gb.get_localdate_str())

        if wavg.WAVG_DIAG_LEVEL != 0x0:
            gb.logging.info("WAVG_DIAG_LEVEL set to 0x%x" %
                            (wavg.WAVG_DIAG_LEVEL))

        cur_datetime = gb.datetime.now()
        sun_date = cur_datetime.date()

        alive_counter = 0

        gb.logging.info("%s: Requesting SUNRISE/SUNSET for %s" %
                        (tm_str, sun_date))
        have_sunrise_sunset = False
        self.request_sunrise_sunset(db_q_out, sun_date)

        # Request running averages for current month
        # (NOTE: current day tallies are ignored on startup)
        if gb.DIAG_LEVEL & gb.WAVG_DAY_NIGHT:
            gb.logging.info("%s: Requesting day/night averages for %s" %
                            (tm_str, sun_date))
        have_day_night_avg = False
        self.req_cur_mo_day_night(cur_datetime, db_q_out)
        gb.logging.info("%s: Requesting high/low averages for %s" %
                        (tm_str, sun_date))
        have_high_low_avg = False
        self.req_cur_mo_high_low(cur_datetime, db_q_out)

        while not end_event.isSet():

            tm_str = gb.get_date_with_seconds(gb.get_localdate_str())
            cur_time = gb.datetime.now()

            #--------------------------------------
            # Check for incoming messages
            #--------------------------------------

            while not wavg_q_in.empty():
                weather_data = wavg_q_in.get()
                wthr_msgType = weather_data[0]

                if gb.DIAG_LEVEL & gb.WAVG_RCV:
                    gb.logging.debug("%s: Recvd: %s(%d)" %
                                    (tm_str,
                                     wavg.get_wavg_msg_str(wthr_msgType),
                                     wthr_msgType))

                if wthr_msgType == wavg.WAVG_SENSOR_DATA:
                    if gb.DIAG_LEVEL & gb.WAVG_RCV:
                        gb.logging.info("%s: Received sensor data" % (tm_str))
                    self.rcv_sensor_data(weather_data)

                    # have_sunrise_sunset is False only on initialization.
                    if have_sunrise_sunset and have_day_night_avg:
                        self.process_day_night_avgs(db_q_out)

                    else:
                        gb.logging.info("%s: Waiting for data..." % (tm_str))
                        if not have_sunrise_sunset:
                            gb.logging.info("%s: have_sunrise_sunset: False" %
                                            (tm_str))
                        if not have_day_night_avg:
                            gb.logging.info("%s: have_day_night_avg: False" %
                                            (tm_str))
                elif wthr_msgType == wavg.WAVG_DAY_NIGHT_INIT:
                    gb.logging.info("RECEIVED MONTH DAY/NIGHT AVERAGES")
                    have_day_night_avg = \
                        self.rcv_day_night_avg_init(weather_data)

                elif wthr_msgType == wavg.WAVG_SUNTIMES:
                    have_sunrise_sunset = \
                        self.rcv_sunrise_sunset(weather_data)

                elif wthr_msgType == wavg.WAVG_HIGH_LOW_INIT:
                    gb.logging.info("RECEIVED MONTH HIGH/LOW AVERAGES")
                    gb.logging.info("%s: Received month high/low avg from DB" %
                                        (tm_str))
                    have_high_low_avg = \
                        self.rcv_cur_mo_high_low(weather_data)

                elif wthr_msgType == wavg.WAVG_TODAY_MIN_MAX:
                    #if gb.DIAG_LEVEL & gb.WAVG_RCV:
                    gb.logging.info("%s: Received today min/max data" %
                                        (tm_str))
                    # Track average high and low daily temperatures
                    # for the current month.  High and low daily temperatures
                    # are tracked by the weatherThread (weather.py) and
                    # and are sent to this thread when the start of a
                    # new day is detected
                    
                    if have_high_low_avg:
                        self.rcv_todays_high_low_from_wthr(
                                             db_q_out, weather_data) 

                elif wthr_msgType == wavg.WAVG_EXIT:
                    # Shutdown likely occurs before this message
                    # has a chance to get processed
                    gb.logging.info("Cleaning up before EXIT")

                else:
                    gb.logging.error("Invalid sensor message type: %d" %
                                     (wthr_msgType))
                    gb.logging.error(weather_data)

            if alive_counter >= 3:
                self.send_wavg_keep_alive(db_q_out)
                alive_counter = 0
            alive_counter += 1

            gb.time.sleep(snsr.SENSOR_SLEEPTIME)

        gb.logging.info("Exiting %s" % (self.name))
