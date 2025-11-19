import gb

import db
import co
import wv
import rg

CO_SLEEP = 1

REQ_SZ = 50
REQS_TIME = [0.0] * REQ_SZ    # epoch time
REQS_AVG1 = [-1.0] * REQ_SZ   # mph
REQS_SDEV1 = [-1.0] * REQ_SZ  # mph
REQS_AVG5 = [-1.0] * REQ_SZ   # mph
REQS_SDEV5 = [-1.0] * REQ_SZ  # mph
REQS_MPH = [0.0] * REQ_SZ     # windspeed in mph (not averaged)

REQS_RVOLT = [-1.0] * REQ_SZ  # resistor windvane voltage
REQS_RVALUE = [0] * REQ_SZ    # resistor windvane ADC digital value
REQS_RDIR = [0] * REQ_SZ      # resistor windvane magnetic direction -- 1-8
REQS_HVOLT = [-1.0] * REQ_SZ  # hall sensor windvane voltage
REQS_HVALUE = [0] * REQ_SZ    # hall sensor windvane ADC digital value
REQS_HDEGREES = [0.0] * REQ_SZ # Hall sensor windvance true degrees
REQS_HDIR = [""] * REQ_SZ     # Hall sensor windvane true direction str
REQS_MDIR = [""] * REQ_SZ     # Hall sensor windvane magnetic direction str

REQS_RAIN = [-1.0] * REQ_SZ   # inches
REQS_DUMP = [0] * REQ_SZ      # count of bucket dumps

