import gb

import snsr
import wthr
import wavg
import lbls
import db

# The WeatherThread recieves sensor readings from the SensorThread
# and updates the current day min/max readings and past 24 hour
# min/max readings based on the sensor data.  Both the past 24
# hour data (last_24) and the current day (cur_day) data are
# written to the DB periodically.  The last_24 data are stored
# in DB table currentreadings and the cur_day are stored
# in DB table readingsToay

# Main loop sleep time
SLEEP_TIME = 10

# sim_mod is used when simulating start of new day for high/low average
sim_mod = 3
simulate_count = 0

# Control for last 24-hours periodic database writes
hr24_stat_updated = False        # Indicates if a last_24 variable updated
next_last24_write = gb.DFLT_TIME # Time after which next DB write can occur

# Past 24 hour structure
last_24 = {
    lbls.tm_FB_min : gb.DFLT_TIME,
    lbls.tempF_B_min : lbls.MAXF,
    lbls.tm_FB_max : gb.DFLT_TIME,
    lbls.tempF_B_max : lbls.MINF,
    lbls.tm_FD_min  : gb.DFLT_TIME,
    lbls.tempF_D_min : lbls.MAXF,
    lbls.tm_FD_max  : gb.DFLT_TIME,
    lbls.tempF_D_max : lbls.MINF,
    lbls.tm_mB_min  : gb.DFLT_TIME,
    lbls.press_mB_min : lbls.MAX_mB,
    lbls.tm_mB_max : gb.DFLT_TIME,
    lbls.press_mB_max : lbls.MIN_mB,
    lbls.tm_ft_min : gb.DFLT_TIME,
    lbls.press_sl_ft_min : lbls.MAX_mB,
    lbls.tm_ft_max  : gb.DFLT_TIME,
    lbls.press_sl_ft_max : lbls.MIN_mB,
    lbls.tm_var_min  : gb.DFLT_TIME,
    lbls.var_min : lbls.MAX_mB,
    lbls.tm_var_max  : gb.DFLT_TIME,
    lbls.var_max : lbls.MIN_mB,
    lbls.tm_humid_min  : gb.DFLT_TIME,
    lbls.humidity_min : lbls.MAX_HUM,
    lbls.tm_humid_max  : gb.DFLT_TIME,
    lbls.humidity_max : lbls.MIN_HUM,
}

# Control for current day periodic database writes
day_stat_updated = False          # Indicates if a cur_day variable updated
next_cur_day_write = gb.DFLT_TIME # Time after which next DB write can occur

# Current day (Today) structure
cur_day = {
    lbls.cur_date : gb.DFLT_TIME,
    lbls.tm_FB_min : gb.DFLT_TIME,
    lbls.tempF_B_min : lbls.MAXF,
    lbls.tm_FB_max : gb.DFLT_TIME,
    lbls.tempF_B_max : lbls.MINF,
    lbls.tm_FD_min  : gb.DFLT_TIME,
    lbls.tempF_D_min : lbls.MAXF,
    lbls.tm_FD_max  : gb.DFLT_TIME,
    lbls.tempF_D_max : lbls.MINF,
    lbls.tm_mB_min  : gb.DFLT_TIME,
    lbls.press_mB_min : lbls.MAX_mB,
    lbls.tm_mB_max : gb.DFLT_TIME,
    lbls.press_mB_max : lbls.MIN_mB,
    lbls.tm_ft_min : gb.DFLT_TIME,
    lbls.press_sl_ft_min : lbls.MAX_mB,
    lbls.tm_ft_max  : gb.DFLT_TIME,
    lbls.press_sl_ft_max : lbls.MIN_mB,
    lbls.tm_var_min  : gb.DFLT_TIME,
    lbls.var_min : lbls.MAX_mB,
    lbls.tm_var_max  : gb.DFLT_TIME,
    lbls.var_max : lbls.MIN_mB,
    lbls.tm_humid_min  : gb.DFLT_TIME,
    lbls.humidity_min : lbls.MAX_HUM,
    lbls.tm_humid_max  : gb.DFLT_TIME,
    lbls.humidity_max : lbls.MIN_HUM,
}

