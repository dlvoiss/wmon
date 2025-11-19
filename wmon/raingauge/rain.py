import gb

import signal

end_script = False

######################################
# GPIO Pins
######################################
RAIN_GAUGE_GPIO = 26

##############################################
# Setup
##############################################
def setup():
    tm_str = gb.get_date_with_seconds(gb.get_localdate_str())
    gb.logging.info("DIAG_LEVEL 0x%x" % (gb.DIAG_LEVEL))
    gb.logging.info("Setting up: %s" % (tm_str))
    gb.GPIO.setmode(gb.GPIO.BCM)
    gb.GPIO.setup(RAIN_GAUGE_GPIO, gb.GPIO.IN)

##############################################
# Destroy
##############################################
def destroy():
    print("Cleaning up")
    gb.GPIO.cleanup()

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

    dumped = True
    dump_count = 0
    rain_total = 0.0
    RAIN_BUCKET_SIZE = 0.011

    try:

        while (end_script == False):
            ##########################################
            # bucket dump occurred when pin is LOW
            ##########################################
            #if not gb.GPIO.input(RAIN_GAUGE_GPIO):
            if gb.GPIO.input(RAIN_GAUGE_GPIO):
                if not dumped:
                    tm_str = gb.get_date_with_seconds(
                                              gb.get_localdate_str())
                    dumped = True
                    dump_count = dump_count + 1
                    gb.logging.info("%s: bucket dumped: %d" %
                                    (tm_str, dump_count))
                    rain_total = rain_total + RAIN_BUCKET_SIZE
            # bucket not dumped (or released)
            else:
                dumped = False

            gb.time.sleep(0.05)

    except KeyboardInterrupt:
        tm_str = gb.get_date_with_seconds(gb.get_localdate_str())
        gb.logging.info("%s: Keyboard Interrrupt, stopping script" % (tm_str))
        end_script = True

    gb.logging.info("dump_count: %d; rain_total %0.2f" %
                    (dump_count, rain_total))
    tm_str = gb.get_date_with_seconds(gb.get_localdate_str())
    gb.time.sleep(1)
    destroy()
    gb.logging.info("%s: MAIN EXIT" % (tm_str))