#######################################################################
#
# Coordinator Thread
#
#######################################################################
class CoordinatorThread(gb.threading.Thread):

    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        gb.threading.Thread.__init__(self, group=group, target=target, name=name)
        gb.logging.info("Setting up Coordinator thread")
        self.args = args
        self.kwargs = kwargs
        self.name = name

    #---------------------------------------------------------
    # Request wind direction and rainfall from windvane
    # and rain gauge processes
    #---------------------------------------------------------
    def request_wind_dir_rain(self, wv_q_out, rg_q_out, e_tm, req_id):
        msg=[]
        msgType = wv.WV_GET_DIRECTION
        msg.append(msgType)
        msg.append(e_tm)
        msg.append(req_id)
        if (gb.DIAG_LEVEL & gb.WIND_DIR_MSG):
            gb.logging.info("Sending %s(%d)" %
                            (wv.get_wv_msg_str(msgType), msgType))
        wv_q_out.put(msg)

        msg=[]
        msgType = rg.RG_GET_RAINFALL
        msg.append(msgType)
        msg.append(e_tm)
        msg.append(req_id)
        if (gb.DIAG_LEVEL & gb.RAIN_MSG):
            gb.logging.info("Sending %s(%d)" %
                            (rg.get_rg_msg_str(msgType), msgType))
        rg_q_out.put(msg)

    #---------------------------------------------------------
    # Process wind direction information from windvane thread
    #---------------------------------------------------------
    def process_winddir(self, msg):

        global REQS_RVOLT
        global REQS_RVALUE
        global REQS_RDIR
        global REQS_HVOLT
        global REQS_HVALUE
        global REQS_HDEGREES
        global REQS_HDIR
        global REQS_MDIR

        msgType = msg[0]
        if (gb.DIAG_LEVEL & gb.WIND_DIR_MSG or
            gb.DIAG_LEVEL & gb.WIND_DIR_DETAIL):
            gb.logging.info("Processing %s(%d)" %
                            (co.get_co_msg_str(msgType), msgType))
        epoch_tm = msg[1]
        req_id = msg[2]
        resistor_volts = msg[3]
        resistor_value = msg[4]
        resistor_winddir_int = msg[5] # magnetic dir str (8-point)
        hall_volts = msg[6]
        hall_value = msg[7]
        hall_winddegrees = msg[8]     # true degrees
        hall_winddir_str = msg[9]     # true dir str (16-point)
        hall_mag_dir_str = msg[10]    # magnetic dir str (8-point)

        REQS_RVOLT[req_id] = resistor_volts
        REQS_RVALUE[req_id] = resistor_value
        REQS_RDIR[req_id] = resistor_winddir_int

        REQS_HVOLT[req_id] = hall_volts
        REQS_HVALUE[req_id] = hall_value
        REQS_HDEGREES[req_id] = hall_winddegrees   # true degrees
        REQS_HDIR[req_id] = hall_winddir_str       # true dir str
        REQS_MDIR[req_id] = hall_mag_dir_str       # magnetic dir str

    #---------------------------------------------------------
    # Process rain fall information from rain gauge process
    #---------------------------------------------------------
    def process_rainfall(self, msg):

        global REQS_DUMP
        global REQS_RAIN

        msgType = msg[0]
        e_tm = msg[1]
        req_id = msg[2]
        dump_cnt = msg[3] # number of times bucket dump occurred
        rainfall = msg[4]

        if (gb.DIAG_LEVEL & gb.RAIN_MSG):
            gb.logging.info("Processing %s(%d): rainfall %0.2f" %
                            (co.get_co_msg_str(msgType), msgType, rainfall))

        REQS_DUMP[req_id] = dump_cnt
        REQS_RAIN[req_id] = rainfall

    def send_gust_to_db(self, db_q, tm, avg5, mph, interval):
        msg = []
        msgType = db.DB_GUST
        msg.append(msgType)
        msg.append(tm)
        msg.append(avg5)
        msg.append(mph)
        msg.append(interval)
        if (gb.DIAG_LEVEL & gb.DB_MSG):
            gb.logging.info("Sending %s(%d)" %
                            (db.get_db_msg_str(msgType), msgType))
        db_q.put(msg)

    def process_gust(self, db_q, msg):
        msgType        = msg[0]
        gust_tm        = msg[1]
        wind_avg       = msg[2]
        gust_mph       = msg[3]
        gust_intervals = msg[4]
        if (gb.DIAG_LEVEL & gb.GUSTS_MSG):
            gb.logging.info("Processing %s(%d)" %
                                (co.get_co_msg_str(msgType), msgType))
            gb.logging.info("Wind Avg: %0.1f mph; GUST %s: %0.1f mph %d intervals" %
                            (wind_avg, gust_tm, gust_mph, gust_intervals))
        self.send_gust_to_db(db_q, gust_tm, wind_avg, gust_mph, gust_intervals)


    def send_reading_to_db(self, db_q, tm_str, wavg1, wsdev1,
                           wavg5, wsdev5, windspeed,
                           w_rvolt, w_rval, wrdir, wrdir_str,
                           w_hvolt, w_hval, wdegrees, w_hdir_str, w_mdir_str,
                           rdump_cnt, rtally):

        msg = []
        msgType = db.DB_READING
        msg.append(msgType)
        msg.append(tm_str)

        msg.append(wavg1)
        msg.append(wsdev1)
        msg.append(wavg5)
        msg.append(wsdev5)
        msg.append(windspeed)

        msg.append(w_rvolt)
        msg.append(w_rval)
        msg.append(wrdir)
        msg.append(wrdir_str)

        msg.append(w_hvolt)
        msg.append(w_hval)
        msg.append(wdegrees)
        msg.append(w_hdir_str)
        msg.append(w_mdir_str)

        msg.append(rdump_cnt)
        msg.append(rtally)

        if (gb.DIAG_LEVEL & gb.DB_MSG):
            gb.logging.info("Sending %s(%d)" %
                            (db.get_db_msg_str(msgType), msgType))
        db_q.put(msg)

    def send_db_test_msg(self, db_q):
        msg = []
        msgType = db.DB_TEST
        msg.append(msgType)
        gb.logging.info("Sending %s(%d)" %
                        (db.get_db_msg_str(msgType), msgType))
        db_q.put(msg)

    def process_windmax(self, db_q, msgType, msg):
        err = False
        if (msgType == co.CO_MP_MAX_1_HOUR):
            msg[0] = db.DB_MAX_1_HOUR
        elif (msgType == co.CO_MP_MAX_TODAY):
            msg[0] = db.DB_MAX_TODAY
        else:
            gb.logging.error("Invalid CO message type: %d" % (msgType))
            err = True

        if (err == False):
            if (gb.DIAG_LEVEL & gb.DB_MSG):
                gb.logging.info("Sending %s(%d)" %
                                (db.get_db_msg_str(msg[0]), msg[0]))
            db_q.put(msg)

    #---------------------------------------------------------
    # Send keep-alive (I am alive) message to DB
    #---------------------------------------------------------
    def relay_keep_alive(self, msgType, msg, db_q_out):

        if (gb.DIAG_LEVEL & gb.SEND_TO_DB):
            gb.logging.info("Sending %s(%d)" %
                     (db.get_db_msg_str(msgType),msgType))
        db_q_out.put(msg)

    #---------------------------------------------------------
    # Send keep-alive (I am alive) message to DB
    #---------------------------------------------------------
    def send_coord_keep_alive(self, db_q_out):
        db_msgType = db.DB_COORD_ALIVE
        dbInfo = []
        dbInfo.append(db_msgType)

        if (gb.DIAG_LEVEL & gb.SEND_TO_DB):
            gb.logging.info("Sending %s(%d)" %
                     (db.get_db_msg_str(db_msgType),db_msgType))
        db_q_out.put(dbInfo)

    #############################################################
    # Database run function
    #############################################################
    def run(self):

        global REQ_SZ
        global REQS_TIME
        global REQS_AVG1
        global REQS_SDEV1
        global REQS_AVG5
        global REQS_SDEV5
        global REQS_MPH
        global REQS_RVOLT
        global REQS_RVALUE
        global REQS_RDIR
        global REQS_HVOLT
        global REQS_HVALUE
        global REQS_HDEGREES
        global REQS_HDIR
        global REQS_MDIR
        global REQS_RAIN
        global REQS_DUMP

        co_q_in = self.args[0]
        co_mp_q_in = self.args[1]
        wv_q_out = self.args[2]
        rg_q_out = self.args[3]
        db_q_out = self.args[4]
        end_event = self.args[5]

        gb.logging.info("Running %s" % (self.name))
        gb.logging.debug(self.args)

        avg_windspeed = 0.0
        wind_rdir = wv.NORTH_INT
        rain = 0.0
        req_id = 0

        old_wind_avg = -1.0
        old_windspeed = -1.0
        old_wind_rdir = wv.INVALID
        old_rain_tally = -1.0
        old_dump_cnt = -1

        alive_counter = 0
        
        ###################################################
        # Coordiantor main loop
        ###################################################
        while not end_event.isSet():

            msgType = ""
            while not co_q_in.empty() or not co_mp_q_in.empty():

                #-----------------------------
                # First check for a message from a thread
                # (Thread vs. process order is arbitrary)
                #-----------------------------
                if (not co_q_in.empty()):
                    msg = co_q_in.get()
                    msgType = msg[0]
                    if (gb.DIAG_LEVEL & gb.COOR_MSG and
                        gb.DIAG_LEVEL & gb.COOR_DETAIL):
                        gb.logging.info("%s:  Received %s(%d)" %
                            (self.name, co.get_co_msg_str(msgType), msgType))

                    if (msgType == co.CO_EXIT):
                        gb.logging.info("%s: Cleanup prior to exit" %
                                        (self.name))

                    elif (msgType == co.CO_WIND_DIR):
                        if (gb.DIAG_LEVEL & gb.WIND_DIR_MSG):
                            gb.logging.info("Processing %s(%d)" %
                                     (co.get_co_msg_str(msgType), msgType))
                        self.process_winddir(msg)

                    elif (msgType == db.DB_WV_ALIVE):
                        self.relay_keep_alive(msgType, msg, db_q_out)

                    else:
                        gb.logging.error("Invalid CO message type: %d" %
                                         (msgType))
                        gb.logging.error(msg)

                #-----------------------------
                # Then check for messages from other processes
                #-----------------------------
                if (not co_mp_q_in.empty()):
                    msg = co_mp_q_in.get()
                    msgType = msg[0]
                    if (gb.DIAG_LEVEL & gb.WIND_AVG_MSG and
                        gb.DIAG_LEVEL & gb.WIND_AVG_DETAIL):
                        gb.logging.info("%s:  Received MP %s(%d)" %
                            (self.name, co.get_co_msg_str(msgType), msgType))

                    if (msgType == co.CO_MP_SHORT_WINDSPEED):
                        if (gb.DIAG_LEVEL & gb.WIND_AVG_MSG):
                            gb.logging.info("Received MP %s(%d)" %
                                (co.get_co_msg_str(msgType), msgType))
                        req_id = req_id + 1
                        if (req_id >= REQ_SZ):
                            req_id = 0
                        epoch_time = gb.time.time()
                        avg1_mph = msg[1]
                        sdev1_mph = msg[2]
                        avg5_mph = msg[3]
                        sdev5_mph = msg[4]
                        windspeed = msg[5]
                        REQS_AVG1[req_id] = avg1_mph
                        REQS_SDEV1[req_id] = sdev1_mph
                        REQS_AVG5[req_id] = avg5_mph
                        REQS_SDEV5[req_id] = sdev5_mph
                        REQS_TIME[req_id] = epoch_time
                        REQS_RDIR[req_id] = 0
                        REQS_HDEGREES[req_id] = float(0.0)
                        REQS_RAIN[req_id] = -1.0
                        REQS_DUMP[req_id] = -1
                        REQS_MPH[req_id] = windspeed
                        self.request_wind_dir_rain(wv_q_out, rg_q_out,
                                                   epoch_time, req_id)

                    elif (msgType == co.CO_MP_LONG_WINDSPEED):
                        if (gb.DIAG_LEVEL & gb.WIND_AVG_MSG):
                            gb.logging.info("Received %s(%d)" %
                                (co.get_co_msg_str(msgType), msgType))

                    elif (msgType == co.CO_MP_RAINFALL):
                        if (gb.DIAG_LEVEL & gb.RAIN_MSG):
                            gb.logging.info("Received %s(%d)" %
                                (co.get_co_msg_str(msgType), msgType))
                        self.process_rainfall(msg)

                    elif (msgType == co.CO_MP_GUST):
                        if (gb.DIAG_LEVEL & gb.GUSTS_MSG):
                            gb.logging.info("Received %s(%d)" %
                                (co.get_co_msg_str(msgType), msgType))
                        self.process_gust(db_q_out, msg)

                    elif (msgType == co.CO_MP_MAX_1_HOUR):
                        if (gb.DIAG_LEVEL & gb.WIND_MAX):
                            gb.logging.info("Processing %s(%d)" %
                                     (co.get_co_msg_str(msgType), msgType))
                        self.process_windmax(db_q_out, msgType, msg)

                    elif (msgType == co.CO_MP_MAX_TODAY):
                        if (gb.DIAG_LEVEL & gb.WIND_MAX):
                            gb.logging.info("Processing %s(%d)" %
                                     (co.get_co_msg_str(msgType), msgType))
                        self.process_windmax(db_q_out, msgType, msg)

                    elif (msgType == db.DB_RG_ALIVE) or \
                         (msgType == db.DB_AN_ALIVE):
                        self.relay_keep_alive(msgType, msg, db_q_out)

                    else:
                        gb.logging.error("Invalid CO MP message type: %d" %
                            (msgType))
                        gb.logging.error(msg)

                gb.time.sleep(0.5)

            # Once all thread andd process messages have been handled,
            # check for any completed requests.  The requests have an
            # ID and timestamp associated with them, and gather up the
            # wind speed, wind vane, and rain gauge information from
            # approximately the same timeframe

            if (msgType != co.CO_EXIT):

                #self.send_db_test_msg(db_q_out)

                #-----------------------------
                # Count uncompleted weather requests
                #-----------------------------
                inprogress = 0
                for ix in range(REQ_SZ):
                    if (REQS_AVG1[ix] != -1.0):
                        inprogress = inprogress + 1 

                #-----------------------------
                # Check for any completed weather requests where the
                # data differs from the last data written to the DB
                #-----------------------------
                for ix in range(REQ_SZ):
                    if ((REQS_AVG1[ix] != -1.0) and
                        (REQS_AVG5[ix] != -1.0) and
                        (REQS_RDIR[ix] != wv.INVALID) and
                        (REQS_RAIN[ix] != -1.0)):

                        wind_avg1 = REQS_AVG1[ix]
                        wind_sdev1 = REQS_SDEV1[ix]

                        wind_avg5 = REQS_AVG5[ix]
                        wind_sdev5 = REQS_SDEV5[ix]

                        rain_tally = REQS_RAIN[ix]
                        #if (rain_tally != 0.0):
                        #    rain_tally = rain_tally + 0.005
                        rain_dump_cnt = REQS_DUMP[ix]

                        wind_rvolt = REQS_RVOLT[ix]
                        wind_rval = REQS_RVALUE[ix]
                        wind_rdir = REQS_RDIR[ix]
                        wind_rdir_str = wv.wind_dir_int_to_str(wind_rdir)

                        wind_hvolt = REQS_HVOLT[ix]
                        wind_hval = REQS_HVALUE[ix]
                        wind_degrees = REQS_HDEGREES[ix]
                        wind_hdir_str = REQS_HDIR[ix]
                        wind_mdir_str = REQS_MDIR[ix]

                        date_seconds = str(
                                    gb.datetime.fromtimestamp(REQS_TIME[ix]))
                        date_seconds = gb.get_date_with_seconds(date_seconds)

                        #-----------------------------
                        # Store values in DB only if one or more changed
                        # from prior readings
                        #-----------------------------
                        if ((old_wind_avg != wind_avg1) or
                            (old_windspeed != windspeed) or
                            (old_rain_tally != rain_tally) or
                            (REQS_RDIR[ix] != old_wind_rdir) or
                            (rain_dump_cnt != old_dump_cnt)):

                            gb.logging.debug(
                                "OLD: %0.1f MPH, Dir %d(%d), %0.2f in" %
                                (old_wind_avg, old_wind_rdir, REQS_RDIR[ix],
                                 old_rain_tally))
                            if (gb.DIAG_LEVEL & gb.COOR):
                                gb.logging.info(
                                    "%d: %s: %0.1f MPH, %s, deg: %.1f; %0.2f in, cnt %d" %
                                    (ix, date_seconds,
                                     wind_avg1,
                                     wind_rdir_str,
                                     wind_degrees,
                                     rain_tally, inprogress))

                            self.send_reading_to_db(db_q_out, date_seconds,
                                                    wind_avg1, wind_sdev1,
                                                    wind_avg5, wind_sdev5,
                                                    windspeed,
                                                    wind_rvolt, wind_rval,
                                                    wind_rdir, wind_rdir_str,
                                                    wind_hvolt, wind_hval, 
                                                    wind_degrees, wind_hdir_str,
                                                    wind_mdir_str,
                                                    rain_dump_cnt, rain_tally)

                            old_wind_avg = wind_avg1
                            old_windspeed = windspeed
                            old_wind_rdir = REQS_RDIR[ix]
                            old_rain_tally = rain_tally
                            old_dump_cnt = rain_dump_cnt

                        REQS_TIME[ix] = 0.0

                        REQS_AVG1[ix] = -1.0
                        REQS_SDEV1[ix] = -1.0
                        REQS_AVG5[ix] = -1.0
                        REQS_SDEV5[ix] = -1.0
                        REQS_MPH[ix] = -1.0

                        REQS_RVOLT[ix] = -1.0
                        REQS_RVALUE[ix] = -1
                        REQS_RDIR[ix] = wv.INVALID
                        REQS_HVOLT[ix] = -1.0
                        REQS_HVALUE[ix] = -1
                        REQS_HDEGREES[ix] = float(-1.0)
                        REQS_HDIR[ix] = ""
                        REQS_MDIR[ix] = ""

                        REQS_RAIN[ix] = -1.0
                        REQS_DUMP[ix] = -1

                if alive_counter >= 30:
                    self.send_coord_keep_alive(db_q_out)
                    alive_counter = 0
                alive_counter += 1

                gb.time.sleep(CO_SLEEP)

        gb.logging.info("Exiting %s" % (self.name))