# Latest readings received from DHT/BME SensorThread
current = {
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

#######################################################################
#
# WeatherThread
# Process sensor data from BME280 and DHT-22 weather sensors (temperature,
# humidity and pressure.)  Check for 24-hr and current day (Today)
# highs and lows for each sensor reading
#
#######################################################################
class WeatherThread(gb.threading.Thread):

    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        gb.threading.Thread.__init__(self, group=group, target=target, name=name)
        self.args = args
        self.kwargs = kwargs
        self.name = name
        self.kill_received = False
   
    #--------------------------------------
    # Get current time and time 24 hours ago (24-hours prior)
    #--------------------------------------
    def get_datetimes(self):
        #---------------------------------------------
        # Set up current time (cur_time)... current_day is not updated
        # until after it is compared to day in cur_time
        #---------------------------------------------
        time_now = gb.datetime.now()
        time_24_prior = time_now - gb.timedelta(hours=24)
        if gb.DIAG_LEVEL & gb.WTHR_TIME_DETAIL:
            gb.logging.info("%s (time_now): time_24_prior: %s" %
                            (gb.get_date_with_seconds(str(time_now)),
                             gb.get_date_with_seconds(str(time_24_prior))))

        return(time_now, time_24_prior)


    def rcv_sensor_data(self, wthr_data):

        global current

        current[lbls.tmval]       = wthr_data[1]
        current[lbls.tempF_B]     = wthr_data[2]
        current[lbls.tempC_B]     = wthr_data[3]
        current[lbls.tempF_D]     = wthr_data[4]
        current[lbls.tempC_D]     = wthr_data[5]
        current[lbls.press_mB]    = wthr_data[6]
        current[lbls.press_sl_ft] = wthr_data[7]
        current[lbls.variance]    = wthr_data[8]
        current[lbls.humidity]    = wthr_data[9]

        if gb.DIAG_LEVEL & gb.WTHR_RCV:
            gb.logging.info("%s: Temp: %.1f F, Hum: %.1f%%, Press: %.1f mB" %
                            (gb.get_date_with_seconds(str(current[lbls.tmval])),
                             current[lbls.tempF_B],
                             current[lbls.humidity], current[lbls.press_mB]))

    #-----------------------------------------------------------
    # Check if current cur_day value is lower than current low value
    # k1:    new reading
    # k2:    current reading
    # k2_tm: current datetime
    #-----------------------------------------------------------
    def cmp_min(self, k1, k2, k2_tm):

        global current
        global cur_day

        upd = False

        # get current day: odd case can occur within a few seconds
        # of midnight where current day reset occurs before last
        # reading from prior day is processed.  Date check is needed
        # to address this corner case 
        c_datetime = current[lbls.tmval]
        c_day = c_datetime.day
        e_datetime = cur_day[k2_tm]
        e_day = e_datetime.day

        if round(current[k1], 1) < round(cur_day[k2], 1) or c_day != e_day:
            old_val = cur_day[k2]
            cur_day[k2] = current[k1]
            cur_day[k2_tm] = current[lbls.tmval]
            upd = True
            if gb.DIAG_LEVEL & gb.WTHR_DETAIL:
                gb.logging.info("cur_day: Updated %s: old: %.1f, new: %.1f" %
                                (k2, old_val, cur_day[k2]))
        return upd

    #-----------------------------------------------------------
    # Check if current cur_day value is higher than current high value
    # k1:    new reading
    # k2:    current reading
    # k2_tm: current datetime
    #-----------------------------------------------------------
    def cmp_max(self, k1, k2, k2_tm):

        global current
        global cur_day

        upd = False

        # get current day: odd case can occur within a few seconds
        # of midnight where current day reset occurs before last
        # reading from prior day is processed.  Date check is needed
        # to address this corner case 
        c_datetime = current[lbls.tmval]
        c_day = c_datetime.day
        e_datetime = cur_day[k2_tm]
        e_day = e_datetime.day

        if round(current[k1], 1) > round(cur_day[k2], 1) or c_day != e_day:
            old_val = cur_day[k2]
            cur_day[k2] = current[k1]
            cur_day[k2_tm] = current[lbls.tmval]
            upd = True
            if gb.DIAG_LEVEL & gb.WTHR_DETAIL:
                gb.logging.info("cur_day: Updated %s: old: %.1f, new: %.1f" %
                                (k2, old_val, cur_day[k2]))
        return upd
    
    #-----------------------------------------------------------
    # Reset readings for Today at start of each day
    # - date_today: datetime()
    #-----------------------------------------------------------
    def reset_cur_day(self, date_today):
        cur_day[lbls.cur_date] = date_today
        #if gb.DIAG_LEVEL & gb.WTHR_DAY_INIT or gb.DIAG_LEVEL & gb.WTHR_CUR:
        gb.logging.info("Resetting cur_day for %s" %
                            (gb.get_date_with_seconds(str(date_today))))

        cur_day[lbls.tm_FB_min] = gb.DFLT_TIME
        cur_day[lbls.tempF_B_min] = 120.0
        cur_day[lbls.tm_FB_max] = gb.DFLT_TIME
        cur_day[lbls.tempF_B_max] = 0.0
        cur_day[lbls.tm_FD_min] =  gb.DFLT_TIME
        cur_day[lbls.tempF_D_min] = 120.0
        cur_day[lbls.tm_FD_max] =  gb.DFLT_TIME
        cur_day[lbls.tempF_D_max] = 0.0
        cur_day[lbls.tm_mB_min] =  gb.DFLT_TIME
        cur_day[lbls.press_mB_min] = 1100.0
        cur_day[lbls.tm_mB_max] = gb.DFLT_TIME
        cur_day[lbls.press_mB_max] = 980.0
        cur_day[lbls.tm_ft_min] = gb.DFLT_TIME
        cur_day[lbls.press_sl_ft_min] = 1100.0
        cur_day[lbls.tm_ft_max] =  gb.DFLT_TIME
        cur_day[lbls.press_sl_ft_max] = 980.0
        cur_day[lbls.tm_var_min] =  gb.DFLT_TIME
        cur_day[lbls.var_min] = 0.0
        cur_day[lbls.tm_var_max] =  gb.DFLT_TIME
        cur_day[lbls.var_max] = 980.0
        cur_day[lbls.tm_humid_min] =  gb.DFLT_TIME
        cur_day[lbls.humidity_min] = 101.0
        cur_day[lbls.tm_humid_max] =  gb.DFLT_TIME
        cur_day[lbls.humidity_max] = 0.0

    #-----------------------------------------------------------
    # Check if current value is lower than low value for past 24 hours
    #-----------------------------------------------------------
    def cmp_24_min(self, k1, k2, k2_tm, k2_prior_day):

        global current
        global last_24
 
        upd = False

        # Update value if the new value is less than or if the
        # value's timestamp is more than 24 hrs old 

        if (round(current[k1], 1) < round(last_24[k2], 1)) or \
            (last_24[k2_tm] < k2_prior_day):
            old_val = last_24[k2]
            last_24[k2] = current[k1]
            last_24[k2_tm] = current[lbls.tmval]
            upd = True
            if gb.DIAG_LEVEL & gb.WTHR_DETAIL:
                gb.logging.info("last_24: Updated %s: old: %.1f, new: %.1f" %
                                (k2, old_val, last_24[k2]))
        return upd

    #-----------------------------------------------------------
    # Check if current value is higher than high value for past 24 hours
    #-----------------------------------------------------------
    def cmp_24_max(self, k1, k2, k2_tm, k2_prior_day):

        global current
        global last_24

        upd = False

        # Update value if the new value is greater than or if the
        # value's timestamp is more than 24 hrs old 
        if (round(current[k1], 1) > round(last_24[k2], 1)) or \
            (last_24[k2_tm] < k2_prior_day):
            old_val = last_24[k2]
            last_24[k2] = current[k1]
            last_24[k2_tm] = current[lbls.tmval]
            upd = True
            if gb.DIAG_LEVEL & gb.WTHR_DETAIL:
                gb.logging.info("last_24: Updated %s: old: %.1f, new: %.1f" %
                                (k2, old_val, last_24[k2]))
        return upd

    #---------------------------------------------------------
    # Request today min/max from DB on startup
    #---------------------------------------------------------
    def req_today_min_max(self, db_q_out):
        dbInfo = []
        db_msgType = db.DB_REQ_TODAY_MIN_MAX
        dbInfo.append(db_msgType)
        if (gb.DIAG_LEVEL & gb.SEND_TO_DB):
            gb.logging.info("Sending %s(%d)" %
                     (db.get_db_msg_str(db_msgType),db_msgType))
        db_q_out.put(dbInfo)

    #---------------------------------------------------------
    # Initialized today min/max from DB data on startup
    #---------------------------------------------------------
    def rcv_today_min_max(self, wthr_data, db_q_out):

        global cur_day

        if wthr_data[1] != 1:  # if DB_SUCCESS
            self.req_today_min_max(db_q_out)
            return False
        # [0] msgType
        # [1] DB_SUCCESS
        cur_day[lbls.cur_date] = wthr_data[2]      # [2]  tmstamp
        cur_day[lbls.tempF_B_min] = wthr_data[3]   # [3]  minTodaybmpf
        cur_day[lbls.tempF_B_max] = wthr_data[4]   # [4]  maxTodaybmpf
        cur_day[lbls.tm_FB_min] = wthr_data[5]     # [5]  minTodaybmpfts
        cur_day[lbls.tm_FB_max] = wthr_data[6]     # [6]  maxTodaybmpfts
        cur_day[lbls.tempF_D_min] = wthr_data[7]   # [7]  minTodaydhtf
        cur_day[lbls.tempF_D_max] = wthr_data[8]   # [8]  maxTodaydhtf
        cur_day[lbls.tm_FD_min] = wthr_data[9]     # [9]  minTodaydhtfts
        cur_day[lbls.tm_FD_max] = wthr_data[10]    # [10]  maxTodaydhtfts
        cur_day[lbls.humidity_min] = wthr_data[11] # [11] minTodayhumidity
        cur_day[lbls.humidity_max] = wthr_data[12] # [12] maxTodayhumidity
        cur_day[lbls.tm_humid_min] = wthr_data[13] # [13] minTodayhumts
        cur_day[lbls.tm_humid_max] = wthr_data[14] # [14] maxTodayhumts
        cur_day[lbls.press_mB_min] = wthr_data[15] # [15] lowTodaymB
        cur_day[lbls.press_mB_max] = wthr_data[16] # [16] higTodayhmB
        cur_day[lbls.tm_mB_min] = wthr_data[17]    # [17] lowTodaymBts
        cur_day[lbls.tm_mB_max] = wthr_data[18]    # [18] highTodaymBts

        if gb.DIAG_LEVEL & gb.WTHR_DAY_INIT or gb.DIAG_LEVEL & gb.WTHR_CUR:
            gb.logging.info("rcv_today_min_max: RECEIVED FROM DB")
            gb.logging.info("rcv_today_min_max: DHT tmn: %.1f tmx: %.1f, "
                        "HUM: hmn: %.1f hmx %.1f" %
                        (cur_day[lbls.tempF_D_min], cur_day[lbls.tempF_D_max],
                         cur_day[lbls.humidity_min],
                         cur_day[lbls.humidity_max]))
        return True

    #---------------------------------------------------------
    # Send min/max readings for today to DB
    #---------------------------------------------------------
    def send_today_min_max_to_db(self, db_q_out, cur_day):
        db_msgType = db.DB_TODAY_MIN_MAX
        dbInfo = []
        dbInfo.append(db_msgType)

        dbInfo.append(gb.get_date_with_seconds(str(cur_day[lbls.tm_FB_min])))
        dbInfo.append(cur_day[lbls.tempF_B_min])
        dbInfo.append(gb.get_date_with_seconds(str(cur_day[lbls.tm_FB_max])))
        dbInfo.append(cur_day[lbls.tempF_B_max])

        dbInfo.append(gb.get_date_with_seconds(str(cur_day[lbls.tm_FD_min])))
        dbInfo.append(cur_day[lbls.tempF_D_min])
        dbInfo.append(gb.get_date_with_seconds(str(cur_day[lbls.tm_FD_max])))
        dbInfo.append(cur_day[lbls.tempF_D_max])

        dbInfo.append(gb.get_date_with_seconds(str(cur_day[lbls.tm_mB_min])))
        dbInfo.append(cur_day[lbls.press_mB_min])
        dbInfo.append(gb.get_date_with_seconds(str(cur_day[lbls.tm_mB_max])))
        dbInfo.append(cur_day[lbls.press_mB_max])

        dbInfo.append(gb.get_date_with_seconds(str(cur_day[lbls.tm_humid_min])))
        dbInfo.append(cur_day[lbls.humidity_min])
        dbInfo.append(gb.get_date_with_seconds(str(cur_day[lbls.tm_humid_max])))
        dbInfo.append(cur_day[lbls.humidity_max])

        if gb.DIAG_LEVEL & gb.WTHR_DAY_INIT or gb.DIAG_LEVEL & gb.WTHR_CUR:
            gb.logging.info("send_today_min_max_to_db: SEND DAY MIN MAX to DB")
            gb.logging.info("send_today_min_max_to_db: "
                        "DHT tmn: %.1f tmx: %.1f, "
                        "HUM: hmn: %.1f hmx %.1f" %
                        (cur_day[lbls.tempF_D_min], cur_day[lbls.tempF_D_max],
                         cur_day[lbls.humidity_min],
                         cur_day[lbls.humidity_max]))

        if (gb.DIAG_LEVEL & gb.SEND_TO_DB):
            gb.logging.info("Sending %s(%d)" %
                     (db.get_db_msg_str(db_msgType),db_msgType))
        db_q_out.put(dbInfo)

    #---------------------------------------------------------
    # Send today's high and low readings to weather averages thread
    # Message is sent whenver a new day starts
    #---------------------------------------------------------
    def send_today_min_max_to_avg(self, wavg_q_out, cur_mo_id):

        tm_str = gb.get_date_with_seconds(gb.get_localdate_str())

        wavg_msgType = wavg.WAVG_TODAY_MIN_MAX
        wavgInfo = []
        wavgInfo.append(wavg_msgType)
        wavgInfo.append(cur_mo_id)
        mo_str = gb.id_to_month(cur_mo_id)
        wavgInfo.append(mo_str)

        wavgInfo.append(cur_day[lbls.tempF_D_min])
        wavgInfo.append(cur_day[lbls.tempF_D_max])

        #if gb.DIAG_LEVEL & gb.WTHR_DAY_INIT or gb.DIAG_LEVEL & gb.WTHR_CUR:
        gb.logging.info("%s: send_today_min_max_to_avg: "
                        "%s(%d): DAY MIN F: %.1f DAY MAX F: %.1f" %
                        (tm_str, mo_str, cur_mo_id, wavgInfo[3], wavgInfo[4]))

        #if (gb.DIAG_LEVEL & gb.SEND_TO_WAVG):
        gb.logging.info("%s: Sending %s(%d)" %
                     (tm_str, wavg.get_wavg_msg_str(wavg_msgType),wavg_msgType))
        wavg_q_out.put(wavgInfo)

    #---------------------------------------------------------
    # Request prior 24 hour min/max from DB on startup
    #---------------------------------------------------------
    def req_24hr_min_max(self, db_q_out):
        dbInfo = []
        db_msgType = db.DB_REQ_24HR_MIN_MAX
        dbInfo.append(db_msgType)
        if (gb.DIAG_LEVEL & gb.SEND_TO_DB):
            gb.logging.info("Sending %s(%d)" %
                     (db.get_db_msg_str(db_msgType),db_msgType))
        db_q_out.put(dbInfo)

    #---------------------------------------------------------
    # Initialized today min/max from DB data on startup
    #---------------------------------------------------------
    def rcv_24hr_min_max(self, wthr_data, db_q_out):

        global cur_day

        if wthr_data[1] != 1:  # if DB_SUCCESS
            self.req_24hr_min_max(db_q_out)
            return False
        # [0] msgType
        # [1] DB_SUCCESS
        last_24[lbls.cur_date] = wthr_data[2]      # [2]  tmstamp
        last_24[lbls.tempF_B_min] = wthr_data[3]   # [3]  minbmpf
        last_24[lbls.tempF_B_max] = wthr_data[4]   # [4]  maxbmpf
        last_24[lbls.tm_FB_min] = wthr_data[5]     # [5]  minbmpfts
        last_24[lbls.tm_FB_max] = wthr_data[6]     # [6]  maxbmpfts
        last_24[lbls.tempF_D_min] = wthr_data[7]   # [7]  mindhtf
        last_24[lbls.tempF_D_max] = wthr_data[8]   # [8]  maxdhtf
        last_24[lbls.tm_FD_min] = wthr_data[9]     # [9]  mindhtfts
        last_24[lbls.tm_FD_max] = wthr_data[10]    # [10]  maxdhtfts
        last_24[lbls.humidity_min] = wthr_data[11] # [11] minhumidity
        last_24[lbls.humidity_max] = wthr_data[12] # [12] maxhumidity
        last_24[lbls.tm_humid_min] = wthr_data[13] # [13] minhumidityts
        last_24[lbls.tm_humid_max] = wthr_data[14] # [14] maxhumidityts
        last_24[lbls.press_mB_min] = wthr_data[15] # [15] lowmB
        last_24[lbls.press_mB_max] = wthr_data[16] # [16] highmB
        last_24[lbls.tm_mB_min] = wthr_data[17]    # [17] lowmBts
        last_24[lbls.tm_mB_max] = wthr_data[18]    # [18] highmBts

        if gb.DIAG_LEVEL & gb.WTHR_DAY_INIT or gb.DIAG_LEVEL & gb.WTHR_24HR:
            gb.logging.info("rcv_24hr_min_max: RECEIVED FROM DB")
            gb.logging.info("rcv_24hr_min_max: DHT tmn: %.1f tmx: %.1f, "
                        "HUM: hmn: %.1f hmx %.1f" %
                        (last_24[lbls.tempF_D_min], last_24[lbls.tempF_D_max],
                         last_24[lbls.humidity_min],
                         last_24[lbls.humidity_max]))
        return True

    #---------------------------------------------------------
    # Send min/max readings for today to DB
    #---------------------------------------------------------
    def send_24hr_min_max_to_db(self, db_q_out):

        global current
        global last_24

        db_msgType = db.DB_24HR_MIN_MAX
        dbInfo = []
        dbInfo.append(db_msgType)

        dbInfo.append(current[lbls.tempF_B])
        dbInfo.append(gb.get_date_with_seconds(str(last_24[lbls.tm_FB_min])))
        dbInfo.append(last_24[lbls.tempF_B_min])
        dbInfo.append(gb.get_date_with_seconds(str(last_24[lbls.tm_FB_max])))
        dbInfo.append(last_24[lbls.tempF_B_max])

        dbInfo.append(current[lbls.tempF_D])
        dbInfo.append(gb.get_date_with_seconds(str(last_24[lbls.tm_FD_min])))
        dbInfo.append(last_24[lbls.tempF_D_min])
        dbInfo.append(gb.get_date_with_seconds(str(last_24[lbls.tm_FD_max])))
        dbInfo.append(last_24[lbls.tempF_D_max])

        dbInfo.append(current[lbls.press_mB])
        dbInfo.append(gb.get_date_with_seconds(str(last_24[lbls.tm_mB_min])))
        dbInfo.append(last_24[lbls.press_mB_min])
        dbInfo.append(gb.get_date_with_seconds(str(last_24[lbls.tm_mB_max])))
        dbInfo.append(last_24[lbls.press_mB_max])

        dbInfo.append(current[lbls.humidity])
        dbInfo.append(gb.get_date_with_seconds(str(last_24[lbls.tm_humid_min])))
        dbInfo.append(last_24[lbls.humidity_min])
        dbInfo.append(gb.get_date_with_seconds(str(last_24[lbls.tm_humid_max])))
        dbInfo.append(last_24[lbls.humidity_max])

        if gb.DIAG_LEVEL & gb.WTHR_DAY_INIT or gb.DIAG_LEVEL & gb.WTHR_24HR:
            gb.logging.info("send_24hr_min_max_to_db: SEND DAY MIN MAX to DB")
            gb.logging.info("send_24hr_min_max_to_db: "
                        "DHT tmn: %.1f tmx: %.1f, "
                        "HUM: hmn: %.1f hmx %.1f" %
                        (last_24[lbls.tempF_D_min], last_24[lbls.tempF_D_max],
                         last_24[lbls.humidity_min],
                         last_24[lbls.humidity_max]))

        if (gb.DIAG_LEVEL & gb.SEND_TO_DB):
            gb.logging.info("Sending %s(%d)" %
                     (db.get_db_msg_str(db_msgType),db_msgType))
        db_q_out.put(dbInfo)

    #---------------------------------------------------------
    # Record updates for min/max reading for today
    # Periodically send min/max data to database
    #---------------------------------------------------------
    def update_day_min_max(self, db_q_out, wavg_q_out, cur_time):

        global cur_day
        global next_cur_day_write
        global day_stat_updated
        global simulate_count
        global sim_mod

        day_stat_updated = False
        new_day = False

        date_00 = cur_time.replace(hour=0, minute=0, second=0, microsecond=0)
        if gb.DIAG_LEVEL & gb.WTHR_TIME_DETAIL:
            gb.logging.info("cur_day: %s, date_00: %s (NEW DAY)" %
                            (str(cur_time), str(date_00)))

        if gb.DIAG_LEVEL & gb.WTHR_SIMULATE_NEW_DAY:
            simulate_count += 1

        #---------------------------------------------------------
        # Check if this is the start of a new day
        # (or new month or new year)
        #---------------------------------------------------------
        if (date_00.year != cur_day[lbls.cur_date].year or \
            date_00.month != cur_day[lbls.cur_date].month or \
            date_00.day != cur_day[lbls.cur_date].day or \
            (gb.DIAG_LEVEL & gb.WTHR_SIMULATE_NEW_DAY and \
             simulate_count % sim_mod == 0)):
            if gb.DIAG_LEVEL & gb.WTHR_TIME_DETAIL:
                gb.logging.info("date_00.year: %d, "
                            "cur_day[lbls.cur_date].year %d" %
                            (date_00.year, cur_day[lbls.cur_date].year))
                gb.logging.info("date_00.month: %d, "
                            "cur_day[lbls.cur_date].month %d" %
                            (date_00.month, cur_day[lbls.cur_date].month))

            gb.logging.info("%s: update_day_min_max: "
                            "Start of NEW DAY: date_00: %s" %
                            (gb.get_date_with_seconds(str(cur_time)),
                             gb.get_date_with_seconds(str(date_00))))
            gb.logging.info("date_00.day: %d, cur_day[lbls.cur_date].day %d" %
                            (date_00.day, cur_day[lbls.cur_date].day))

            # Send today's high/low temperature to the averaging thread
            self.send_today_min_max_to_avg(wavg_q_out,
                                           cur_day[lbls.cur_date].month)

            # Reset data for today (new day starting)
            self.reset_cur_day(date_00)
            new_day = True

        # local_day_stat_updated True if any cur_day variable updated
        local_day_stat_updated = \
            self.cmp_min(lbls.tempF_B, lbls.tempF_B_min, lbls.tm_FB_min) | \
            self.cmp_max(lbls.tempF_B, lbls.tempF_B_max, lbls.tm_FB_max) | \
            self.cmp_min(lbls.tempF_D, lbls.tempF_D_min, lbls.tm_FD_min) | \
            self.cmp_max(lbls.tempF_D, lbls.tempF_D_max, lbls.tm_FD_max) | \
            self.cmp_min(lbls.press_mB, lbls.press_mB_min, lbls.tm_mB_min) | \
            self.cmp_max(lbls.press_mB, lbls.press_mB_max, lbls.tm_mB_max) | \
            self.cmp_min(lbls.press_sl_ft, lbls.press_sl_ft_min,
                         lbls.tm_ft_min) | \
            self.cmp_max(lbls.press_sl_ft, lbls.press_sl_ft_max,
                         lbls.tm_ft_max) | \
            self.cmp_min(lbls.variance, lbls.var_min,
                         lbls.tm_var_min) | \
            self.cmp_max(lbls.variance, lbls.var_max,
                         lbls.tm_var_max) | \
            self.cmp_min(lbls.humidity, lbls.humidity_min,
                         lbls.tm_humid_min) | \
            self.cmp_max(lbls.humidity, lbls.humidity_max,
                         lbls.tm_humid_max)

        if local_day_stat_updated:
            if gb.DIAG_LEVEL & gb.WTHR_DETAIL:
                gb.logging.info("update_day_min_max: cur_day var updated")
            day_stat_updated = True

        if local_day_stat_updated and gb.DIAG_LEVEL & gb.WTHR_DAY_INIT:
            gb.logging.info("update_day_min_max: BME tmn: %.1f tmx: %.1f, "
                        "DHT tmn: %.1f tmx: %.1f" %
                        (cur_day[lbls.tempF_B_min], cur_day[lbls.tempF_B_max],
                         cur_day[lbls.tempF_D_min], cur_day[lbls.tempF_D_max]))

        if new_day or (day_stat_updated and cur_time > next_cur_day_write):
            self.send_today_min_max_to_db(db_q_out, cur_day)
            next_cur_day_write = cur_time + gb.timedelta(minutes=3)
            day_stat_updated = False

    #---------------------------------------------------------
    # Record updates for min/max reading for today
    # Periodically send min/max data to database
    #---------------------------------------------------------
    def check_24hr_min_max(self, db_q_out, prior_24, cur_time):

        global next_last24_write
        global hr24_stat_updated

        local_hr24_stat_updated = \
            self.cmp_24_min(lbls.tempF_B, lbls.tempF_B_min,
                            lbls.tm_FB_min, prior_24) | \
            self.cmp_24_max(lbls.tempF_B, lbls.tempF_B_max,
                            lbls.tm_FB_max, prior_24) | \
            self.cmp_24_min(lbls.tempF_D, lbls.tempF_D_min,
                            lbls.tm_FD_min, prior_24) | \
            self.cmp_24_max(lbls.tempF_D, lbls.tempF_D_max,
                            lbls.tm_FD_max, prior_24) | \
            self.cmp_24_min(lbls.press_mB, lbls.press_mB_min,
                            lbls.tm_mB_min, prior_24) | \
            self.cmp_24_max(lbls.press_mB, lbls.press_mB_max,
                            lbls.tm_mB_max, prior_24) | \
            self.cmp_24_min(lbls.press_sl_ft, lbls.press_sl_ft_min,
                            lbls.tm_ft_min, prior_24) | \
            self.cmp_24_max(lbls.press_sl_ft, lbls.press_sl_ft_max,
                            lbls.tm_ft_max, prior_24) | \
            self.cmp_24_min(lbls.variance, lbls.var_min,
                            lbls.tm_var_min, prior_24) | \
            self.cmp_24_max(lbls.variance, lbls.var_max,
                            lbls.tm_var_max, prior_24) | \
            self.cmp_24_min(lbls.humidity, lbls.humidity_min,
                            lbls.tm_humid_min, prior_24) | \
            self.cmp_24_max(lbls.humidity, lbls.humidity_max,
                            lbls.tm_humid_max, prior_24)

        if local_hr24_stat_updated:
            if gb.DIAG_LEVEL & gb.WTHR_DETAIL:
                gb.logging.info("check_24hr_min_max: last_24 var updated")
            hr24_stat_updated = True

        if hr24_stat_updated and cur_time > next_last24_write:
            self.send_24hr_min_max_to_db(db_q_out)
            next_last24_write = cur_time + gb.timedelta(minutes=3)
            hr24_stat_updated = False

    #---------------------------------------------------------
    # Send keep-alive (I am alive) message to DB
    #---------------------------------------------------------
    def send_wthr_keep_alive(self, db_q_out):
        db_msgType = db.DB_WTHR_ALIVE
        dbInfo = []
        dbInfo.append(db_msgType)

        if (gb.DIAG_LEVEL & gb.SEND_TO_DB):
            gb.logging.info("Sending %s(%d)" %
                     (db.get_db_msg_str(db_msgType),db_msgType))
        db_q_out.put(dbInfo)

    ####################################################################
    # Weather run function
    ####################################################################
    def run(self):

        wthr_q_in = self.args[0]
        db_q_out = self.args[1]
        wavg_q_out = self.args[2]
        end_event = self.args[3]

        gb.logging.info("Running %s" % (self.name))

        cur_tempF = 0.0
        cur_humidity = 0.0
        cur_pressure_mB = 0.0

        have_weather_data = False
        have_today_min_max_data = False
        have_24hr_min_max_data = False

        alive_counter = 0
            
        self.req_today_min_max(db_q_out)
        self.req_24hr_min_max(db_q_out)

        while not end_event.isSet():
            #--------------------------------------
            # Check for incoming sensor messages
            #--------------------------------------
            tm_str = gb.get_date_with_seconds(gb.get_localdate_str())

            while not wthr_q_in.empty():
                weather_data = wthr_q_in.get()
                wthr_msgType = weather_data[0]

                if gb.DIAG_LEVEL & gb.WTHR_RCV:
                    gb.logging.debug("%s: Recvd: %s(%d)" %
                                    (tm_str,
                                     wthr.get_wthr_msg_str(wthr_msgType),
                                     wthr_msgType))

                if wthr_msgType == wthr.WTHR_SENSOR_DATA:
                    if gb.DIAG_LEVEL & gb.WTHR_RCV:
                        gb.logging.info("%s: Received sensor data" % (tm_str))
                    self.rcv_sensor_data(weather_data)
                    have_weather_data = True

                elif wthr_msgType == wthr.WTHR_TODAY_MIN_MAX:
                    if gb.DIAG_LEVEL & gb.WTHR_RCV:
                        gb.logging.info("%s: Received day min/max data" %
                        (tm_str))
                    have_today_min_max_data = \
                        self.rcv_today_min_max(weather_data, db_q_out)

                elif wthr_msgType == wthr.WTHR_24HR_MIN_MAX:
                    if gb.DIAG_LEVEL & gb.WTHR_RCV:
                        gb.logging.info("%s: Received 24hr min/max data" %
                        (tm_str))
                    have_24hr_min_max_data = \
                        self.rcv_24hr_min_max(weather_data, db_q_out)

                elif wthr_msgType == wthr.WTHR_EXIT:
                    # Shutdown likely occurs before this message
                    # has a chance to get processed
                    gb.logging.info("Cleaning up before EXIT")

                else:
                    gb.logging.error("%s: Invalid sensor message type: %d" %
                                     (tm_str, wthr_msgType))
                    gb.logging.error(weather_data)

            # Start database writes only after all initialization is complete
            # Confirm that readings from sensors (have_weather_data)
            # have been received, and cur_day and last_24 data have been
            # obtained from database (have_today_min_max_data and
            # have_24hr_min_max_data) before any updates to the
            # database tables are allowed

            if not have_weather_data or not have_today_min_max_data or \
               not have_24hr_min_max_data:
                gb.logging.info("%s: Weather: Waiting for data..." % (tm_str))
                if not have_weather_data:
                    gb.logging.info("%s: have_weather_data: False" %
                                    (tm_str))
                if not have_today_min_max_data:
                    gb.logging.info("%s: have_today_min_max_data: False" %
                                    (tm_str))
                if not have_24hr_min_max_data:
                    gb.logging.info("%s: have_24hr_min_max_data: False" %
                                    (tm_str))

                gb.time.sleep(SLEEP_TIME)
                continue

            cur_datetime, prior_24hr_datetime = self.get_datetimes()

            self.update_day_min_max(db_q_out, wavg_q_out, cur_datetime)
            self.check_24hr_min_max(db_q_out, prior_24hr_datetime, cur_datetime)

            if alive_counter >= 3:
                self.send_wthr_keep_alive(db_q_out)
                alive_counter = 0
            alive_counter += 1

            gb.time.sleep(SLEEP_TIME)

        gb.logging.info("Exiting %s" % (self.name))
