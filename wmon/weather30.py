import gb

import db
import snsr
import wthr
import wthr30
import lbls

# The Weather30Thread recieves sensor readings from the SensorThread and
# updates the prior 30 days min/max readings, current month min/max
# readings and all-time min/max readings based on the sensor data.
# The 30-day, month, and all-time data are written to the DB periodically.
# The 30-day data are stored in DB table readings30, the month data stored in
# DB table monthdata, and the all-time data in DB table alltimedata.

# Main loop sleep time
SLEEP_TIME = 10

# Control for last 30-day min/max periodic database writes
last_30day_stat_updated = False # Indicates if an 30-day variable updated
next_30day_write = gb.DFLT_TIME # Time after which next DB write can occur

# Last 30 days structure
last_30days = {
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
    lbls.var_min     : lbls.MAX_mB,
    lbls.tm_var_max  : gb.DFLT_TIME,
    lbls.var_max     : lbls.MIN_mB,
    lbls.tm_humid_min  : gb.DFLT_TIME,
    lbls.humidity_min : lbls.MAX_HUM,
    lbls.tm_humid_max  : gb.DFLT_TIME,
    lbls.humidity_max : lbls.MIN_HUM,
}

# Control for monthly min/max for current year periodic database writes
mo_year_updated = False           # Indicates if a mo_year variable updated
next_mo_year_write = gb.DFLT_TIME # Time after which next DB write can occur
have_mo_year_min_max_data = False

# Monthly min/max readings for current year structure (current month)
mo_year = {
    lbls.cur_month : '',

    lbls.tm_FD_min  : gb.DFLT_TIME,
    lbls.tempF_D_min : lbls.MAXF,
    lbls.tm_FD_max  : gb.DFLT_TIME,
    lbls.tempF_D_max : lbls.MINF,

    lbls.tm_humid_min  : gb.DFLT_TIME,
    lbls.humidity_min : lbls.MAX_HUM,
    lbls.tm_humid_max  : gb.DFLT_TIME,
    lbls.humidity_max : lbls.MIN_HUM,

    lbls.tm_mB_min  : gb.DFLT_TIME,
    lbls.press_mB_min : lbls.MAX_mB,
    lbls.tm_mB_max : gb.DFLT_TIME,
    lbls.press_mB_max : lbls.MIN_mB,
}

# Control for all-time min/max periodic database writes
all_time_stat_updated = False     # Indicates if an all-time variable updated
next_alltime_write = gb.DFLT_TIME # Time after which next DB write can occur
have_all_time_min_max_data = False

