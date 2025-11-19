import gb
import db
import fan

DFLT_FAN_ON_THRESHOLD = 55.0
DFLT_FAN_OFF_THRESHOLD = 45.0

#######################################################################
#
# CPU Fan Thread
#
#######################################################################
class CPUFanControlThread(gb.threading.Thread):

    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        gb.threading.Thread.__init__(self, group=group, target=target, name=name)
        gb.logging.info("Setting up CPU Fan Control thread")
        self.args = args
        self.kwargs = kwargs
        self.name = name
        self.db_conn = 0
        self.db_cursor = 0

   #####################################
   # Get CPU temperature -- fan turns on when CPU temp reaches upper
   # threshold and turns off when CPU temperature subsequently drops
   # below lower threshold
   #####################################
    def get_cpu_temp(self):
        cpu_temp_str = gb.os.popen("vcgencmd measure_temp").readline()
        gb.logging.debug("%s" % (cpu_temp_str))
        temp_cpu_str = cpu_temp_str.replace("\n", "")
        return temp_cpu_str.replace("temp=", "")

   #####################################
   # Update fan-on and fan-off temeperature threshold
   #####################################
    def fan_update_fan_thresholds(self, fan_data):

        fan_thresh = [0.0] * 2
        fan_thresh[0] = fan_data[1]
        fan_thresh[0] = fan_data[2]

        return fan_thresh

    #---------------------------------------------------------
    # Send keep-alive (I am alive) message to DB
    #---------------------------------------------------------
    def send_fan_keep_alive(self, db_q_out):
        db_msgType = db.DB_FAN_ALIVE
        dbInfo = []
        dbInfo.append(db_msgType)

        if (gb.DIAG_LEVEL & gb.SEND_TO_DB):
            gb.logging.info("Sending %s(%d)" %
                     (db.get_db_msg_str(db_msgType),db_msgType))
        db_q_out.put(dbInfo)

    #############################################################
    # CPU Fan run function
    #############################################################
    def run(self):
        global DB_SELECT

        cpufan_q_in = self.args[0]
        db_q_out = self.args[1]
        end_event = self.args[2]

        gb.logging.info("Running %s" % (self.name))
        gb.logging.debug(self.args)

        FAN_SLEEP_INTERVAL = 10  # (seconds)
        iter = 0

        alive_counter = 0

        # Turn fan Fan on at or above this temp (Celcius)
        fan_on_threshold = DFLT_FAN_ON_THRESHOLD
        #fan_on_threshold = 43  # Fan on test setting

        # Turn Fan offl at or below this temp (Celcius)
        fan_off_threshold = DFLT_FAN_OFF_THRESHOLD
        #fan_off_threshold = 41 # Fan off test setting

        # Get initial CPU fan state based on GPIO pin
        gb.GPIO.output(gb.FAN_PIN, gb.GPIO.LOW)  # FAN off
        if gb.GPIO.input(gb.FAN_PIN):
            fan_state = "ON"
        else:
            fan_state = "OFF"
        gb.logging.info("CPU Fan State (GPIO): %s" % (fan_state))

        tm_str = gb.get_date_with_seconds(gb.get_localdate_str())

        # Set initial fan state in database to GPIO reported state
        dbInfo = []
        db_msgType = db.DB_CPU_FAN
        dbInfo.append(db_msgType)
        dbInfo.append(tm_str)
        dbInfo.append(fan_state)
        gb.logging.debug("Sending DB_CPU_FAN state")
        db_q_out.put(dbInfo)

        gb.logging.info("CPU Fan ON Threshold: %.1f C" % (fan_on_threshold))
        gb.logging.info("CPU Fan OFF Threshold: %.1f C" % (fan_off_threshold))

        temp_max = 0.0
        cpu_temp_max_str = ""
        cputempc_prior = gb.PRIOR_TEMP_DFLT
        temperature_diff = fan.FAN_TEMPERATURE_DIFF

        ###################################################
        # CPU Fan main loop: Part 1: INCOMING MESSAGES
        ###################################################
        while not end_event.isSet():

            cpu_temp_str = self.get_cpu_temp()
            temp_s = cpu_temp_str.split('\'')[0]
            temp = float(temp_s)

            if gb.GPIO.input(gb.FAN_PIN):
                fanstate = "ON"
            else:
                fanstate = "OFF"

            ##################################################
            # Report CPU temeperature and fanstate if temperature
            # differs by more than +/- temperature_diff degrees C
            ##################################################
            if (temp < (cputempc_prior - temperature_diff) or
                temp > (cputempc_prior + temperature_diff)):
                if (gb.DIAG_LEVEL & 0x100):
                    gb.logging.info("%s: CPU TEMPERATURE: %s: GPIO %d/FAN: %s" %
                                    (tm_str, cpu_temp_str,gb.FAN_PIN,fanstate))
                dbInfo = []
                db_msgType = db.DB_CPU_TEMPERATURE
                dbInfo.append(db_msgType)
                dbInfo.append(tm_str)
                dbInfo.append(temp)
                dbInfo.append(fanstate)
                if (gb.DIAG_LEVEL & 0x100):
                    gb.logging.info("Sending DB_CPU_TEMPERATURE")
                db_q_out.put(dbInfo)

                cputempc_prior = temp
            ##################################################
            # (Check) Turn FAN ON
            # Start the fan if the temperature has reached the threshold
            # and the fan isn't already running.
            ##################################################

            tm_str = gb.get_date_with_seconds(gb.get_localdate_str())
            if temp > fan_on_threshold:
                if not gb.GPIO.input(gb.FAN_PIN):  # Turn on only if not running
                    temp_max = temp
                    gb.logging.info("%s: CPU temperature: %s" % (tm_str,cpu_temp_str))
                    gb.GPIO.output(gb.FAN_PIN, gb.GPIO.HIGH)  # FAN on
                    gb.logging.info("%s: CPU Fan ON: %d" % (tm_str,gb.GPIO.input(gb.FAN_PIN)))

                    # Send msg to DatabaseThread
                    dbInfo = []
                    db_msgType = db.DB_CPU_FAN
                    dbInfo.append(db_msgType)
                    dbInfo.append(tm_str)
                    dbInfo.append(fan_state)
                    if (gb.DIAG_LEVEL & 0x100):
                        gb.logging.debug("Sending DB_CPU_FAN state ON")
                    db_q_out.put(dbInfo)

                if temp > temp_max:
                    cpu_temp_max_str = cpu_temp_str

            ##################################################
            # (Check) Turn FAN OFF
            # Stop the fan if the fan is running and the temperature
            # has dropped below fan-off threshold.
            ##################################################

            elif temp < fan_off_threshold:
                if gb.GPIO.input(gb.FAN_PIN): # turn off only if running
                    gb.logging.info("%s: CPU temperature: %s" % (tm_str,cpu_temp_str))
                    gb.logging.info("%s: CPU MAX temperature: %s" % (tm_str,cpu_temp_max_str))
                    gb.GPIO.output(gb.FAN_PIN, gb.GPIO.LOW)  # FAN off
                    gb.logging.info("%s: CPU Fan OFF: %d" % (tm_str,gb.GPIO.input(gb.FAN_PIN)))
                    # Send msg to DatabaseThread
                    dbInfo = []
                    db_msgType = db.DB_CPU_FAN
                    dbInfo.append(db_msgType)
                    dbInfo.append(tm_str)
                    dbInfo.append(fan_state)
                    if (gb.DIAG_LEVEL & 0x100):
                        gb.logging.debug("Sending DB_CPU_FAN state OFF")
                    db_q_out.put(dbInfo)

            #gb.logging.info("DB Part 1: Check for incoming DB msgs")

            while not cpufan_q_in.empty():

                cpufan_data = cpufan_q_in.get()
                cpufan_msgType = cpufan_data[0]

                gb.logging.debug(cpufan_data)

                    #if (fan_msgType == gb.FAN_THRESH):
                    #    fan_thresh = self.fan_update_fan_thresholds(db_data)
                    #    fan_on_threshold = fan_thresh[0]
                    #    fan_off_threshold = fan_thresh[1]

                    #else:
                    #    gb.logging.error("Invalid Fan message type: %d" %
                    #                                          (fan_msgType))
                    #    gb.logging.error(fan_data)

                gb.time.sleep(1)

            if alive_counter >= 3:
                self.send_fan_keep_alive(db_q_out)
                alive_counter = 0
            alive_counter += 1

            gb.time.sleep(FAN_SLEEP_INTERVAL)

        gb.logging.info("Exiting %s" % (self.name))
