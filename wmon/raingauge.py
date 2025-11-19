import gb

import rg
import co
import db

###########################################################
# Rain Gauge process
###########################################################
def log_rain_total(total_rainfall):
    rain_total_rounded = 0.0
    if (total_rainfall != 0.0):
        rain_total_rounded = total_rainfall + 0.005
    tm_str = gb.get_date_with_seconds(gb.get_localdate_str())
    gb.logging.info("%s: RAINFALL TODAY: %0.2f inches" %
                    (tm_str, rain_total_rounded))

def send_rainfall(nm, pd, co_mp_q_out, msg_in, dump_cnt, rainfall):

    e_tm = msg_in[1]
    req_id = msg_in[2]
    msg = []
    msgType = co.CO_MP_RAINFALL
    msg.append(msgType)
    msg.append(e_tm)
    msg.append(req_id)
    msg.append(dump_cnt)
    msg.append(rainfall)
    if (gb.DIAG_LEVEL & gb.RAIN_MSG):
        gb.logging.info("%s(%d) sending %s(%d): rainfall %0.2f" %
                    (nm, pd, co.get_co_msg_str(msgType), msgType, rainfall))
    co_mp_q_out.put(msg)

#---------------------------------------------------------
# Send keep-alive (I am alive) message to DB via Coordinator
#---------------------------------------------------------
def send_rg_keep_alive(co_mp_q_out):
    db_msgType = db.DB_RG_ALIVE
    coInfo = []
    coInfo.append(db_msgType)

    if (gb.DIAG_LEVEL & gb.SEND_TO_DB):
        gb.logging.info("Sending %s(%d) via coordinator" %
                 (db.get_db_msg_str(db_msgType),db_msgType))
    co_mp_q_out.put(coInfo)

def rain_gauge(rq_in, co_mp_q_out):

    myname = gb.MP.current_process().name
    rg_pid = gb.os.getpid()
    gb.logging.info("Running %s process, PID: %d" % (myname, rg_pid))

    tm_str = gb.get_date_with_seconds(gb.get_localdate_str())
    cur_date = gb.datetime.now()
    current_day_of_month = cur_date.today().day - 1
    interval_end = cur_date
    gb.logging.info("%s: Rain Gauge: Day of month %d" %
                    (tm_str, current_day_of_month))

    RAIN_BUCKET_SIZE = 0.011

    SLEEP_INTERVAL = 0.05

    RAIN_REPORT_INTERVAL = 600   # seconds
    #RAIN_REPORT_INTERVAL = 60   # Testing

    dumped = True
    dump_count = 0
    
    rain_total = 0.0
    ten_minute_rain_total = 0.0
    ten_minute_dump_count = 0

    total_logged = False

    alive_counter = 0

    exit_process = False

    while(exit_process == False):
        try:
            msg = ""
            while (not rq_in.empty()):
                msg = rq_in.get()
                msgType = msg[0]
                if (gb.DIAG_LEVEL & gb.RAIN_MSG and
                    gb.DIAG_LEVEL & gb.RAIN_DETAIL):
                    gb.logging.info("%s(%d): Received %s(%d)" %
                        (myname, rg_pid, rg.get_rg_msg_str(msgType), msgType))

                if (msgType == rg.RG_EXIT):
                    gb.logging.info("%s(%d) Cleanup prior to exit" %
                                    (myname, rg_pid))
                    exit_process = True
                elif (msgType == rg.RG_GET_RAINFALL):
                    if (gb.DIAG_LEVEL & gb.RAIN_MSG):
                        gb.logging.info("%s(%d) Received %s(%d)" %
                            (myname, rg_pid, rg.get_rg_msg_str(msgType),
                             msgType))
                    send_rainfall(myname, rg_pid, co_mp_q_out, msg,
                                  ten_minute_dump_count, ten_minute_rain_total)
                else:
                    gb.logging.error("Invalid CO message type: %d" %
                        (msgType))
                    gb.logging.error(msg)

            if (exit_process == False):
                ##########################################
                # bucket dump occurred when pin is LOW
                ##########################################
                if gb.GPIO.input(gb.RAIN_GAUGE_GPIO):
                    if not dumped:
                        tm_str = gb.get_date_with_seconds(
                                                  gb.get_localdate_str())
                        dumped = True
                        dump_count = dump_count + 1
                        rain_total = rain_total + RAIN_BUCKET_SIZE
                        if (gb.DIAG_LEVEL & gb.RAIN_CNT):
                            gb.logging.info("%s: %s: dumped: %d in: %.3f" %
                                            (myname, tm_str, dump_count,
                                             rain_total))
                        total_logged = False
                # bucket not dumped (or released)
                else:
                    #if (dumped == True):
                    #    old_dump_count = dump_count
                    dumped = False

                ##########################################
                # Check for change in day every 10 minutes.  Rain total is
                # is reset to 0 when day switch occurs.
                ##########################################

                cur_date = gb.datetime.now()
                if (cur_date >= interval_end):
                    interval_end = cur_date + gb.timedelta(seconds=RAIN_REPORT_INTERVAL)
                    if (gb.DIAG_LEVEL & gb.RAIN):
                        gb.logging.info("Next rain report: %s" %
                                        (str(interval_end)))

                    #--------------------------------
                    # 10 minute counts are only updated once every
                    # ten minutes and are the values sent to the
                    # coordinator thread.  The 10 minute counts reset
                    # to 0 only when the day changes
                    #--------------------------------
                    ten_minute_dump_count = dump_count
                    ten_minute_rain_total = rain_total

                    #--------------------------------
                    # Reset rain total to 0.0 at start of new day
                    #--------------------------------
                    cur_day = cur_date.today().day
                    if (current_day_of_month != cur_day):
                        tm_str = gb.get_date_with_seconds(
                                                  gb.get_localdate_str())
                        gb.logging.info(
                            "%s: %s: change: today %d, yesterday %d" %
                            (tm_str, myname, cur_day, current_day_of_month))
                        current_day_of_month = cur_day
                        # reset rain total when new day detected
                        rain_total = 0.0
                        ten_minute_rain_total = 0.0
                        dump_count = 0
                        ten_minute_dump_count = 0
                        #old_dump_count = 0
                        dumped = False

                if alive_counter >= 600:
                    # Coordinator relays message to DB
                    send_rg_keep_alive(co_mp_q_out)
                    alive_counter = 0
                alive_counter += 1

                gb.time.sleep(SLEEP_INTERVAL)

        except KeyboardInterrupt:
            gb.logging.info("%s(%d) received keyboard interrupt" %
                            (myname, rg_pid))

    log_rain_total(rain_total)
    gb.logging.info("%s process exiting..." % (myname))