# All-time readings structure
all_time = {
    lbls.cur_month : '',

    lbls.tm_FD_min  : gb.DFLT_TIME,
    lbls.tempF_D_min : lbls.MAXF,
    lbls.tm_FD_max  : gb.DFLT_TIME,
    lbls.tempF_D_max : lbls.MINF,

    lbls.tm_humid_min  : gb.DFLT_TIME,
    lbls.humidity_min : lbls.MAX_HUM,
    lbls.tm_humid_max  : gb.DFLT_TIME,
    lbls.humidity_max : lbls.MIN_HUM,

    lbls.tm_mB_min  : gb.DFLT_TIME,
    lbls.press_mB_min : lbls.MAX_mB,
    lbls.tm_mB_max : gb.DFLT_TIME,
    lbls.press_mB_max : lbls.MIN_mB,
}

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
# Weather30 Thread
# Process sensor data from BME280 and DHT-22 weather sensors (temperature,
# humidity and pressure.)  Check for all-time and 30-day highs and
# lows for each reading
#
#######################################################################
class Weather30Thread(gb.threading.Thread):

    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        gb.threading.Thread.__init__(self, group=group, target=target, name=name)
        self.args = args
        self.kwargs = kwargs
        self.name = name
        self.kill_received = False

    #--------------------------------------
    # Get current time and time 30 days ago (one day prior)
    #--------------------------------------
    def get_times(self):
        #---------------------------------------------
        # Set up current time (cur_time)... current_day is not updated
        # until after it is compared to day in cur_time
        #---------------------------------------------
        time_now = gb.datetime.now()
        time_30d_prior = time_now - gb.timedelta(days=30)
        if gb.DIAG_LEVEL & gb.WTHR30_TIME_DETAIL:
            gb.logging.info("time_now %s, time_30d_prior: %s" %
                            (str(time_now), str(time_30d_prior)))

        return(time_now, time_30d_prior)

    #--------------------------------------------------
    # Store temperature, humidity and pressure readings received
    # from the sensor thread
    #--------------------------------------------------
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

        if gb.DIAG_LEVEL & gb.WTHR30_RCV:
            gb.logging.info("%s: Temp: %.1f F, Hum: %.1f%%, Press: %.1f mB" %
                            (str(current[lbls.tmval]), current[lbls.tempF_B],
                            current[lbls.humidity], current[lbls.press_mB]))

    #-----------------------------------------------------------
    # Check if current sensor value is lower than the existing month's
    # all-time low value
    #-----------------------------------------------------------
    def cmp_all_time_min(self, k1, k2, k2_tm):

        global current
        global all_time

        upd = False

        if round(current[k1], 1) < round(all_time[k2], 1):
            old_val = all_time[k2]
            all_time[k2] = current[k1]
            all_time[k2_tm] = current[lbls.tmval]
            upd = True
            if gb.DIAG_LEVEL & gb.WTHR30_ALL_TIME:
                gb.logging.info("all_time: Updated %s: old: %.1f, new: %.1f" %
                                (k2, old_val, all_time[k2]))
        return upd

    #-----------------------------------------------------------
    # Check if current sensor value is greater than the existing month's
    # all-time high value
    #-----------------------------------------------------------
    def cmp_all_time_max(self, k1, k2, k2_tm):

        global current
        global all_time

        upd = False

        if round(current[k1], 1) > round(all_time[k2], 1):
            old_val = all_time[k2]
            all_time[k2] = current[k1]
            all_time[k2_tm] = current[lbls.tmval]
            upd = True
            if gb.DIAG_LEVEL & gb.WTHR30_ALL_TIME:
                gb.logging.info("all_time: Updated %s: old: %.1f, new: %.1f" %
                                (k2, old_val, all_time[k2]))
        return upd

    #-----------------------------------------------------------
    # Check if current sensor value is lower than the existing 30-day low
    # value or if existing 30-day value is older than 30 days
    #-----------------------------------------------------------
    def cmp_30d_min(self, k1, k2, k2_tm, k2_prior_30day):

        global current
        global last_30days
 
        upd = False

        # Update value if the new value is less than the existing
        # value or if the existing value's timestamp is more
        # than 30 days old 
        if (round(current[k1], 1) < round(last_30days[k2], 1)) or \
            (last_30days[k2_tm] < k2_prior_30day):
            old_val = last_30days[k2]
            last_30days[k2] = current[k1]
            last_30days[k2_tm] = current[lbls.tmval]
            upd = True
            if gb.DIAG_LEVEL & gb.WTHR30_30DAY:
                gb.logging.info(
                         "last_30days: Updated %s: old: %.1f, new: %.1f" %
                         (k2, old_val, last_30days[k2]))
        return upd

    #-----------------------------------------------------------
    # Check if current sensor value is greater than the existing 30-day
    # high value or if existing 30-day value is older than 30 days
    #-----------------------------------------------------------
    def cmp_30d_max(self, k1, k2, k2_tm, k2_prior_30day):

        global current
        global last_30days

        upd = False

        # Update value if the new value is greater than the existing
        # value or if the existing value's timestamp is more
        # than 30 days old 
        if (round(current[k1], 1) > round(last_30days[k2], 1)) or \
            (last_30days[k2_tm] < k2_prior_30day):
            old_val = last_30days[k2]
            last_30days[k2] = current[k1]
            last_30days[k2_tm] = current[lbls.tmval]
            upd = True
            if gb.DIAG_LEVEL & gb.WTHR30_30DAY:
                gb.logging.info("last_30days: "
                                "Updated %s: old: %.1f, new: %.1f" %
                                (k2, old_val, last_30days[k2]))
        return upd

    #---------------------------------------------------------
    # Request all-time min/max from DB on startup
    #---------------------------------------------------------
    def req_all_time_min_max(self, db_q_out, month_id):
        dbInfo = []
        db_msgType = db.DB_REQ_ALL_TIME_MIN_MAX
        dbInfo.append(db_msgType)
        dbInfo.append(month_id)
        if (gb.DIAG_LEVEL & gb.SEND_TO_DB):
            gb.logging.info("Sending %s(%d): %s" %
                     (db.get_db_msg_str(db_msgType),db_msgType, month_id))
        db_q_out.put(dbInfo)

    #---------------------------------------------------------
    # Initialize all-time min/max from DB data on startup
    #---------------------------------------------------------
    def rcv_all_time_min_max(self, wthr_data, db_q_out, month_id):

        if wthr_data[1] != 1:  # if DB_SUCCESS
            self.req_all_time_min_max(db_q_out, month_id)
            return False

        # [0] msgType
        # [1] DB_SUCCESS
        all_time[lbls.id]           = wthr_data[2]  # [2]  id/month 1-12
        all_time[lbls.cur_month]    = wthr_data[3]  # [3]  month (str)

        all_time[lbls.tm_FD_min]    = wthr_data[4]  # [4]  mintempfts
        all_time[lbls.tempF_D_min]  = wthr_data[5]  # [5]  mintempf
        all_time[lbls.tm_FD_max]    = wthr_data[6]  # [6]  maxtempfts
        all_time[lbls.tempF_D_max]  = wthr_data[7]  # [7]  maxtempf
        all_time[lbls.tm_humid_min] = wthr_data[8]  # [8]  minhumts
        all_time[lbls.humidity_min] = wthr_data[9]  # [9]  minhum
        all_time[lbls.tm_humid_max] = wthr_data[10] # [10] maxhumts
        all_time[lbls.humidity_max] = wthr_data[11] # [11] mxhum
        all_time[lbls.tm_mB_min]    = wthr_data[12] # [12] lowmBts
        all_time[lbls.press_mB_min] = wthr_data[13] # [13] lowmB
        all_time[lbls.tm_mB_max]    = wthr_data[14] # [14] highmBts
        all_time[lbls.press_mB_max] = wthr_data[15] # [15] highmB

        if gb.DIAG_LEVEL & gb.WTHR_DAY_INIT or gb.DIAG_LEVEL & gb.WTHR30_30DAY:
            gb.logging.info("rcv_all_time_min_max: RECEIVED FROM DB")
            gb.logging.info("rcv_all_time_min_max: DHT tmn: %.1f tmx: %.1f, "
                        "HUM: hmn: %.1f hmx %.1f" %
                        (all_time[lbls.tempF_D_min],
                         all_time[lbls.tempF_D_max],
                         all_time[lbls.humidity_min],
                         all_time[lbls.humidity_max]))
        return True

    #---------------------------------------------------------
    # Send all-time min/max readings to DB
    #---------------------------------------------------------
    def send_all_time_min_max_to_db(self, db_q_out, cur_mo_id):

        global all_time

        db_msgType = db.DB_ALLTIME_MIN_MAX
        dbInfo = []
        dbInfo.append(db_msgType)

        cur_month = gb.id_to_month(cur_mo_id)
        dbInfo.append(cur_mo_id)
        dbInfo.append(cur_month)

        dbInfo.append(gb.get_date_with_seconds(
                                str(all_time[lbls.tm_FD_max])))
        dbInfo.append(all_time[lbls.tempF_D_min])
        dbInfo.append(gb.get_date_with_seconds(
                                str(all_time[lbls.tm_mB_min])))
        dbInfo.append(all_time[lbls.tempF_D_max])

        dbInfo.append(gb.get_date_with_seconds(
                                str(all_time[lbls.tm_humid_min])))
        dbInfo.append(all_time[lbls.humidity_min])
        dbInfo.append(gb.get_date_with_seconds(
                                str(all_time[lbls.tm_humid_max])))
        dbInfo.append(all_time[lbls.humidity_max])

        dbInfo.append(gb.get_date_with_seconds(
                                str(all_time[lbls.tm_mB_min])))
        dbInfo.append(all_time[lbls.press_mB_min])
        dbInfo.append(gb.get_date_with_seconds(
                                str(all_time[lbls.tm_mB_max])))
        dbInfo.append(all_time[lbls.press_mB_max])

        if gb.DIAG_LEVEL & gb.WTHR30_30DAY:
            gb.logging.info("send_all_time_min_max_to_db: SND to DB")
            gb.logging.info("send_all_time_min_max_to_db: "
                        "DHT tmn: %.1f tmx: %.1f, "
                        "HUM: hmn: %.1f hmx %.1f" %
                        (all_time[lbls.tempF_D_min],
                         all_time[lbls.tempF_D_max],
                         all_time[lbls.humidity_min],
                         all_time[lbls.humidity_max]))

        if (gb.DIAG_LEVEL & gb.SEND_TO_DB):
            gb.logging.info("Sending %s(%d)" %
                     (db.get_db_msg_str(db_msgType),db_msgType))
        db_q_out.put(dbInfo)

    #---------------------------------------------------------
    # Record updates for min/max all-time reading for current month.
    # Periodically send min/max data to database if updates occur
    #---------------------------------------------------------
    def update_all_time_min_max(self, db_q_out, cur_time, cur_mo_id):

        global all_time
        global all_time_stat_updated
        global next_alltime_write
        global have_all_time_min_max_data

        all_time_mo_id = gb.month_to_id(all_time[lbls.cur_month])
        if cur_mo_id != all_time_mo_id:
            gb.logging.info("cur_mo_id: %d, all_time_mo_id: %d" %
                            (cur_mo_id, all_time_mo_id))

            # Setting have_all_time_min_max_data to False triggers
            # a wait-loop on DB updates until all time data is updated

            have_all_time_min_max_data = False
            self.req_all_time_min_max(db_q_out, cur_mo_id)
            gb.logging.info("Start of new month detected: %d" % (cur_mo_id))
            return
            
        local_alltime_stat_updated = \
            self.cmp_all_time_min(lbls.tempF_D,
                                  lbls.tempF_D_min, lbls.tm_FD_min) | \
            self.cmp_all_time_max(lbls.tempF_D,
                                  lbls.tempF_D_max, lbls.tm_FD_max) | \
            self.cmp_all_time_min(lbls.press_mB,
                                  lbls.press_mB_min, lbls.tm_mB_min) | \
            self.cmp_all_time_max(lbls.press_mB,
                                  lbls.press_mB_max, lbls.tm_mB_max) | \
            self.cmp_all_time_min(lbls.humidity, lbls.humidity_min,
                                  lbls.tm_humid_min) | \
            self.cmp_all_time_max(lbls.humidity, lbls.humidity_max,
                                  lbls.tm_humid_max)

        if local_alltime_stat_updated:
            if gb.DIAG_LEVEL & gb.WTHR30_DETAIL:
                gb.logging.info("local_alltime_stat_updated: "
                                "all_time var updated")
            all_time_stat_updated = True

        if (all_time_stat_updated and cur_time > next_alltime_write):
            self.send_all_time_min_max_to_db(db_q_out, cur_mo_id)
            next_alltime_write = cur_time + gb.timedelta(minutes=3)
            all_time_stat_updated = False

    #---------------------------------------------------------
    # Request mo_year min/max from DB on startup
    #---------------------------------------------------------
    def req_mo_year_min_max(self, db_q_out, month_id):
        dbInfo = []
        db_msgType = db.DB_REQ_MO_YEAR_MIN_MAX
        dbInfo.append(db_msgType)
        dbInfo.append(month_id)
        if (gb.DIAG_LEVEL & gb.SEND_TO_DB):
            gb.logging.info("Sending %s(%d): %s" %
                     (db.get_db_msg_str(db_msgType),db_msgType, month_id))
        db_q_out.put(dbInfo)

    #---------------------------------------------------------
    # Initialize mo_year min/max from DB data on startup
    #---------------------------------------------------------
    def rcv_mo_year_min_max(self, wthr_data, db_q_out, month_id):

        if wthr_data[1] != 1:  # if DB_SUCCESS
            self.req_mo_year_min_max(db_q_out, month_id)
            return False

        # [0] msgType
        # [1] DB_SUCCESS
        mo_year[lbls.id]           = wthr_data[2]  # [2]  id/month 1-12
        mo_year[lbls.cur_month]    = wthr_data[3]  # [3]  month (str)

        mo_year[lbls.tm_FD_min]    = wthr_data[4]  # [4]  mintempfts
        mo_year[lbls.tempF_D_min]  = wthr_data[5]  # [5]  mintempf
        mo_year[lbls.tm_FD_max]    = wthr_data[6]  # [6]  maxtempfts
        mo_year[lbls.tempF_D_max]  = wthr_data[7]  # [7]  maxtempf
        mo_year[lbls.tm_humid_min] = wthr_data[8]  # [8]  minhumts
        mo_year[lbls.humidity_min] = wthr_data[9]  # [9]  minhum
        mo_year[lbls.tm_humid_max] = wthr_data[10] # [10] maxhumts
        mo_year[lbls.humidity_max] = wthr_data[11] # [11] mxhum
        mo_year[lbls.tm_mB_min]    = wthr_data[12] # [12] lowmBts
        mo_year[lbls.press_mB_min] = wthr_data[13] # [13] lowmB
        mo_year[lbls.tm_mB_max]    = wthr_data[14] # [14] highmBts
        mo_year[lbls.press_mB_max] = wthr_data[15] # [15] highmB

        if gb.DIAG_LEVEL & gb.WTHR30_MO_INIT or \
            gb.DIAG_LEVEL & gb.WTHR30_MO_YEAR:
            gb.logging.info("rcv_mo_year_min_max: RECEIVED FROM DB")
            gb.logging.info("rcv_mo_year_min_max: DHT tmn: %.1f tmx: %.1f, "
                        "HUM: hmn: %.1f hmx %.1f" %
                        (mo_year[lbls.tempF_D_min],
                         mo_year[lbls.tempF_D_max],
                         mo_year[lbls.humidity_min],
                         mo_year[lbls.humidity_max]))

        # Confirm readings are for current year, if not
        # reset reading to default values
        yr = gb.datetime.now()
        yr_mo = mo_year[lbls.tm_FD_min]
        if yr_mo.year != yr.year:
            print(mo_year[lbls.tm_FD_min], lbls.tm_FD_min,
                  " year does not match current year")
            mo_year[lbls.tm_FD_min] = gb.DFLT_TIME
            mo_year[lbls.tempF_D_min] = 120.0

        yr_mo = mo_year[lbls.tm_FD_max]
        if yr_mo.year != yr.year:
            print(mo_year[lbls.tm_FD_max], lbls.tempF_D_max,
                  " year does not match current year")
            mo_year[lbls.tm_FD_max] =  gb.DFLT_TIME
            mo_year[lbls.tempF_D_max] = 0.0

        yr_mo = mo_year[lbls.tm_humid_min]
        if yr_mo.year != yr.year:
            print(mo_year[lbls.tm_humid_min], lbls.humidity_min,
                  " year does not match current year")
            mo_year[lbls.tm_humid_min] =  gb.DFLT_TIME
            mo_year[lbls.humidity_min] = 101.0

        yr_mo = mo_year[lbls.tm_humid_max]
        if yr_mo.year != yr.year:
            print(mo_year[lbls.tm_humid_max], lbls.humidity_max,
                  " year does not match current year")
            mo_year[lbls.tm_humid_max] =  gb.DFLT_TIME
            mo_year[lbls.humidity_max] = 0.0

        yr_mo = mo_year[lbls.tm_mB_min]
        if yr_mo.year != yr.year:
            print(mo_year[lbls.tm_mB_min], lbls.press_mB_min,
                  " year does not match current year")
            mo_year[lbls.tm_mB_min] =  gb.DFLT_TIME
            mo_year[lbls.press_mB_min] = 1100.0

        yr_mo = mo_year[lbls.tm_mB_max]
        if yr_mo.year != yr.year:
            print(mo_year[lbls.tm_mB_max], lbls.press_mB_max,
                  " year does not match current year")
            mo_year[lbls.tm_mB_max] = gb.DFLT_TIME
            mo_year[lbls.press_mB_max] = 980.0

        return True

    #---------------------------------------------------------
    # Send min/max readings for mo_year to DB
    #---------------------------------------------------------
    def send_mo_year_min_max_to_db(self, db_q_out, cur_mo_str):
        db_msgType = db.DB_MO_YEAR_MIN_MAX
        dbInfo = []
        dbInfo.append(db_msgType)

        cur_mo_id = gb.month_to_id(cur_mo_str)
        dbInfo.append(cur_mo_id)
        dbInfo.append(cur_mo_str)

        dbInfo.append(gb.get_date_with_seconds(str(mo_year[lbls.tm_FD_max])))
        dbInfo.append(mo_year[lbls.tempF_D_min])
        dbInfo.append(gb.get_date_with_seconds(str(mo_year[lbls.tm_mB_min])))
        dbInfo.append(mo_year[lbls.tempF_D_max])

        dbInfo.append(gb.get_date_with_seconds(str(mo_year[lbls.tm_humid_min])))
        dbInfo.append(mo_year[lbls.humidity_min])
        dbInfo.append(gb.get_date_with_seconds(str(mo_year[lbls.tm_humid_max])))
        dbInfo.append(mo_year[lbls.humidity_max])

        dbInfo.append(gb.get_date_with_seconds(str(mo_year[lbls.tm_mB_min])))
        dbInfo.append(mo_year[lbls.press_mB_min])
        dbInfo.append(gb.get_date_with_seconds(str(mo_year[lbls.tm_mB_max])))
        dbInfo.append(mo_year[lbls.press_mB_max])

        if gb.DIAG_LEVEL & gb.WTHR30_MO_YEAR:
            gb.logging.info("send_mo_year_min_max_to_db: SND to DB")
            gb.logging.info("send_mo_year_min_max_to_db: "
                        "DHT tmn: %.1f tmx: %.1f, "
                        "HUM: hmn: %.1f hmx %.1f" %
                        (mo_year[lbls.tempF_D_min],
                         mo_year[lbls.tempF_D_max],
                         mo_year[lbls.humidity_min],
                         mo_year[lbls.humidity_max]))

        if (gb.DIAG_LEVEL & gb.SEND_TO_DB):
            gb.logging.info("Sending %s(%d)" %
                     (db.get_db_msg_str(db_msgType),db_msgType))
        db_q_out.put(dbInfo)

    #-----------------------------------------------------------
    # Reset readings for mo_yearl at start of each month
    #-----------------------------------------------------------
    def reset_cur_mo_year(self, cur_mo_str):

        if gb.DIAG_LEVEL & gb.WTHR30_MO_INIT:
            gb.logging.info("NEW MONTH: Resetting mo_year for %s" %
                            (cur_mo_str))

        mo_year[lbls.cur_month] = cur_mo_str

        mo_year[lbls.tm_FD_min] =  gb.DFLT_TIME
        mo_year[lbls.tempF_D_min] = 120.0
        mo_year[lbls.tm_FD_max] =  gb.DFLT_TIME
        mo_year[lbls.tempF_D_max] = 0.0

        mo_year[lbls.tm_humid_min] =  gb.DFLT_TIME
        mo_year[lbls.humidity_min] = 101.0
        mo_year[lbls.tm_humid_max] =  gb.DFLT_TIME
        mo_year[lbls.humidity_max] = 0.0

        mo_year[lbls.tm_mB_min] =  gb.DFLT_TIME
        mo_year[lbls.press_mB_min] = 1100.0
        mo_year[lbls.tm_mB_max] = gb.DFLT_TIME
        mo_year[lbls.press_mB_max] = 980.0

    #-----------------------------------------------------------
    # Check if current sensor value is lower than the existing month
    # (current year) low value
    #-----------------------------------------------------------
    def cmp_mo_year_min(self, cur_var, mo_yr_min, mo_yr_tm):

        global current
        global mo_year

        upd = False

        if round(current[cur_var], 1) < round(mo_year[mo_yr_min], 1):
            old_val = mo_year[mo_yr_min]
            mo_year[mo_yr_min] = current[cur_var]
            mo_year[mo_yr_tm] = current[lbls.tmval]
            upd = True
            if gb.DIAG_LEVEL & gb.WTHR30_ALL_TIME:
                gb.logging.info("mo_year: Updated %s: old: %.1f, new: %.1f" %
                                (mo_yr_tm, old_val, mo_year[mo_yr_min]))
        return upd

    #-----------------------------------------------------------
    # Check if current sensor value is greater than the existing month
    # (current year) high value
    #-----------------------------------------------------------
    def cmp_mo_year_max(self, cur_var, mo_yr_max, mo_yr_tm):

        global current
        global mo_year

        upd = False

        if round(current[cur_var], 1) > round(mo_year[mo_yr_max], 1):
            old_val = mo_year[mo_yr_max]
            mo_year[mo_yr_max] = current[cur_var]
            mo_year[mo_yr_tm] = current[lbls.tmval]
            upd = True
            if gb.DIAG_LEVEL & gb.WTHR30_MO_YEAR:
                gb.logging.info("mo_year: Updated %s: old: %.1f, new: %.1f" %
                                (mo_yr_tm, old_val, mo_year[mo_yr_max]))
        return upd

    #---------------------------------------------------------
    # Record updates for min/max for current month and current year.
    # Periodically send min/max data to database if updates occur
    #---------------------------------------------------------
    def update_mo_year_min_max(self, db_q_out, cur_time, mo_id, cur_mo_str):

        global mo_year
        global mo_year_updated
        global next_mo_year_write

        new_month = False

        if mo_year[lbls.cur_month] != cur_mo_str:
            self.reset_cur_mo_year(cur_mo_str)
            new_month = True

        local_mo_year_updated = \
            self.cmp_mo_year_min(lbls.tempF_D,
                                 lbls.tempF_D_min, lbls.tm_FD_min) | \
            self.cmp_mo_year_max(lbls.tempF_D,
                                 lbls.tempF_D_max, lbls.tm_FD_max) | \
            self.cmp_mo_year_min(lbls.humidity, lbls.humidity_min,
                                 lbls.tm_humid_min) | \
            self.cmp_mo_year_max(lbls.humidity, lbls.humidity_max,
                                 lbls.tm_humid_max) | \
            self.cmp_mo_year_min(lbls.press_sl_ft, lbls.press_mB_min,
                                 lbls.tm_mB_min) | \
            self.cmp_mo_year_max(lbls.press_sl_ft, lbls.press_mB_max,
                                 lbls.tm_mB_max)

        if local_mo_year_updated:
            if gb.DIAG_LEVEL & gb.WTHR30_DETAIL:
                gb.logging.info("update_mo_year_min_max: mo_year var updated")
            mo_year_updated = True

        if new_month or (mo_year_updated and cur_time > next_mo_year_write):
            self.send_mo_year_min_max_to_db(db_q_out, cur_mo_str)
            next_mo_year_write = cur_time + gb.timedelta(minutes=3)
            mo_year_updated = False

    #---------------------------------------------------------
    # Request prior 30-days min/max from DB on startup
    #---------------------------------------------------------
    def req_30day_min_max(self, db_q_out):
        dbInfo = []
        db_msgType = db.DB_REQ_30DAY_MIN_MAX
        dbInfo.append(db_msgType)
        if (gb.DIAG_LEVEL & gb.SEND_TO_DB):
            gb.logging.info("Sending %s(%d)" %
                     (db.get_db_msg_str(db_msgType),db_msgType))
        db_q_out.put(dbInfo)

    #---------------------------------------------------------
    # Initialize past 30-days min/max from DB data on startup
    #---------------------------------------------------------
    def rcv_30day_min_max(self, wthr_data, db_q_out):
        global cur_day

        if wthr_data[1] != 1:  # if DB_SUCCESS
            self.req_30day_min_max(db_q_out)
            return False

        # [0] msgType
        # [1] DB_SUCCESS
        last_30days[lbls.cur_date] = wthr_data[2]      # [2]  tmstamp
        last_30days[lbls.tempF_B_min] = wthr_data[3]   # [3]  minbmpf
        last_30days[lbls.tempF_B_max] = wthr_data[4]   # [4]  maxbmpf
        last_30days[lbls.tm_FB_min] = wthr_data[5]     # [5]  minbmpfts
        last_30days[lbls.tm_FB_max] = wthr_data[6]     # [6]  maxbmpfts
        last_30days[lbls.tempF_D_min] = wthr_data[7]   # [7]  mindhtf
        last_30days[lbls.tempF_D_max] = wthr_data[8]   # [8]  maxdhtf
        last_30days[lbls.tm_FD_min] = wthr_data[9]     # [9]  mindhtfts
        last_30days[lbls.tm_FD_max] = wthr_data[10]    # [10]  maxdhtfts
        last_30days[lbls.humidity_min] = wthr_data[11] # [11] minhumidity
        last_30days[lbls.humidity_max] = wthr_data[12] # [12] maxhumidity
        last_30days[lbls.tm_humid_min] = wthr_data[13] # [13] minhumidityts
        last_30days[lbls.tm_humid_max] = wthr_data[14] # [14] maxhumidityts
        last_30days[lbls.press_mB_min] = wthr_data[15] # [15] lowmB
        last_30days[lbls.press_mB_max] = wthr_data[16] # [16] highmB
        last_30days[lbls.tm_mB_min] = wthr_data[17]    # [17] lowmBts
        last_30days[lbls.tm_mB_max] = wthr_data[18]    # [18] highmBts

        if gb.DIAG_LEVEL & gb.WTHR_DAY_INIT or gb.DIAG_LEVEL & gb.WTHR30_30DAY:
            gb.logging.info("rcv_24hr_min_max: RECEIVED FROM DB")
            gb.logging.info("rcv_24hr_min_max: DHT tmn: %.1f tmx: %.1f, "
                        "HUM: hmn: %.1f hmx %.1f" %
                        (last_30days[lbls.tempF_D_min],
                         last_30days[lbls.tempF_D_max],
                         last_30days[lbls.humidity_min],
                         last_30days[lbls.humidity_max]))
        return True

    #---------------------------------------------------------
    # Send min/max readings for past 30 days to DB
    #---------------------------------------------------------
    def send_30day_min_max_to_db(self, db_q_out):

        db_msgType = db.DB_30DAY_MIN_MAX
        dbInfo = []
        dbInfo.append(db_msgType)

        dbInfo.append(gb.get_date_with_seconds(
                                str(last_30days[lbls.tm_FB_min])))
        dbInfo.append(last_30days[lbls.tempF_B_min])
        dbInfo.append(gb.get_date_with_seconds(
                                str(last_30days[lbls.tm_FB_max])))
        dbInfo.append(last_30days[lbls.tempF_B_max])
        dbInfo.append(gb.get_date_with_seconds(
                                str(last_30days[lbls.tm_FD_min])))
        dbInfo.append(last_30days[lbls.tempF_D_min])
        dbInfo.append(gb.get_date_with_seconds(
                                str(last_30days[lbls.tm_FD_max])))
        dbInfo.append(last_30days[lbls.tempF_D_max])
        dbInfo.append(gb.get_date_with_seconds(
                                str(last_30days[lbls.tm_mB_min])))
        dbInfo.append(last_30days[lbls.press_mB_min])
        dbInfo.append(gb.get_date_with_seconds(
                                str(last_30days[lbls.tm_mB_max])))
        dbInfo.append(last_30days[lbls.press_mB_max])
        dbInfo.append(gb.get_date_with_seconds(
                                str(last_30days[lbls.tm_humid_min])))
        dbInfo.append(last_30days[lbls.humidity_min])
        dbInfo.append(gb.get_date_with_seconds(
                                str(last_30days[lbls.tm_humid_max])))
        dbInfo.append(last_30days[lbls.humidity_max])

        if gb.DIAG_LEVEL & gb.WTHR30_30DAY:
            gb.logging.info("send_30day_min_max_to_db: SND 30DAY MIN MAX to DB")
            gb.logging.info("send_30day_min_max_to_db: "
                        "DHT tmn: %.1f tmx: %.1f, "
                        "HUM: hmn: %.1f hmx %.1f" %
                        (last_30days[lbls.tempF_D_min],
                         last_30days[lbls.tempF_D_max],
                         last_30days[lbls.humidity_min],
                         last_30days[lbls.humidity_max]))

        if (gb.DIAG_LEVEL & gb.SEND_TO_DB):
            gb.logging.info("Sending %s(%d)" %
                     (db.get_db_msg_str(db_msgType),db_msgType))
        db_q_out.put(dbInfo)

    #---------------------------------------------------------
    # Record updates for min/max reading for past 30 days.
    # Periodically send min/max data to database
    #---------------------------------------------------------
    def update_30day_min_max(self, db_q_out, cur_time, prior_30d):

        global last_30day_stat_updated
        global next_30day_write

        local_30day_stat_updated = \
            self.cmp_30d_min(lbls.tempF_B, lbls.tempF_B_min,
                            lbls.tm_FB_min, prior_30d) | \
            self.cmp_30d_max(lbls.tempF_B, lbls.tempF_B_max,
                            lbls.tm_FB_max, prior_30d) | \
            self.cmp_30d_min(lbls.tempF_D, lbls.tempF_D_min,
                            lbls.tm_FD_min, prior_30d) | \
            self.cmp_30d_max(lbls.tempF_D, lbls.tempF_D_max,
                            lbls.tm_FD_max, prior_30d) | \
            self.cmp_30d_min(lbls.press_mB, lbls.press_mB_min,
                            lbls.tm_mB_min, prior_30d) | \
            self.cmp_30d_max(lbls.press_mB, lbls.press_mB_max,
                            lbls.tm_mB_max, prior_30d) | \
            self.cmp_30d_min(lbls.press_sl_ft, lbls.press_sl_ft_min,
                            lbls.tm_ft_min, prior_30d) | \
            self.cmp_30d_max(lbls.press_sl_ft, lbls.press_sl_ft_max,
                            lbls.tm_ft_max, prior_30d) | \
            self.cmp_30d_min(lbls.variance, lbls.var_min,
                            lbls.tm_var_min, prior_30d) | \
            self.cmp_30d_max(lbls.variance, lbls.var_max,
                            lbls.tm_var_max, prior_30d) | \
            self.cmp_30d_min(lbls.humidity, lbls.humidity_min,
                            lbls.tm_humid_min, prior_30d) | \
            self.cmp_30d_max(lbls.humidity, lbls.humidity_max,
                            lbls.tm_humid_max, prior_30d)

        if local_30day_stat_updated:
            if gb.DIAG_LEVEL & gb.WTHR30_DETAIL:
                gb.logging.info("local_30day_stat_updated: "
                                "last_30days var updated")
            last_30day_stat_updated = True

        if (last_30day_stat_updated and cur_time > next_30day_write):
            self.send_30day_min_max_to_db(db_q_out)
            next_30day_write = cur_time + gb.timedelta(minutes=3)
            last_30day_stat_updated = False

    #---------------------------------------------------------
    # Send keep-alive (I am alive) message to DB
    #---------------------------------------------------------
    def send_wthr30_keep_alive(self, db_q_out):
        db_msgType = db.DB_WTHR30_ALIVE
        dbInfo = []
        dbInfo.append(db_msgType)

        if (gb.DIAG_LEVEL & gb.SEND_TO_DB):
            gb.logging.info("Sending %s(%d)" %
                     (db.get_db_msg_str(db_msgType),db_msgType))
        db_q_out.put(dbInfo)

    ####################################################################
    # Weather30 run function
    ####################################################################
    def run(self):

        global have_all_time_min_max_data
        global have_mo_year_min_max_data

        wthr_q_in = self.args[0]
        db_q_out = self.args[1]
        end_event = self.args[2]

        gb.logging.info("Running %s" % (self.name))

        cur_tempF = 0.0
        cur_humidity = 0.0
        cur_pressure_mB = 0.0

        have_weather_data = False
        have_30day_min_max_data = False

        alive_counter = 0

        cur_mo_id, cur_mo_str = gb.get_current_month()
        gb.logging.info("Current Month: %s(%d)" %
                        (cur_mo_str, cur_mo_id))

        self.req_30day_min_max(db_q_out)
        self.req_mo_year_min_max(db_q_out, cur_mo_id)
        self.req_all_time_min_max(db_q_out, cur_mo_id)

        while not end_event.isSet():
            #--------------------------------------
            # Check for incoming sensor messages
            #--------------------------------------
            tm_str = gb.get_date_with_seconds(gb.get_localdate_str())
            cur_mo_id, cur_mo_str = gb.get_current_month()

            while not wthr_q_in.empty():
                weather_data = wthr_q_in.get()
                wthr_msgType = weather_data[0]

                if gb.DIAG_LEVEL & gb.WTHR30_RCV:
                    gb.logging.debug("%s: Recvd: %s(%d)" %
                                    (tm_str,
                                     wthr30.get_wthr30_msg_str(wthr_msgType),
                                     wthr_msgType))

                if wthr_msgType == wthr30.WTHR30_SENSOR_DATA:
                    if gb.DIAG_LEVEL & gb.WTHR30_RCV:
                        gb.logging.info("%s: Received sensor data" % (tm_str))
                    self.rcv_sensor_data(weather_data)
                    have_weather_data = True

                elif wthr_msgType == wthr30.WTHR30_30DAY_MIN_MAX:
                    gb.logging.info("RECEIVED 30-DAY MIN/MAX DATA")
                    have_30day_min_max_data = \
                        self.rcv_30day_min_max(weather_data, db_q_out)

                elif wthr_msgType == wthr30.WTHR30_MO_YEAR_MIN_MAX:
                    gb.logging.info("RECEIVED MO_YEAR MIN/MAX DATA")
                    have_mo_year_min_max_data = \
                        self.rcv_mo_year_min_max(weather_data,
                                                 db_q_out, cur_mo_id)

                elif wthr_msgType == wthr30.WTHR30_ALL_TIME_MIN_MAX:
                    gb.logging.info("RECEIVED ALL-TIME MIN/MAX DATA")
                    have_all_time_min_max_data = \
                        self.rcv_all_time_min_max(weather_data,
                                                  db_q_out, cur_mo_id)

                elif wthr_msgType == wthr30.WTHR30_EXIT:
                    # Shutdown likely occurs before this message
                    # has a chance to get processed
                    gb.logging.info("Cleaning up before EXIT")

                else:
                    gb.logging.error("%s: Invalid sensor message type: %d" %
                                     (tm_str, wthr_msgType))
                    gb.logging.error(weather_data)

            # Start database writes only after all initialization is complete
            # Confirm that readings from sensors (have_weather_data)
            # have been received, and last_30days and all_time data have been
            # obtained from database (have_all_time_min_max_data and
            # have_30day_min_max_data) before any updates to the
            # database tables are allowed.  When the month changes,
            # the all time data needs to be updated for the current month,
            # so have_all_time_min_max_data is set to False at that
            # point also, and data for the new month is requested

            if not have_weather_data or not have_30day_min_max_data or \
               not have_mo_year_min_max_data or not have_all_time_min_max_data:
                gb.logging.info("%s: Weather30: Waiting for data..." % (tm_str))
                if not have_weather_data:
                    gb.logging.info("%s: have_weather_data: False" % (tm_str))
                if not have_30day_min_max_data:
                    gb.logging.info("%s: have_30day_min_max_data: False" %
                                    (tm_str))
                if not have_mo_year_min_max_data:
                    gb.logging.info("%s: have_mo_year_min_max_data: False" %
                                    (tm_str))
                if not have_all_time_min_max_data:
                    gb.logging.info("%s: have_all_time_min_max_data: False" %
                                    (tm_str))

                gb.time.sleep(SLEEP_TIME)
                continue

            cur_time, day_prior = self.get_times()

            self.update_30day_min_max(db_q_out, cur_time, day_prior)
            self.update_mo_year_min_max(db_q_out, cur_time,
                                        cur_mo_id, cur_mo_str)
            self.update_all_time_min_max(db_q_out, cur_time, cur_mo_id)

            if alive_counter >= 3:
                self.send_wthr30_keep_alive(db_q_out)
                alive_counter = 0
            alive_counter += 1

            gb.time.sleep(SLEEP_TIME)

        gb.logging.info("Exiting %s" % (self.name))
