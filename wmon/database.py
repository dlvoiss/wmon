import gb
import db
import fan
import wthr
import wthr30
import wavg
import config

import mysql.connector as mariadb
import sys
from decimal import Decimal

#------------------------------
# Database Tables
#------------------------------
# alltimedata           All Time Min/Max
# cpulatest             Track CPU temperature and fan state
# current_stats         Sunrise/sunset today, latest wind, rain,
#                       Wind dir readings
# readings              Ongoing history of readings from sensors
# currentreadings       Current (latest) readings from sensors 
#                       plus 24-hr min/max readings and timestamps
# readingsToday         Current day min/Max readings and timestamps
# readings30            30-day min/max readings and timestamps
# historycputemp        CPU temperature and fan state
# monthavg              Averages by month
# monthdata             Month-to-Month Min/Max for current year
# rmt_readings          No longer needed
# sun                   Sunrise/Sunset times
# windrain              ongoing history of wind, rain and wind direction

PRIOR_CPU_TEMPC = gb.PRIOR_TEMP_DFLT

DB_SLEEP = 5
DB_SUCCESS = 1

# DST_START/DST_END: Year is set to current year when DST variables accessed
DST_START = gb.datetime(2025, 3, 9, 2, 0, 0)
DST_END =   gb.datetime(2025, 11, 2, 2, 0, 0)

#######################################################################
#
# Database Thread
#
#######################################################################
class DatabaseThread(gb.threading.Thread):

    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        gb.threading.Thread.__init__(self, group=group, target=target, name=name)
        gb.logging.info("Setting up Database thread")
        self.args = args
        self.kwargs = kwargs
        self.name = name
        self.db_conn = 0
        self.db_cursor = 0

    #------------------------------------
    def add_start_record(self):

        tm_str = gb.get_date_with_seconds(gb.get_localdate_str())

        db_id = 1

        try:
            add_start = ("REPLACE INTO windrain "
                         "(recordType, tmstamp, dbid) "
                         "VALUES (%s, %s, %s)")
            data_add = ('START', tm_str, db_id)

            self.db_cursor.execute(add_start, data_add)
            self.db_cursor.execute("COMMIT")

        except mariadb.Error as e:
            gb.logging.error("MariaDB ERROR %d: %s" % (db_id, e))

        gb.logging.info("%s: Added START record to windrain table" %(tm_str))

    #------------------------------------
    def add_stop_record(self):

        tm_str = gb.get_date_with_seconds(gb.get_localdate_str())

        db_id = 2
        try:
            add_stop = ("REPLACE INTO windrain "
                         "(recordType, tmstamp, dbid) "
                         "VALUES (%s, %s, %s)")
            data_add = ('STOP', tm_str, db_id)

            self.db_cursor.execute(add_stop, data_add)
            self.db_cursor.execute("COMMIT")

        except mariadb.Error as e:
            gb.logging.error("MariaDB ERROR %d: %s" % (db_id, e))

        gb.logging.info("%s: Added STOP record to windrain table" % (tm_str))

    #------------------------------------
    # Request min/max values for today
    #------------------------------------
    def db_req_today_min_max(self, wthr_q_out):
        db_error = DB_SUCCESS;

        db_id = 3
        err_resp = -db_id

        tm_str = gb.get_date_with_seconds(gb.get_localdate_str())

        sql_select = 'SELECT * FROM readingsToday WHERE id=1'
        try:
            select = self.db_cursor.execute(sql_select)
            select_data = self.db_cursor.fetchone()

            if (gb.DIAG_LEVEL & gb.WTHR_DAY_INIT):
                print("\nSELECT resp: ", select_data, "\n")

        except mariadb.Error as e:
            gb.logging.error("MariaDB ERROR %d: %s" % (db_id, e))
            db_error = err_resp

        wthr_info = []
        wthr_msgType = wthr.WTHR_TODAY_MIN_MAX
        wthr_info.append(wthr_msgType)
        wthr_info.append(db_error)

        if (db_error == DB_SUCCESS):

            #elements_in_select_data = len(select_data)
            #gb.logging.info("elements_in_select_data: %d" %
            #                    (elements_in_select_data))
            #for fld in range(elements_in_select_data):
            #    print(fld, select_data[fld])

            wthr_info.append(select_data[1])  # tmstamp
            wthr_info.append(select_data[2])  # minTodaybmpf
            wthr_info.append(select_data[3])  # maxTodaybmpf
            wthr_info.append(select_data[4])  # minTodaybmpfts
            wthr_info.append(select_data[5])  # maxTodaybmpfts
            wthr_info.append(select_data[6])  # minTodaydhtf
            wthr_info.append(select_data[7])  # maxTodaydhtf
            wthr_info.append(select_data[8])  # minTodaydhtfts
            wthr_info.append(select_data[9])  # maxTodaydhtfts
            wthr_info.append(select_data[10]) # minTodayhumidity
            wthr_info.append(select_data[11]) # maxTodayhumidity
            wthr_info.append(select_data[12]) # minTodayhumts
            wthr_info.append(select_data[13]) # maxTodayhumts
            wthr_info.append(select_data[14]) # lowTodaymB
            wthr_info.append(select_data[15]) # highTodaymB
            wthr_info.append(select_data[16]) # lowTodaymBts
            wthr_info.append(select_data[17]) # highTodaymBts

            if gb.DIAG_LEVEL & gb.WTHR_DAY_INIT:
                gb.logging.info("db_req_today_min_max: "
                                "GET TODAY MIN MAX from DB")
                gb.logging.info("db_req_today_min_max: "
                        "BME tmn: %.1f tmx: %.1f, "
                        "DHT tmn: %.1f tmx: %.1f" %
                        (select_data[2], select_data[3],
                         select_data[6], select_data[7]))

        if (gb.DIAG_LEVEL & gb.DB_SEND_TO_WTHR):
            gb.logging.info("%s: Sending %s(%d)" %
                     (tm_str, wthr.get_wthr_msg_str(wthr_msgType),wthr_msgType))
        wthr_q_out.put(wthr_info)

    #------------------------------------
    # Updated min/max values for today
    #------------------------------------
    def db_update_today_min_max(self, db_data):

        minTodaybmpts    = db_data[1]
        minTodaybmpf     = db_data[2]
        maxTodaybmpts    = db_data[3]
        maxTodaybmpf     = db_data[4]

        minTodaydhtts    = db_data[5]
        minTodaydhtf     = db_data[6]
        maxTodaydhtts    = db_data[7]
        maxTodaydhtf     = db_data[8]

        lowTodaymbts     = db_data[9]
        lowTodaymB       = db_data[10]
        highTodaymbts    = db_data[11]
        highTodaymB      = db_data[12]

        minTodayhumts    = db_data[13]
        minTodayhumidity = db_data[14]
        maxTodayhumts    = db_data[15]
        maxTodayhumidity = db_data[16]

        #gb.logging.info("maxTodaydhtf: %.1f, "
        #                "minTodayhumts %s, minTodayhumidity: %.1f, " %
        #                (maxTodaydhtf, str(minTodayhumts), minTodayhumidity))

        if gb.DIAG_LEVEL & gb.WTHR_DAY_INIT:
            gb.logging.info("db_update_today_min_max: "
                        "DHT tmn: %.1f tmx: %.1f, "
                        "HUM: hmn: %.1f hmx %.1f" %
                        (minTodaydhtf, maxTodaydhtf, minTodayhumidity, maxTodayhumidity))

        db_id = 4
        try:
            if gb.DIAG_LEVEL & gb.DB_SENSOR_DATA:
                tm_str = gb.get_date_with_seconds(gb.get_localdate_str())

            day_min_max = ("REPLACE INTO readingsToday "
                           "(id, minTodaybmpts, minTodaybmpf, "
                           "maxTodaybmpts, maxTodaybmpf, "
                           "minTodaydhtts, minTodaydhtf, "
                           "maxTodaydhtts, maxTodaydhtf, "
                           "lowTodaymbts, lowTodaymB, "
                           "highTodaymbts, highTodaymB, "
                           "minTodayhumts, minTodayhumidity, "
                           "maxTodayhumts, maxTodayhumidity) "
                           "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")

            data_add = ('1', minTodaybmpts, minTodaybmpf, maxTodaybmpts, maxTodaybmpf, minTodaydhtts, minTodaydhtf, maxTodaydhtts, maxTodaydhtf, lowTodaymbts, lowTodaymB, highTodaymbts, highTodaymB, minTodayhumts, minTodayhumidity, maxTodayhumts, maxTodayhumidity)

            if gb.DIAG_LEVEL & gb.DB_DETAIL:
                tm_str = gb.get_date_with_seconds(gb.get_localdate_str())
                gb.logging.info("%s: REPLACE INTO readingsToday; db_id: %d" %
                                (tm_str, db_id))
            self.db_cursor.execute(day_min_max, data_add)
            self.db_cursor.execute("COMMIT")

        except mariadb.Error as e:
            gb.logging.error("MariaDB ERROR %d: %s" % (db_id, e))

    #------------------------------------
    # Request min/max values for prior 24 hours
    #------------------------------------
    def db_req_24hr_min_max(self, wthr_q_out):

        db_error = DB_SUCCESS;

        db_id = 5
        err_resp = -db_id

        tm_str = gb.get_date_with_seconds(gb.get_localdate_str())

        sql_select = 'SELECT * FROM currentreadings WHERE id=1'
        try:
            select = self.db_cursor.execute(sql_select)
            select_data = self.db_cursor.fetchone()

            if (gb.DIAG_LEVEL & gb.WTHR_DAY_INIT):
                print("\nSELECT resp: ", select_data, "\n")

        except mariadb.Error as e:
            gb.logging.error("MariaDB ERROR %d: %s" % (db_id, e))
            db_error = err_resp

        wthr_info = []
        wthr_msgType = wthr.WTHR_24HR_MIN_MAX
        wthr_info.append(wthr_msgType)
        wthr_info.append(db_error)

        if (db_error == DB_SUCCESS):

            #elements_in_select_data = len(select_data)
            #gb.logging.info("elements_in_select_data: %d" %
            #                    (elements_in_select_data))
            #for fld in range(elements_in_select_data):
            #    print(fld, select_data[fld])

            wthr_info.append(select_data[1])  # tmstamp
            wthr_info.append(select_data[3])  # minbmpf
            wthr_info.append(select_data[4])  # maxbmpf
            wthr_info.append(select_data[5])  # minbmpfts
            wthr_info.append(select_data[6])  # maxbmpfts
            wthr_info.append(select_data[8])  # mindhtf
            wthr_info.append(select_data[9])  # maxdhtf
            wthr_info.append(select_data[10]) # mindhtfts
            wthr_info.append(select_data[11]) # maxdhtfts
            wthr_info.append(select_data[13]) # minhumidity
            wthr_info.append(select_data[14]) # maxhumidity
            wthr_info.append(select_data[15]) # minhumidityts
            wthr_info.append(select_data[16]) # maxhumidityts
            wthr_info.append(select_data[18]) # lowmB
            wthr_info.append(select_data[19]) # highmB
            wthr_info.append(select_data[20]) # lowmBts
            wthr_info.append(select_data[21]) # highmBts

            if gb.DIAG_LEVEL & gb.WTHR_DAY_INIT:
                gb.logging.info("db_req_24hr_min_max: "
                                "GET PRIOR 24HR MIN MAX from DB")
                gb.logging.info("db_req_24hr_min_max: "
                        "BME tmn: %.1f tmx: %.1f, "
                        "DHT tmn: %.1f tmx: %.1f" %
                        (select_data[3], select_data[4],
                         select_data[8], select_data[9]))

        if (gb.DIAG_LEVEL & gb.DB_SEND_TO_WTHR):
            gb.logging.info("%s: Sending %s(%d)" %
                     (tm_str, wthr.get_wthr_msg_str(wthr_msgType),wthr_msgType))
        wthr_q_out.put(wthr_info)

    #------------------------------------
    # Update min/max values for current day
    #------------------------------------
    def db_update_24hr_min_max(self, db_data):

        tempbmpf = db_data[1]
        minbmpts = db_data[2]
        minbmpf = db_data[3]
        maxbmpts = db_data[4]
        maxbmpf = db_data[5]

        tempdhtf = db_data[6]
        mindhtts = db_data[7]
        mindhtf = db_data[8]
        maxdhtts = db_data[9]
        maxdhtf = db_data[10]

        baromB = db_data[11]
        lowmbts = db_data[12]
        lowmB = db_data[13]
        highmbts = db_data[14]
        highmB = db_data[15]

        humidity = db_data[16]
        minhumts = db_data[17]
        minhumidity = db_data[18]
        maxhumts = db_data[19]
        maxhumidity = db_data[20]

        if gb.DIAG_LEVEL & gb.WTHR_DAY_INIT:
            gb.logging.info("db_update_24hr_min_max: "
                        "DHT tmn: %.1f tmx: %.1f, "
                        "HUM: hmn: %.1f hmx %.1f" %
                        (mindhtf, maxdhtf, minhumidity, maxhumidity))

        db_id = 6
        id = 1
        try:
            tm_str = gb.get_date_with_seconds(gb.get_localdate_str())
            if gb.DIAG_LEVEL & gb.DB_DETAIL:
                gb.logging.info("%s: UPDATE currentReadings 24-hr min/max; "
                                "db_id: %d" %
                                (tm_str, db_id))
            self.db_cursor.execute("""UPDATE currentreadings SET tmstamp=%s, minbmpts=%s, minbmpf=%s, maxbmpts=%s, maxbmpf=%s, mindhtts=%s, mindhtf=%s, maxdhtts=%s, maxdhtf=%s, lowmbts=%s, lowmB=%s, highmbts=%s, highmB=%s, minhumts=%s, minhumidity=%s, maxhumts=%s, maxhumidity=%s WHERE id=%s""", (tm_str, minbmpts, minbmpf, maxbmpts, maxbmpf, mindhtts, mindhtf, maxdhtts, maxdhtf, lowmbts, lowmB, highmbts, highmB, minhumts, minhumidity, maxhumts, maxhumidity, id))
            self.db_cursor.execute("COMMIT")

        except mariadb.Error as e:
            gb.logging.error("MariaDB ERROR %d: %s" % (db_id, e))

    #------------------------------------
    # Update data from sensors
    #------------------------------------
    def db_update_local(self, db_data):
        gb.logging.debug("db_update_local")
        #print(db_data)
        tm_str = db_data[1]
        pressure_hPa = db_data[2]
        pressure_inHg = db_data[3]
        pressure_mmHg = db_data[4]                # not stored in DB
        pressure_psi = db_data[5]                 # not stored in DB
        pressure_adjusted_sea_level = db_data[6]  # not stored in DB
        columbia_dr_variance = db_data[7]
        bmp_temp_f = db_data[8]
        bmp_temp_c = db_data[9]
        dht_temp_f = db_data[10]
        dht_temp_c = db_data[11]
        dht_humidity = db_data[12]
        temp_combined = db_data[13]

        db_id = 7
        try:
            #------------------------------------------------
            # Update readings table with latest sensor info
            #------------------------------------------------
            add_local_weather = ("REPLACE INTO readings "
                                 "(recordType, tmstamp, baromB, baroinHg, "
                                 "baroVariance, tempbmpf, tempbmpc, humidity, "
                                 "tempdhtc, tempdhtf, tempCombined) "
                                 "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
            data_add = ('LOCAL', tm_str, pressure_hPa, pressure_inHg, columbia_dr_variance, bmp_temp_f, bmp_temp_c, dht_humidity, dht_temp_c, dht_temp_f, temp_combined)

            if gb.DIAG_LEVEL & gb.DB_DETAIL:
                gb.logging.info("%s: REPLACE INTO readings; db_id: %d" %
                                (tm_str, db_id))
            self.db_cursor.execute(add_local_weather, data_add)
            self.db_cursor.execute("COMMIT")

            #------------------------------------------------
            # Update currentreadings table with latest sensor info
            #------------------------------------------------

            db_id = 31

            if gb.DIAG_LEVEL & gb.DB_DETAIL:
                gb.logging.info("%s: UPDATE currentreadings; db_id: %d" %
                                (tm_str, db_id))
            id = 1
            self.db_cursor.execute("""UPDATE currentreadings SET tmstamp=%s, tempbmpf=%s, tempdhtf=%s, humidity=%s, baromB=%s WHERE id=%s""", (tm_str, bmp_temp_f, dht_temp_f, dht_humidity, pressure_hPa, id))
            self.db_cursor.execute("COMMIT")

        except mariadb.Error as e:
            gb.logging.error("MariaDB ERROR %d: %s" % (db_id, e))

    #------------------------------------
    # Request min/max values for past 30 days
    #------------------------------------
    def db_req_30day_min_max(self, wthr30_q_out):
        db_error = DB_SUCCESS;

        db_id = 8
        err_resp = -db_id

        tm_str = gb.get_date_with_seconds(gb.get_localdate_str())

        sql_select = 'SELECT * FROM readings30 WHERE id=1'
        try:
            select = self.db_cursor.execute(sql_select)
            select_data = self.db_cursor.fetchone()

            if (gb.DIAG_LEVEL & gb.WTHR_DAY_INIT):
                print("\nSELECT resp: ", select_data, "\n")

        except mariadb.Error as e:
            gb.logging.error("MariaDB ERROR %d: %s" % (db_id, e))
            db_error = err_resp

        wthr_info = []
        wthr_msgType = wthr30.WTHR30_30DAY_MIN_MAX
        wthr_info.append(wthr_msgType)
        wthr_info.append(db_error)

        if (db_error == DB_SUCCESS):

            #elements_in_select_data = len(select_data)
            #gb.logging.info("elements_in_select_data: %d" %
            #                    (elements_in_select_data))
            #for fld in range(elements_in_select_data):
            #    print(fld, select_data[fld])

            wthr_info.append(select_data[1])  # tmstamp
            wthr_info.append(select_data[2])  # min30bmpf
            wthr_info.append(select_data[3])  # max30bmpf
            wthr_info.append(select_data[4])  # min30bmpfts
            wthr_info.append(select_data[5])  # max30bmpfts
            wthr_info.append(select_data[6])  # min30dhtf
            wthr_info.append(select_data[7])  # max30dhtf
            wthr_info.append(select_data[8])  # min30dhtfts
            wthr_info.append(select_data[9])  # max30dhtfts
            wthr_info.append(select_data[10]) # min30humidity
            wthr_info.append(select_data[11]) # max30humidity
            wthr_info.append(select_data[12]) # min30humts
            wthr_info.append(select_data[13]) # max30humts
            wthr_info.append(select_data[14]) # low30mB
            wthr_info.append(select_data[15]) # high30mB
            wthr_info.append(select_data[16]) # low30mBts
            wthr_info.append(select_data[17]) # high30mBts

            if gb.DIAG_LEVEL & gb.WTHR_DAY_INIT:
                gb.logging.info("db_req_30day_min_max: "
                                "GET 30-DAY MIN MAX from DB")
                gb.logging.info("db_req_30day_min_max: "
                        "BME tmn: %.1f tmx: %.1f, "
                        "DHT tmn: %.1f tmx: %.1f" %
                        (select_data[2], select_data[3],
                         select_data[6], select_data[7]))

        if (gb.DIAG_LEVEL & gb.DB_SEND_TO_WTHR):
            gb.logging.info("%s: Sending %s(%d)" %
                     (tm_str, wthr30.get_wthr30_msg_str(wthr_msgType),
                      wthr_msgType))
        wthr30_q_out.put(wthr_info)

    #------------------------------------
    # Update min/max values for past 30 days
    #------------------------------------
    def db_update_30day_min_max(self, db_data):

        min30bmpts    = db_data[1]
        min30bmpf     = db_data[2]
        max30bmpts    = db_data[3]
        max30bmpf     = db_data[4]

        min30dhtts    = db_data[5]
        min30dhtf     = db_data[6]
        max30dhtts    = db_data[7]
        max30dhtf     = db_data[8]

        low30mbts     = db_data[9]
        low30mB       = db_data[10]
        high30mbts    = db_data[11]
        high30mB      = db_data[12]

        min30humts    = db_data[13]
        min30humidity = db_data[14]
        max30humts    = db_data[15]
        max30humidity = db_data[16]

        if gb.DIAG_LEVEL & gb.WTHR_DAY_INIT:
            gb.logging.info("db_update_today_min_max: "
                        "DHT tmn: %.1f tmx: %.1f, "
                        "HUM: hmn: %.1f hmx %.1f" %
                        (min30dhtf, max30dhtf, min30humidity, max30humidity))

        db_id = 9
        try:
            day_min_max = ("REPLACE INTO readings30 "
                           "(id, min30bmpts, min30bmpf, "
                           "max30bmpts, max30bmpf, "
                           "min30dhtts, min30dhtf, "
                           "max30dhtts, max30dhtf, "
                           "low30mbts, low30mB, "
                           "high30mbts, high30mB, "
                           "min30humts, min30humidity, "
                           "max30humts, max30humidity) "
                           "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")

            data_add = ('1', min30bmpts, min30bmpf, max30bmpts, max30bmpf, min30dhtts, min30dhtf, max30dhtts, max30dhtf, low30mbts, low30mB, high30mbts, high30mB, min30humts, min30humidity, max30humts, max30humidity)

            if gb.DIAG_LEVEL & gb.DB_DETAIL:
                tm_str = gb.get_date_with_seconds(gb.get_localdate_str())
                gb.logging.info("%s: REPLACE INTO readings30; db_id: %d" %
                                (tm_str, db_id))
            self.db_cursor.execute(day_min_max, data_add)
            self.db_cursor.execute("COMMIT")

        except mariadb.Error as e:
            gb.logging.error("MariaDB ERROR %d: %s" % (db_id, e))

    #------------------------------------
    # On startup only, request min/max values for current month
    #------------------------------------
    def db_req_mo_year_min_max(self, wthr30_q_out, db_data):
        db_error = DB_SUCCESS;

        db_id = 10
        err_resp = -db_id

        cur_mo = db_data[1]

        sql_select = f"SELECT * FROM monthdata WHERE id={cur_mo}"

        try:
            select = self.db_cursor.execute(sql_select)
            select_data = self.db_cursor.fetchone()

            if (gb.DIAG_LEVEL & gb.WTHR_DAY_INIT):
                print("\nSELECT resp: ", select_data, "\n")

        except mariadb.Error as e:
            gb.logging.error("MariaDB ERROR %d: %s" % (db_id, e))
            db_error = err_resp

        wthr_info = []
        wthr_msgType = wthr30.WTHR30_MO_YEAR_MIN_MAX
        wthr_info.append(wthr_msgType)
        wthr_info.append(db_error)

        if (db_error == DB_SUCCESS):

            tm_str = gb.get_date_with_seconds(gb.get_localdate_str())

            #elements_in_select_data = len(select_data)
            #gb.logging.info("elements_in_select_data: %d" %
            #                    (elements_in_select_data))
            #for fld in range(elements_in_select_data):
            #    print(fld, select_data[fld])

            wthr_info.append(select_data[0])  # id/month
            wthr_info.append(select_data[1])  # month (str)
                                              # [2] tmstamp
            wthr_info.append(select_data[3])  # mintempfts
            wthr_info.append(select_data[4])  # mintempf
            wthr_info.append(select_data[5])  # maxtempfts
            wthr_info.append(select_data[6])  # maxtempf

            wthr_info.append(select_data[7]) # minhumts
            wthr_info.append(select_data[8]) # minhum
            wthr_info.append(select_data[9]) # maxhumts
            wthr_info.append(select_data[10]) # maxhum

            wthr_info.append(select_data[11]) # lowmBts
            wthr_info.append(select_data[12]) # lowmB
            wthr_info.append(select_data[13]) # highmBts
            wthr_info.append(select_data[14]) # highmB

            if gb.DIAG_LEVEL & gb.WTHR_DAY_INIT:
                gb.logging.info("db_req_mo_year_min_max: "
                                "GET ALL-TIME MIN MAX from DB")
                gb.logging.info("db_req_mo_year_min_max: "
                        "TEMP tmn: %.1f tmx: %.1f, "
                        "HUM hmn: %.1f hmx: %.1f" %
                        (select_data[4], select_data[6],
                         select_data[8], select_data[10]))

        if (gb.DIAG_LEVEL & gb.DB_SEND_TO_WTHR):
            gb.logging.info("%s: Sending %s(%d)" %
                     (tm_str, wthr30.get_wthr30_msg_str(wthr_msgType),
                      wthr_msgType))
        wthr30_q_out.put(wthr_info)

        return


    #------------------------------------
    # Update min/max values for current month, this year
    #------------------------------------
    def db_update_mo_year_min_max(self, db_data):

        id            = db_data[1]
        month         = db_data[2]

        mintempfts    = db_data[3]
        mintempf      = db_data[4]
        maxtempfts    = db_data[5]
        maxtempf      = db_data[6]

        minhumts      = db_data[7]
        minhum        = db_data[8]
        maxhumts      = db_data[9]
        maxhum        = db_data[10]

        lowmBts       = db_data[11]
        lowmB         = db_data[12]
        highmBts      = db_data[13]
        highmB        = db_data[14]

        #print(db_data[0], id, month)
        #print(mintempfts, mintempf, maxtempfts, maxtempf)
        #print(minhumts, minhum, maxhumts, maxhum)
        #print(lowmBts, lowmB, highmBts, highmB)

        if gb.DIAG_LEVEL & gb.WTHR30_MO_INIT:
            gb.logging.info("db_update_mo_year_min_max: "
                        "TEMP tmn: %.1f tmx: %.1f, "
                        "HUM: hmn: %.1f hmx %.1f" %
                        (mintempf, maxtempf, minhum, maxhum))

        db_id = 11
        try:
            mo_year_min_max = ("REPLACE INTO monthdata "
                           "(id, month, "
                           "mintempfts, mintempf, "
                           "maxtempfts, maxtempf, "
                           "minhumts, minhum, "
                           "maxhumts, maxhum, "
                           "lowmBts, lowmB, "
                           "highmBts, highmB) "
                           "VALUES (%s, %s, %s, %s, %s, %s, "
                           "%s, %s, %s, %s, %s, %s, %s, %s)")

            data_add = (id, month, mintempfts, mintempf, maxtempfts, maxtempf, minhumts, minhum, maxhumts, maxhum, lowmBts, lowmB, highmBts, highmB)

            if gb.DIAG_LEVEL & gb.DB_DETAIL:
                tm_str = gb.get_date_with_seconds(gb.get_localdate_str())
                gb.logging.info("%s: REPLACE INTO monthdata; db_id: %d" %
                                (tm_str, db_id))

            self.db_cursor.execute(mo_year_min_max, data_add)
            self.db_cursor.execute("COMMIT")

        except mariadb.Error as e:
            gb.logging.error("MariaDB ERROR %d: %s" % (db_id, e))

    #------------------------------------
    # Request all-time min/max values for current month
    #------------------------------------
    def db_req_alltime_min_max(self, wthr30_q_out, db_data):
        db_error = DB_SUCCESS;

        db_id = 12
        err_resp = -db_id

        cur_mo = db_data[1]

        sql_select = f"SELECT * FROM alltimedata WHERE id={cur_mo}"

        try:
            select = self.db_cursor.execute(sql_select)
            select_data = self.db_cursor.fetchone()

            if (gb.DIAG_LEVEL & gb.WTHR_DAY_INIT):
                print("\nSELECT resp: ", select_data, "\n")

        except mariadb.Error as e:
            gb.logging.error("MariaDB ERROR %d: %s" % (db_id, e))
            db_error = err_resp

        wthr_info = []
        wthr_msgType = wthr30.WTHR30_ALL_TIME_MIN_MAX
        wthr_info.append(wthr_msgType)
        wthr_info.append(db_error)

        if (db_error == DB_SUCCESS):

            tm_str = gb.get_date_with_seconds(gb.get_localdate_str())

            #elements_in_select_data = len(select_data)
            #gb.logging.info("elements_in_select_data: %d" %
            #                    (elements_in_select_data))
            #for fld in range(elements_in_select_data):
            #    print(fld, select_data[fld])

            wthr_info.append(select_data[0])  # id/month
            wthr_info.append(select_data[1])  # month (str)
                                              # [2] tmstamp
            wthr_info.append(select_data[3])  # mintempfts
            wthr_info.append(select_data[4])  # mintempf
            wthr_info.append(select_data[5])  # maxtempfts
            wthr_info.append(select_data[6])  # maxtempf

            wthr_info.append(select_data[7]) # minhumts
            wthr_info.append(select_data[8]) # minhum
            wthr_info.append(select_data[9]) # maxhumts
            wthr_info.append(select_data[10]) # maxhum

            wthr_info.append(select_data[11]) # lowmBts
            wthr_info.append(select_data[12]) # lowmB
            wthr_info.append(select_data[13]) # highmBts
            wthr_info.append(select_data[14]) # highmB

            if gb.DIAG_LEVEL & gb.WTHR_DAY_INIT:
                gb.logging.info("db_req_alltime_min_max: "
                                "GET ALL-TIME MIN MAX from DB")
                gb.logging.info("db_req_alltime_min_max: "
                        "TEMP tmn: %.1f tmx: %.1f, "
                        "HUM hmn: %.1f hmx: %.1f" %
                        (select_data[4], select_data[6],
                         select_data[8], select_data[10]))

        if (gb.DIAG_LEVEL & gb.DB_SEND_TO_WTHR):
            gb.logging.info("%s: Sending %s(%d)" %
                     (wthr30.get_wthr30_msg_str(wthr_msgType),wthr_msgType))
        wthr30_q_out.put(wthr_info)

    #------------------------------------
    # Update all-time data for current month
    #------------------------------------
    def db_update_alltime_min_max(self, db_data):

        mo_id         = db_data[1]
        mo_str        = db_data[2]

        mintempfts    = db_data[3]
        mintempf      = db_data[4]
        maxtempfts    = db_data[5]
        maxtempf      = db_data[6]

        minhumts      = db_data[7]
        minhum        = db_data[8]
        maxhumts      = db_data[9]
        maxhum        = db_data[10]

        lowmBts       = db_data[11]
        lowmB         = db_data[12]
        highmBts      = db_data[13]
        highmB        = db_data[14]

        if gb.DIAG_LEVEL & gb.WTHR_DAY_INIT:
            gb.logging.info("db_update_alltime_min_max: "
                        "TEMP tmn: %.1f tmx: %.1f, "
                        "HUM: hmn: %.1f hmx %.1f" %
                        (mintempf, maxtempf, minhum, maxhum))

        db_id = 13
        try:
            all_time_min_max = ("REPLACE INTO alltimedata "
                           "(id, month, "
                           "mintempfts, mintempf, "
                           "maxtempfts, maxtempf, "
                           "minhumts, minhum, "
                           "maxhumts, maxhum, "
                           "lowmBts, lowmB, "
                           "highmBts, highmB) "
                           "VALUES (%s, %s, %s, %s, %s, %s, "
                           "%s, %s, %s, %s, %s, %s, %s, %s)")

            data_add = (mo_id, mo_str, mintempfts, mintempf, maxtempfts, maxtempf, minhumts, minhum, maxhumts, maxhum, lowmBts, lowmB, highmBts, highmB)

            if gb.DIAG_LEVEL & gb.DB_DETAIL:
                tm_str = gb.get_date_with_seconds(gb.get_localdate_str())
                gb.logging.info("%s: REPLACE INTO alltimedata; db_id: %d" %
                                (tm_str, db_id))

            self.db_cursor.execute(all_time_min_max, data_add)
            self.db_cursor.execute("COMMIT")

        except mariadb.Error as e:
            gb.logging.error("MariaDB ERROR %d: %s" % (db_id, e))

    #------------------------------------
    # Update high/low averages for current month
    # Values are updated around midnight each day
    #------------------------------------
    def db_update_high_low_avg(self, db_data):
        #print(db_data)
        
        cur_mo_id  = db_data[1]
        cur_mo_str = db_data[2]
        high_tally = db_data[3]
        avg_high   = db_data[4]
        low_tally  = db_data[5]
        avg_low    = db_data[6]

        tm_str = gb.get_date_with_seconds(gb.get_localdate_str())

        gb.logging.info("UPDATE high/low avg for %s(%d)" %
                        (db_data[2], db_data[1]))

        gb.logging.info("%s: db_update_high_low_avg: %s(%d) "
                        "HIGH: tally: %d avg: %.1f" %
                        (tm_str, cur_mo_str, cur_mo_id, high_tally, avg_high))
        gb.logging.info("%s: db_update_high_low_avg: %s(%d) "
                        "LOW: tally: %d avg: %.1f" %
                        (tm_str, cur_mo_str, cur_mo_id, low_tally, avg_low))

        db_id = 14

        try:
            #if (gb.DIAG_LEVEL & 0x10):
            gb.logging.info("UPDATE monthavg for %s; db_id: %d" %
                                (db_data[2], db_id))

            self.db_cursor.execute("""UPDATE monthavg SET avghightally=%s, avghightempf=%s, avglowtally=%s, avglowtempf=%s WHERE id=%s""", (high_tally, avg_high, low_tally, avg_low, cur_mo_id))
            self.db_cursor.execute("COMMIT")

        except mariadb.Error as e:
            gb.logging.error("MariaDB ERROR %d: %s" % (db_id, e))

    #############################################################
    # Initialize in-memory tallies and running average high
    # and low temperatures for a month
    # DB_INIT_HIGH_LOW_AVG
    #############################################################
    def db_get_high_low_avg_temp(self, db_data, avg_q_out):

        global DB_SUCCESS
        global DB_SELECT

        tm_str = gb.get_date_with_seconds(gb.get_localdate_str())

        gb.logging.info("%s: Processing db_get_high_low_avg_temp for %s(%d)" %
                        (tm_str, db_data[1], db_data[2]))

        mo_str = db_data[1]
        mo_id  = db_data[2]

        db_error = DB_SUCCESS;

        db_id = 29
        err_resp = -db_id

        sql_select = "SELECT avghightally,avghightempf,avglowtally,avglowtempf from monthavg where id={0}".format(mo_id)
        gb.logging.debug("db_get_high_low_avg_temp: averages SQL: %s" %
                         (sql_select))
        try:
            select = self.db_cursor.execute(sql_select)
            select_data = self.db_cursor.fetchone()

            if (gb.DIAG_LEVEL & gb.DB_DETAIL):
                print("\nSELECT resp: ", select_data, "\n")

        except mariadb.Error as e:
            gb.logging.error("MariaDB ERROR %d: %s" % (db_id, e))
            db_error = err_resp

        if (db_error == DB_SUCCESS):

            tm_str = gb.get_date_with_seconds(gb.get_localdate_str())

            if (gb.DIAG_LEVEL & gb.DB_DETAIL):
                elements_in_select_data = len(select_data)
                gb.logging.info("elements_in_select_data: %d" %
                                (elements_in_select_data))
                print(select_data[0],select_data[1])
                print(select_data[2],select_data[3])

            db_id = 30
            err_resp = -db_id

            hightally = select_data[0]
            highavg = select_data[1]
            lowtally = select_data[2]
            lowavg = select_data[3]

            gb.logging.info("%s: db_get_high_low_avg_temp: hightally %d "
                            "highavg %.1f; lowtally %d lowavg %.1f" %
                            (tm_str, hightally, highavg, lowtally, lowavg))

            avg_msgType = wavg.WAVG_HIGH_LOW_INIT
            avgInfo = []
            avgInfo.append(avg_msgType)
            avgInfo.append(mo_str)
            avgInfo.append(hightally)
            avgInfo.append(highavg)
            avgInfo.append(lowtally)
            avgInfo.append(lowavg)
            gb.logging.info("%s: Sending %s(%d)" %
                             (tm_str, wavg.get_wavg_msg_str(avg_msgType),
                              avg_msgType))
            avg_q_out.put(avgInfo)

        else:
            gb.logging.error("Failed to get high/low running averages")
            return

    #------------------------------------
    # Update daytime average and nighttime average for current month
    #------------------------------------
    def db_update_day_night_avg(self, db_data):

        #print(db_data)

        db_id = 15

        mo_id           = db_data[1]
        mo_str          = db_data[2]
        day_or_night    = db_data[3]

        day_tally       = db_data[4]
        avg_day_tempf   = db_data[5]
        night_tally     = db_data[6]
        avg_night_tempf = db_data[7]

        #if gb.DIAG_LEVEL & gb.WAVG_DAY_NIGHT:
        tm_str = gb.get_date_with_seconds(gb.get_localdate_str())
        gb.logging.info("%s: db_update_day_night_avg: UPDATE day/night for %s(%d)" %
                        (tm_str, mo_str, mo_id))
        gb.logging.info("%s: mo_id: %d, day_tally: %d, avg_day_tempf: %.1f" %
                        (tm_str, mo_id, day_tally, avg_day_tempf))
        gb.logging.info("%s: mo_id: %d, night_tally: %d, avg_night_tempf: %.1f" %
                        (tm_str, mo_id, night_tally, avg_night_tempf))

        try:
            if day_or_night == wavg.DAYTIME:
                # DAYTIME
                self.db_cursor.execute("""UPDATE monthavg SET daytally=%s, avgdaytimetempf=%s WHERE id=%s""", (day_tally, avg_day_tempf, mo_id))

            else:
                # NIGHTTIME
                self.db_cursor.execute("""UPDATE monthavg SET nighttally=%s, avgnighttimetempf=%s WHERE id=%s""", (night_tally, avg_night_tempf, mo_id))

        except mariadb.Error as e:
            gb.logging.error("MariaDB ERROR %d: %s" % (db_id, e))

    #############################################################
    # Initialize in-memory tallies and running average daytime
    # and nighttime temperatures for a month
    # DB_INIT_DAY_NIGHT_AVG
    #############################################################
    def db_get_day_night_avg_temp(self, db_data, avg_q_out):

        global DB_SUCCESS
        global DB_SELECT

        tm_str = gb.get_date_with_seconds(gb.get_localdate_str())

        gb.logging.info("%s: Processing db_get_day_night_avg_temp for %s(%d)" %
                        (tm_str, db_data[1], db_data[2]))

        mo_str = db_data[1]
        mo_id  = db_data[2]

        db_error = DB_SUCCESS;

        db_id = 16
        err_resp = -db_id

        sql_select = "SELECT daytally,avgdaytimetempf,nighttally,avgnighttimetempf from monthavg where id={0}".format(mo_id)
        gb.logging.debug("db_get_day_night_avg_temp: averages SQL: %s" %
                         (sql_select))
        try:
            select = self.db_cursor.execute(sql_select)
            select_data = self.db_cursor.fetchone()

            if (gb.DIAG_LEVEL & gb.DB_DETAIL):
                print("\nSELECT resp: ", select_data, "\n")

        except mariadb.Error as e:
            gb.logging.error("MariaDB ERROR %d: %s" % (db_id, e))
            db_error = err_resp

        if (db_error == DB_SUCCESS):

            tm_str = gb.get_date_with_seconds(gb.get_localdate_str())

            elements_in_select_data = len(select_data)
            if (gb.DIAG_LEVEL & gb.DB_DETAIL):
                gb.logging.info("elements_in_select_data: %d" %
                                (elements_in_select_data))
                print(select_data[0],select_data[1])
                print(select_data[2],select_data[3])

            db_id = 17
            err_resp = -db_id

            daytally = select_data[0]
            dayavg = select_data[1]
            nighttally = select_data[2]
            nightavg = select_data[3]

            avg_msgType = wavg.WAVG_DAY_NIGHT_INIT
            avgInfo = []
            avgInfo.append(avg_msgType)
            avgInfo.append(mo_str)
            avgInfo.append(daytally)
            avgInfo.append(dayavg)
            avgInfo.append(nighttally)
            avgInfo.append(nightavg)
            gb.logging.info("%s: Sending %s(%d)" %
                             (tm_str, wavg.get_wavg_msg_str(avg_msgType),
                              avg_msgType))
            avg_q_out.put(avgInfo)

        else:
            gb.logging.error("Failed to get day/night running averages")
            return

    #------------------------------------
    # Adjust sunrise and sunset times if daylight savings time in effect
    #------------------------------------
    def adjust_dst(self, date, sunrise, sunset):

        global DST_START
        global DST_END

        sr = sunrise
        ss = sunset

        sr_str = str(sr)
        ss_str = str(ss)
        dt_str = str(date)

        dt_sr = dt_str + " " + sr_str
        dt_ss = dt_str + " " + ss_str

        format_data = "%Y-%m-%d %H:%M:%S"
        SUNRISE_TODAY = gb.datetime.strptime(dt_sr, format_data)
        SUNSET_TODAY = gb.datetime.strptime(dt_ss, format_data)

        # Update daylight savings time start/end to current year
        cur_time = gb.datetime.now()
        DST_START = DST_START.replace(year=cur_time.year)
        DST_END = DST_END.replace(year=cur_time.year)

        dst = ""
        if (SUNRISE_TODAY > DST_START) and (SUNRISE_TODAY < DST_END):
            gb.logging.info("DAYLIGHT SAVINGS TIME IN EFFECT")
            # Daylight Savings Time in affect, adjust sunrise/sunset
            SUNRISE_TODAY = SUNRISE_TODAY + gb.timedelta(hours=1)
            SUNSET_TODAY = SUNSET_TODAY + gb.timedelta(hours=1)
            dst = "dst: "

            sr = SUNRISE_TODAY.time()
            ss = SUNSET_TODAY.time()

        return sr, ss

    #------------------------------------
    # Update sunrise and sunset times for current day into current_stats table
    #------------------------------------
    def update_suntimes(self, date, sunrise, sunset):

        db_id = 19
        try:
            self.db_cursor.execute("""UPDATE current_stats SET dt=%s, sunrise=%s, sunset=%s WHERE id=1""", (date, sunrise, sunset))
            self.db_cursor.execute("COMMIT")

        except mariadb.Error as e:
            gb.logging.error("MariaDB ERROR %d: %s" % (db_id, e))

    #-----------------------------------------
    # Get sunrise and sunset times from sun table
    #-----------------------------------------
    def db_get_suntimes(self, db_data, avg_q_out):

        date = db_data[1]

        db_id = 18
        err_resp = -db_id
        db_error = DB_SUCCESS;

        tm_str = gb.get_date_with_seconds(gb.get_localdate_str())

        sql_select = 'SELECT sunrise, sunset from sun where dt="{0}"'.format(date)
        gb.logging.debug("db_get_suntimes: averages SQL: %s" % (sql_select))

        try:
            select = self.db_cursor.execute(sql_select)
            select_data = self.db_cursor.fetchone()

        except mariadb.Error as e:
            gb.logging.error("MariaDB ERROR %d: %s" % (db_id, e))
            db_error = err_resp

        if (db_error == DB_SUCCESS):
            if (gb.DIAG_LEVEL & gb.DB_DETAIL):
                elements_in_select_data = len(select_data)
                gb.logging.info("elements_in_select_data: %d" %
                                    (elements_in_select_data))
                print(select_data[0],select_data[1])

            sunrise = select_data[0]
            sunset = select_data[1]

            sr, ss = self.adjust_dst(date, sunrise, sunset)

            # Update sunrise and sunset times in current_stats table.
            # If daylight savings time in effect, these times are
            # udpated to reflect DST
            self.update_suntimes(date, sr, ss)

            avg_msgType = wavg.WAVG_SUNTIMES
            avgInfo = []
            avgInfo.append(avg_msgType)
            avgInfo.append(date)
            avgInfo.append(sr)
            avgInfo.append(ss)
            gb.logging.info("%s: Sending %s(%d)" %
                             (tm_str, wavg.get_wavg_msg_str(avg_msgType),
                              avg_msgType))
            avg_q_out.put(avgInfo)

        else:
            gb.logging.info("Failed to get sunrise/sunset times")
            return

    #------------------------------------
    #------------------------------------
    def process_weather_reading(self, msgType, msg):

        tm_str     = msg[1]
        wavg1      = msg[2]
        wsdev1     = msg[3]
        wavg5      = msg[4]
        wsdev5     = msg[5]
        windspeed  = msg[6]

        wrvolt     = msg[7]
        wrval      = msg[8]
        wrdir      = msg[9]
        wrdir_str  = msg[10]    # magnetic 8-point resistor wind dir str

        whvolt     = msg[11]
        whval      = msg[12]
        whdeg      = msg[13]     # true wind direction degrees
        whdir_str  = msg[14]     # true 16-point wind direction str
        wmdir_str  = msg[15]     # magnetic 8-point wind direction str

        rain_dump_cnt = msg[16]  # teeter-totter bucket dumps
        rain_tally    = msg[17]  # inches

        if (gb.DIAG_LEVEL & gb.DB):
            gb.logging.info("Running process_weather_reading(): tmstamp %s" %
                            (tm_str))
            gb.logging.info("tm_str: %s %.1f mph %.1f deg, "
                            "%0.2f inches cnt %d" %
                            (tm_str, wavg1, whdeg, rain_tally, rain_dump_cnt))
        db_id = 20

        try:
            add_reading = ("REPLACE INTO windrain "
                         "(recordType, tmstamp, dbid, windavg1, windsdev1, windavg5, windsdev5, windspeed, wind_h_volts, wind_h_val, wind_degree, wind_dir_str, wind_mag_dir_str, wind_r_volts, wind_r_val, dir, winddir, rainfall, rainfall_counter) "
                         "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")

            data_add = ('AVG', tm_str, db_id, wavg1, wsdev1, wavg5, wsdev5, windspeed, whvolt, whval, whdeg, whdir_str, wmdir_str, wrvolt, wrval, wrdir, wrdir_str, rain_tally, rain_dump_cnt)

            self.db_cursor.execute(add_reading, data_add)
            self.db_cursor.execute("COMMIT")

        except mariadb.Error as e:
            gb.logging.error("MariaDB ERROR %d: %s" % (db_id, e))

        db_id = 21 
        try:
            self.db_cursor.execute("""UPDATE current_stats SET windavg1=%s, windavg5=%s, wind_degree=%s, windspeed=%s, wind_dir=%s, wind_dir_str=%s, rainfall_today=%s, rainfall_counter=%s WHERE id=1""", (wavg1, wavg5, whdeg, windspeed, wrdir, whdir_str, rain_tally, rain_dump_cnt))
            self.db_cursor.execute("COMMIT")

        except mariadb.Error as e:
            gb.logging.error("MariaDB ERROR %d: %s" % (db_id, e))

    #------------------------------------
    #------------------------------------
    def process_gust(self, msgType, msg):

        tm_str = msg[1]
        avg5 = msg[2]
        mph = msg[3]
        intervals = msg[4]

        if (gb.DIAG_LEVEL & gb.DB):
            gb.logging.info("Running process_gust(): tmstamp %s" %
                            (tm_str))
            gb.logging.info("tm_str: %s avg %.1f, gust %0.1f mph intervals %d" %
                            (tm_str, avg5, mph, intervals))
        db_id = 5
        try:
            db_sql = ("REPLACE INTO windrain "
                      "(recordType, tmstamp, dbid, windavg5, windgust, gust_interval) "
                      "VALUES (%s, %s, %s, %s, %s, %s)")
            data_add = ('GUST', tm_str, db_id, avg5, mph, intervals)
            self.db_cursor.execute(db_sql, data_add)
            self.db_cursor.execute("COMMIT")

        except mariadb.Error as e:
            gb.logging.error("MariaDB ERROR %d: %s" % (db_id, e))

        db_id = 22
        try:
            self.db_cursor.execute("""UPDATE current_stats SET gust_tm=%s, gust=%s, gust_intervals=%s WHERE id=1""", (tm_str, mph, intervals))
            self.db_cursor.execute("COMMIT")

        except mariadb.Error as e:
            gb.logging.error("MariaDB ERROR %d: %s" % (db_id, e))

    #------------------------------------
    #------------------------------------
    def process_max_1_hour(self, msgType, msg):

        max_tm = str(msg[1])
        mph = msg[2]

        db_id = 23
        try:
            self.db_cursor.execute("""UPDATE current_stats SET windmax1hour_tm=%s, windmax1hour=%s WHERE id=1""", (max_tm, mph))
            self.db_cursor.execute("COMMIT")

        except mariadb.Error as e:
            gb.logging.error("MariaDB ERROR %d: %s" % (db_id, e))

    #------------------------------------
    #------------------------------------
    def process_max_today(self, msgType, msg):
        max_tm = str(msg[1])
        mph = msg[2]

        db_id = 24
        try:
            self.db_cursor.execute("""UPDATE current_stats SET windmaxtoday_tm=%s, windmaxtoday=%s WHERE id=1""", (max_tm, mph))
            self.db_cursor.execute("COMMIT")

        except mariadb.Error as e:
            gb.logging.error("MariaDB ERROR %d: %s" % (db_id, e))

    #------------------------------------
    # Update CPU temperature in database
    # DB_CPU_TEMPERATURE
    #------------------------------------
    def db_update_cpu_temperature(self, db_data):

        global PRIOR_CPU_TEMPC

        tm_str = db_data[1]
        cpu_c = db_data[2]
        fan_st = db_data[3]

        pri_key = 1

        db_id = 25
        try:
            if (gb.DIAG_LEVEL & 0x10):
                gb.logging.info("UPDATE cpulatest; db_id: %d" % (db_id))

            self.db_cursor.execute("""UPDATE cpulatest SET cputempc=%s WHERE id=%s""", (cpu_c, pri_key))
            self.db_cursor.execute("COMMIT")

        except mariadb.Error as e:
            gb.logging.error("MariaDB ERROR %d: %s" % (db_id, e))

        # Update temperature history only if change greater
        # FAN_TEMPERATURE_DIFF_DB
        if (abs(PRIOR_CPU_TEMPC - cpu_c) >= fan.FAN_TEMPERATURE_DIFF_DB or
            (PRIOR_CPU_TEMPC == gb.PRIOR_TEMP_DFLT)):
            PRIOR_CPU_TEMPC = cpu_c

            db_id = 26
            try:
                if (gb.DIAG_LEVEL & 0x10):
                    gb.logging.info("REPLACE INTO historycputemp; db_id: %d" %
                               (db_id))

                add_history = ("REPLACE INTO historycputemp "
                               "(tmstamp, cputempc, cpufanstate) "
                               "VALUES (%s, %s, %s)")
                data_add = (tm_str, cpu_c, fan_st)

                self.db_cursor.execute(add_history, data_add)
                self.db_cursor.execute("COMMIT")

            except mariadb.Error as e:
                gb.logging.error("MariaDB ERROR %d: %s" % (db_id, e))

    #------------------------------------
    # Update CPU fan state in database
    # DB_CPU_FAN
    #------------------------------------
    def db_update_cpu_fan(self, db_data):

        tm_str = db_data[1]
        fan_st = db_data[2]

        pri_key = 1

        db_id = 27
        try:
            if (gb.DIAG_LEVEL & 0x10):
                gb.logging.info("UPDATE cpulatest; db_id: %d" % (db_id))

            self.db_cursor.execute("""UPDATE cpulatest SET fanchangetm=%s, cpufanstate=%s WHERE id=%s""", (tm_str, fan_st, pri_key))
            self.db_cursor.execute("COMMIT")

        except mariadb.Error as e:
            gb.logging.error("MariaDB ERROR %d: %s" % (db_id, e))

        db_id = 28
        try:
            if (gb.DIAG_LEVEL & 0x10):
                gb.logging.info("REPLACE INTO historycputemp; db_id: %d" %
                               (db_id))

            add_history = ("REPLACE INTO historycputemp "
                                  "(tmstamp, cpufanstate) "
                                  "VALUES (%s, %s)")
            data_add = (tm_str, fan_st)

            self.db_cursor.execute(add_history, data_add)
            self.db_cursor.execute("COMMIT")

        except mariadb.Error as e:
            gb.logging.error("MariaDB ERROR 2049: %s" % (e))

    #------------------------------------
    # Update keep-alive status for threads and processes
    #------------------------------------
    def process_keep_alive(self, db_msgType):

        tm_str = gb.get_date_with_seconds(gb.get_localdate_str())

        # Get index into keep alive table
        db_indx = db.get_keep_alive_index(db_msgType)

        db_id = 28

        try:
            if (gb.DIAG_LEVEL & gb.DB_KEEP_ALIVE_UPDATE):
                gb.logging.info( \
                    "UPDATE keepalive for %s(%d); db_indx %d, db_id: %d" %
                    (db.get_db_msg_str(db_msgType), db_msgType,
                     db_indx, db_id))

            self.db_cursor.execute("""UPDATE keepalive SET tmstamp=%s WHERE id=%s""", (tm_str, db_indx))
            self.db_cursor.execute("COMMIT")

        except mariadb.Error as e:
            gb.logging.error("MariaDB ERROR %d: %s" % (db_id, e))

    #############################################################
    # Database run function
    #############################################################
    def run(self):

        db_q_in = self.args[0]
        wthr_q_out = self.args[1]
        wthr30_q_out = self.args[2]
        avg_q_out = self.args[3]
        end_event = self.args[4]

        gb.logging.info("Running %s" % (self.name))
        gb.logging.debug(self.args)

        init_1 = False
        init_30 = False
        not_sent = True

        try:
            self_db_conn = mariadb.connect(
                user=config.dbuser,
                password=config.dbpwd,
                host="localhost",
                port=3306,
                database="weather"
            )

            self_db_conn.autocommit = False
            gb.logging.info("Database autocommit DISABLED, DIAG_LEVEL 0x%x" %
                         (gb.DIAG_LEVEL))

            self.db_cursor = self_db_conn.cursor()

        except mariadb.Error as e:
            gb.logging.error("MariaDB ERROR 0: %s" % (e))
            sys.exit(1)

        self.add_start_record()

        ###################################################
        # DB main loop: Part 1: INCOMING MESSAGES
        ###################################################
        while not end_event.isSet():

            #gb.logging.info("DB Part 1: Check for incoming DB msgs")

            while not db_q_in.empty():
                db_data = db_q_in.get()
                db_msgType = db_data[0]
                
                if gb.DIAG_LEVEL & gb.DB_MSG_DETAIL:
                    gb.logging.info("Recvd: %s(%d)" %
                                     (db.get_db_msg_str(db_msgType),db_msgType))
                    gb.logging.debug(db_data)

                if (db_msgType == db.DB_EXIT):
                    gb.logging.info("%s: Cleanup prior to exit" % (self.name))

                elif (db_msgType == db.DB_CPU_TEMPERATURE):
                    self.db_update_cpu_temperature(db_data)

                elif (db_msgType == db.DB_CPU_FAN):
                    self.db_update_cpu_fan(db_data)

                elif (db_msgType == db.DB_SUNTIMES):
                    self.db_get_suntimes(db_data, avg_q_out)

                elif (db_msgType == db.DB_LOCAL_STATS):
                    self.db_update_local(db_data)

                elif (db_msgType == db.DB_TODAY_MIN_MAX):
                    self.db_update_today_min_max(db_data)

                elif (db_msgType == db.DB_REQ_TODAY_MIN_MAX):
                    self.db_req_today_min_max(wthr_q_out)

                elif (db_msgType == db.DB_24HR_MIN_MAX):
                    self.db_update_24hr_min_max(db_data)

                elif (db_msgType == db.DB_REQ_24HR_MIN_MAX):
                    self.db_req_24hr_min_max(wthr_q_out)

                elif (db_msgType == db.DB_30DAY_MIN_MAX):
                    self.db_update_30day_min_max(db_data)

                elif (db_msgType == db.DB_REQ_30DAY_MIN_MAX):
                    self.db_req_30day_min_max(wthr30_q_out)

                elif (db_msgType == db.DB_MO_YEAR_MIN_MAX):
                    self.db_update_mo_year_min_max(db_data)

                elif (db_msgType == db.DB_REQ_MO_YEAR_MIN_MAX):
                    self.db_req_mo_year_min_max(wthr30_q_out, db_data)

                elif (db_msgType == db.DB_ALLTIME_MIN_MAX):
                    self.db_update_alltime_min_max(db_data)

                elif (db_msgType == db.DB_REQ_ALL_TIME_MIN_MAX):
                    self.db_req_alltime_min_max(wthr30_q_out, db_data)

                elif (db_msgType == db.DB_DAY_HIGH_LOW_AVG):
                    self.db_update_high_low_avg(db_data)

                elif (db_msgType == db.DB_INIT_HIGH_LOW_AVG):
                    self.db_get_high_low_avg_temp(db_data, avg_q_out)

                elif (db_msgType == db.DB_DAY_NIGHT_AVG):
                    self.db_update_day_night_avg(db_data)

                elif (db_msgType == db.DB_INIT_DAY_NIGHT_AVG):
                    self.db_get_day_night_avg_temp(db_data, avg_q_out)

                elif (db_msgType == db.DB_READING):
                    if gb.DIAG_LEVEL & gb.DB_MSG_DETAIL:
                        gb.logging.info("%s: Processing wind/rain msg %s(%d)" %
                            (self.name, db.get_db_msg_str(db_msgType),
                             db_msgType))
                    self.process_weather_reading(db_msgType, db_data)

                elif (db_msgType == db.DB_GUST):
                    if gb.DIAG_LEVEL & gb.DB_MSG_DETAIL:
                        gb.logging.info("%s: Processing gust msg %s(%d)" %
                            (self.name, db.get_db_msg_str(db_msgType),
                             db_msgType))
                    self.process_gust(db_msgType, db_data)

                elif (db_msgType == db.DB_MAX_1_HOUR):
                    if gb.DIAG_LEVEL & gb.DB_MSG_DETAIL:
                        gb.logging.info("%s: Processing gust msg %s(%d)" %
                            (self.name, db.get_db_msg_str(db_msgType),
                             db_msgType))
                    self.process_max_1_hour(db_msgType, db_data)

                elif (db_msgType == db.DB_MAX_TODAY):
                    if gb.DIAG_LEVEL & gb.DB_MSG_DETAIL:
                        gb.logging.info("%s: Processing gust msg %s(%d)" %
                            (self.name, db.get_db_msg_str(db_msgType),
                             db_msgType))
                    self.process_max_today(db_msgType, db_data)

                elif (db_msgType == db.DB_WTHR_ALIVE) or \
                     (db_msgType == db.DB_WTHR30_ALIVE) or \
                     (db_msgType == db.DB_WAVG_ALIVE) or \
                     (db_msgType == db.DB_COORD_ALIVE) or \
                     (db_msgType == db.DB_WV_ALIVE) or \
                     (db_msgType == db.DB_FAN_ALIVE) or \
                     (db_msgType == db.DB_RG_ALIVE) or \
                     (db_msgType == db.DB_AN_ALIVE) or \
                     (db_msgType == db.DB_SNSR_ALIVE):
                    self.process_keep_alive(db_msgType)

                elif (db_msgType == db.DB_TEST):
                    gb.logging.info("%s: Processing %s(%d)" %
                            (self.name, db.get_db_msg_str(db_msgType),
                             db_msgType))

                else:
                    gb.logging.error("Invalid DB message type: %d" %
                                                          (db_msgType))
                    gb.logging.error(db_data)

            gb.time.sleep(DB_SLEEP)

        self.add_stop_record()
        gb.time.sleep(1)
        gb.logging.info("Exiting %s" % (self.name))
