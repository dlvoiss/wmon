import gb
import os

import wv
import co
import db

import signal
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

MAX_VOLTAGE = 5.336
MIN_VOLTAGE = 0.005

MAX_COUNT = 28456
MIN_COUNT = 28

MNT_VIEW_DECLINATION = -11.31

SOFT_GAIN_ADJUST = 347.7

HL_MAX = 9
R_HL_MAX = 60000
R_HL_MIN = -1
# Invalid(0), North(1), North-East(2), East(3), ... North-West(8)
R_VAL_L = [60000, 21578, 2576, 60000, 60000, 7960, 16542, 25920, 24348]
R_VAL_H = [-1, 21763, 2584, -1, -1, 7973, 16590, 26141, 24548]
HL_VARIANCE = 200
R_RANGE_FILE = "dir_resistor_ranges.txt"

###########################################################
# Wind Vane thread
###########################################################
class WindvaneThread(gb.threading.Thread):

    def __init__(self, group=None, target=None, name=None,
                args=(), kwargs=None, verbose=None):
        gb.threading.Thread.__init__(self, group=group, target=target,
                                     name=name)
        self.args = args
        self.kwargs = kwargs
        self.name = name
        self.kill_received = False

        return

    #---------------------------------------------------------
    # Send wind direction readings to coordinator thread
    #---------------------------------------------------------
    def send_direction(self, co_q_out, msg_in, resistor_volts, resistor_value,
                       resistor_wind_dir_str, hall_volts, hall_value,
                       hall_wind_dir_str, hall_wind_degrees, hall_mag_dir_str):

        # r_* is used for resistance based windvane
        # hall_* is used for hall effect (magfet) windvane
        req_id = msg_in[2]
        epoch_tm = msg_in[1]
        resistor_wind_dir_int = wv.wind_dir_str_to_int(resistor_wind_dir_str)
        msg = []
        msgType = co.CO_WIND_DIR
        msg.append(msgType)
        msg.append(epoch_tm)
        msg.append(req_id)
        msg.append(resistor_volts)
        msg.append(resistor_value)
        msg.append(resistor_wind_dir_int)  # wind dir magnetic str (8 point)
        msg.append(hall_volts)
        msg.append(hall_value)
        msg.append(hall_wind_degrees)      # wind degrees true
        msg.append(hall_wind_dir_str)      # wind dir true str (16 point)
        msg.append(hall_mag_dir_str)       # wind dir true str (16 point)
        if (gb.DIAG_LEVEL & gb.WIND_DIR_MSG):
            gb.logging.info("%s sending %s(%d)" %
                            (nm, co.get_co_msg_str(msgType), msgType))
        co_q_out.put(msg)

    #---------------------------------------------------------
    # Adjust for Mountain View CA magnetic declination
    #---------------------------------------------------------
    def adjust_declination(self, degrees):
        # Handle magnetic North declination
        true_dir = degrees + MNT_VIEW_DECLINATION
        if true_dir < 0.0:
            # When direction is slightly West of North (up to 11.24
            # degrees West of North), the true North reading is
            # negative.  While the value is correct, it is better
            # to keep this value within the positive 0-360 range
            true_dir = 360.0 + true_dir
        return true_dir

    #---------------------------------------------------------
    # Get direction string from magfet degree reading
    #---------------------------------------------------------
    def get_magfet_direction_str(self, degrees):

        N_min = 348.75
        N_max = 11.25
        range = 22.5

        dir = wv.NORTH

        if degrees > N_min or degrees <= N_max:
            dir = wv.NORTH
        elif degrees <= (N_max + (1 * range)):
            dir = wv.NNE
        elif degrees <= (N_max + (2 * range)):
            dir = wv.NORTH_EAST
        elif degrees <= (N_max + (3 * range)):
            dir = wv.ENE
        elif degrees <= (N_max + (4 * range)):
            dir = wv.EAST
        elif degrees <= (N_max + (5 * range)):
            dir = wv.ESE
        elif degrees <= (N_max + (6 * range)):
            dir = wv.SOUTH_EAST
        elif degrees <= (N_max + (7 * range)):
            dir = wv.SSE
        elif degrees <= (N_max + (8 * range)):
            dir = wv.SOUTH
        elif degrees <= (N_max + (9 * range)):
            dir = wv.SSW
        elif degrees <= (N_max + (10 * range)):
            dir = wv.SOUTH_WEST
        elif degrees <= (N_max + (11 * range)):
            dir = wv.WSW
        elif degrees <= (N_max + (12 * range)):
            dir = wv.WEST
        elif degrees <= (N_max + (13 * range)):
            dir = wv.WNW
        elif degrees <= (N_max + (14 * range)):
            dir = wv.NORTH_WEST
        elif degrees <= (N_max + (15 * range)):
            dir = wv.NNW

        return dir

    #---------------------------------------------------------
    # Get 8-point direction string for comparison
    # against resister windvane bearing
    #---------------------------------------------------------
    def get_8_point_direction_str(self, degrees):

        N8_min = 337.5
        N8_max = 22.5
        range8 = 45

        dir8 = wv.NORTH
        dir8_int = wv.INVALID

        if degrees > N8_min or degrees <= N8_max:
            dir8 = wv.NORTH
            dir8_int = 1
        elif degrees <= (N8_max + (1 * range8)):
            dir8 = wv.NORTH_EAST
            dir8_int = 2
        elif degrees <= (N8_max + (2 * range8)):
            dir8 = wv.EAST
            dir8_int = 3
        elif degrees <= (N8_max + (3 * range8)):
            dir8 = wv.SOUTH_EAST
            dir8_int = 4
        elif degrees <= (N8_max + (4 * range8)):
            dir8 = wv.SOUTH
            dir8_int = 5
        elif degrees <= (N8_max + (5 * range8)):
            dir8 = wv.SOUTH_WEST
            dir8_int = 6
        elif degrees <= (N8_max + (6 * range8)):
            dir8 = wv.WEST
            dir8_int = 7
        elif degrees <= (N8_max + (7 * range8)):
            dir8 = wv.NORTH_WEST
            dir8_int = 8

        return dir8, dir8_int

    #---------------------------------------------------------
    # Show the resistor value readings for each 8-point direction
    #---------------------------------------------------------
    def dump_hl(self, rlow, rhigh):

        global HL_MAX

        gb.logging.info("--- direction resistor value range ---")
        for ix in range(0, HL_MAX):
            dir_str = wv.wind_dir_int_to_str(ix)
            # dump data only if readings have been updated
            if rlow[ix] != R_HL_MAX or rhigh[ix] != R_HL_MIN:
                gb.logging.info("  **%s(%d) %d - %d" %
                                (dir_str, ix, rlow[ix], rhigh[ix]))

    #---------------------------------------------------------
    # Read in resistor value ranges for resistance-based
    # weathervane
    #---------------------------------------------------------
    def read_hl(self):

        global R_VAL_L
        global R_VAL_H
        global R_RANGE_FILE

        range_file = R_RANGE_FILE
        if (os.path.exists(R_RANGE_FILE)):
            file_o = open(range_file, 'r')
            data_str = file_o.read()

            lines = data_str.splitlines()
            # Remove and leading and trailing whitespace
            lines[0] = lines[0].replace("L: [", "")
            lines[1] = lines[1].replace("H: [", "")
            lines[0] = lines[0].replace("]", "")
            lines[1] = lines[1].replace("]", "")
            print("lines[0]:", lines[0])
            print("lines[1]:", lines[1])

            low = lines[0].split(',')
            high = lines[1].split(',')

            for ix in range(0,len(low)):
                R_VAL_L[ix] = int(low[ix])
                R_VAL_H[ix] = int(high[ix])

            file_o.close()

            self.dump_hl(R_VAL_L, R_VAL_H)
        else:
            gb.logging.error("Error reading %s" % (range_file))

    #---------------------------------------------------------
    # Read in resistor value ranges for resistance-based
    # weathervane
    #---------------------------------------------------------
    def store_hl(self, rlow, rhigh):

        global R_RANGE_FILE

        range_file = R_RANGE_FILE
        if gb.DIAG_LEVEL & gb.WIND_DIR_DETAIL:
            gb.logging.info("Updating %s..." % (range_file))
            self.dump_hl(rlow, rhigh)
        if (os.path.exists(R_RANGE_FILE)):
            file_o = open(range_file, 'w')
            file_o.write(f"L: {rlow}\n")
            file_o.write(f"H: {rhigh}\n")
            gb.logging.info("Wrote %s" % (range_file))
            file_o.close()

            #file_o = open(R_RANGE_FILE, 'r')
            #data_str = file_o.read()
            #lines = data_str.splitlines()

            # Remove and leading and trailing whitespace
            #lines[0] = lines[0].replace("L: [", "")
            #lines[1] = lines[1].replace("H: [", "")
            #lines[0] = lines[0].replace("]", "")
            #lines[1] = lines[1].replace("]", "")
            #print("lines[0]:", lines[0])
            #print("lines[1]:", lines[1])

            #low = lines[0].split(',')
            #high = lines[1].split(',')
            #dir_str = "test"
            #for ix in range(0,len(low)):
            #    gb.logging.info("  **%s(%d) %d - %d" %
            #                    (dir_str, ix, int(low[ix]), int(high[ix])))
        else:
            gb.logging.error("Error opening %s" % (range_file))

    #---------------------------------------------------------
    # Get magnetic resistor direction string based on ADS value
    #---------------------------------------------------------
    def get_r_magnetic_dir(self, r_value):

        global R_VAL_L
        global R_VAL_H

        if r_value >= R_VAL_L[1] and r_value < R_VAL_H[1]:
            wv_r_dir_str = wv.NORTH
        elif r_value >= R_VAL_L[2] and r_value < R_VAL_H[2]:
            wv_r_dir_str = wv.NORTH_EAST
        elif r_value >= R_VAL_L[3] and r_value < R_VAL_H[3]:
            wv_r_dir_str = wv.EAST
        elif r_value >= R_VAL_L[4] and r_value < R_VAL_H[4]:
            wv_r_dir_str = wv.SOUTH_EAST
        elif r_value >= R_VAL_L[5] and r_value < R_VAL_H[5]:
            wv_r_dir_str = wv.SOUTH
        elif r_value >= R_VAL_L[6] and r_value < R_VAL_H[6]:
            wv_r_dir_str = wv.SOUTH_WEST
        elif r_value >= R_VAL_L[7] and r_value < R_VAL_H[7]:
            wv_r_dir_str = wv.WEST
        elif r_value >= R_VAL_L[8] and r_value < R_VAL_H[8]:
            wv_r_dir_str = wv.NORTH_WEST
        else:
            wv_r_dir_str = "Invalid"

        return wv_r_dir_str

    #---------------------------------------------------------
    # Confirm hall sensor voltage is within expected range
    #---------------------------------------------------------
    def check_max_v(self, volts):

        global MAX_VOLTAGE

        new_max = False
        if volts > MAX_VOLTAGE and volts < 6.0:
            MAX_VOLTAGE = volts
            new_max = True

        return new_max

    #---------------------------------------------------------
    # Confirm hall sensor voltage is within expected range
    #---------------------------------------------------------
    def check_min_v(self, volts):

        global MIN_VOLTAGE

        new_min = False
        if volts < MIN_VOLTAGE and volts > 0.0:
            MIN_VOLTAGE = volts
            new_min = True

        return new_min

    #---------------------------------------------------------
    # Confirm hall sensor count is within expected range
    #---------------------------------------------------------
    def check_max_c(self, count):

        global MAX_COUNT

        new_max = False
        if count > MAX_COUNT and count < 35000:
            MAX_COUNT = count
            new_max = True

        return new_max

    #---------------------------------------------------------
    # Confirm hall sensor count is within expected range
    #---------------------------------------------------------
    def check_min_c(self, count):

        global MIN_COUNT

        new_min = False
        if count < MIN_COUNT and count >= 0:
            MIN_COUNT = count
            new_min = True

        return new_min

    #---------------------------------------------------------
    # Calculate hall sensor degrees / volt
    #---------------------------------------------------------
    def calc_step_v(self, min_volts, max_volts):

        # degrees/volt == 360.0 / voltage range

         range = max_volts - min_volts
         deg_step = range / 360.0

         #if gb.DIAG_LEVEL & gb.WV_RANGE:
         gb.logging.info(
                  "degrees/volt: %.3f MIN: %.3f v, MAX %.3f v, range: %.3f v" %
                  (deg_step, min_volts, max_volts, range))

         return deg_step

    #---------------------------------------------------------
    # Calculate hall sensor degrees / count
    #---------------------------------------------------------
    def calc_step_c(self, min_count, max_count):

        # degrees/count == 360.0 / counter range

         range = max_count - min_count
         deg_step = float(range) / 360.0

         #if gb.DIAG_LEVEL & gb.WV_RANGE:
         gb.logging.info("degrees/count: %.3f MIN: %d, MAX %d, range %d" %
                          (deg_step, min_count, max_count, range))

         return deg_step

    #---------------------------------------------------------
    # Use inverse if hall sensor shaft points downward
    #---------------------------------------------------------
    def adjust_shaft_down(self, dir):
        if dir > 180.0:
            dir = 180.0 - (dir - 180.0)
        elif dir < 180.0:
            dir = 180.0 + (180.0 - dir)
        return dir

    #---------------------------------------------------------
    # Voltage corresponds to inverse direction if hall sensor shaft
    # points downward i.e., 270 degrees is due East, 90 degrees is
    # due West 180 degrees is still South and 0 degrees is North
    #---------------------------------------------------------
    def calc_dir_v(self, volts, min_v, max_v):
        # degrees/volt == 360.0 / voltage range
        # degrees = volts * degrees/volt
        dir = (volts * 360.0) / (max_v - min_v)
        dir_in_degrees = self.adjust_shaft_down(dir)
        return dir_in_degrees

    #---------------------------------------------------------
    # Count corresponds to inverse direction if hall sensor
    # shaft points downward
    #---------------------------------------------------------
    def calc_dir_c(self, count, min_c, max_c):
        # degrees/count == 360.0 / counter range
        # degrees = count * degrees/count
        dir = (float(count) * 360.0) / (float(max_c) - float(min_c))
        dir_in_degrees = self.adjust_shaft_down(dir)
        return dir_in_degrees

    #---------------------------------------------------------
    # Process magfet (hall sensor) readings from ADS1115
    #---------------------------------------------------------
    def get_degrees(self, volts, raw):

        if self.check_min_v(volts) or self.check_max_v(volts):
            degree_step = self.calc_step_v(MIN_VOLTAGE, MAX_VOLTAGE)
        if self.check_min_c(raw) or self.check_max_c(raw):
            count_step = self.calc_step_c(MIN_COUNT, MAX_COUNT)

        direction_v = self.calc_dir_v(volts, MIN_VOLTAGE, MAX_VOLTAGE)
        direction_v = round(direction_v + 0.05, 1)

        direction_c = self.calc_dir_c(raw, MIN_COUNT, MAX_COUNT)
        direction_c = round(direction_c + 0.05, 1)

        return direction_v, direction_c

    #---------------------------------------------------------
    # Send keep-alive (I am alive) message to DB via Coordinator
    #---------------------------------------------------------
    def send_wv_keep_alive(self, co_q_out):
        db_msgType = db.DB_WV_ALIVE
        coInfo = []
        coInfo.append(db_msgType)

        if (gb.DIAG_LEVEL & gb.SEND_TO_DB):
            gb.logging.info("Sending %s(%d) via Coordinator" %
                     (db.get_db_msg_str(db_msgType),db_msgType))
        co_q_out.put(coInfo)

    ###########################################################
    # Wind Vane thread run loop
    ###########################################################
    def run(self):

        global R_VAL_L
        global R_VAL_H

        gb.logging.info("Running %s thread" % (self.name))
        if (gb.DIAG_LEVEL & gb.WIND_DIR_DETAIL):
            gb.logging.info(self.args)

        wv_q_in = self.args[0]
        co_q_out = self.args[1]
        end_event = self.args[2]

        # Get stored value ranges for resistor based weathervane
        self.read_hl()
        # store_hl at this line is only used for testing reading
        # and writing the dir_resistor_range.txt file.  store_hl
        # is used and needed later in this function
        #self.store_hl(R_VAL_L, R_VAL_H)

        # ADS115 is 16-bit ADC
        i2c = busio.I2C(board.SCL, board.SDA)
        # Create the ADS object and specify the gain
        ads = ADS.ADS1115(i2c)
        # ADS gain
        # Gain can change based on the voltage signal - Gain of 1
        # is typically enough for a many sensors, but range
        # is limited to 0-4.xv
        #  - Gain of 1 results in max voltage of 4.0x and about
        #    1/4 of the hall effect sensor rotation pegs at 4.096v
        #  - Need to use 2/3 gain to get full 0-5v (0-6.xv) range
        #    and a varying voltage through all 360 degrees
        #ads.gain = 1
        ads.gain = 2.0/3.0

        chan0 = AnalogIn(ads, ADS.P0)  # Windvane direction
        chan1 = AnalogIn(ads, ADS.P1)  # Magfet windvane direction
        chan2 = AnalogIn(ads, ADS.P2)  # Unused
        chan3 = AnalogIn(ads, ADS.P3)  # Unused
        gb.logging.info("ADS1115 (i2c) initialized")

        magfet_dir_str = ""
        dir8 = ""

        alive_counter = 0

        degree_step = self.calc_step_v(MIN_VOLTAGE, MAX_VOLTAGE)
        count_step = self.calc_step_c(MIN_COUNT, MAX_COUNT)

        wv_r_volts = 0.0
        wv_r_value = 0

        wv_hall_volts = 0.0
        wv_hall_value = 0
        true_magfet_degrees = 0.0

        logging_time_next = gb.datetime.now()

        updated = False

        while not end_event.isSet():
            wv_data = ""
            while (not wv_q_in.empty()):
                msg = wv_q_in.get()
                msgType = msg[0]
                if ((gb.DIAG_LEVEL & gb.WIND_DIR_MSG) and
                    (gb.DIAG_LEVEL & gb.WIND_DIR_DETAIL)):
                    gb.logging.info("%s: Received %s(%d)" %
                            (self.name, wv.get_wv_msg_str(msgType), msgType))

                if (msgType == wv.WV_EXIT):
                    gb.logging.info("%s: Cleanup prior to exit" % (self.name))

                elif (msgType == wv.WV_GET_DIRECTION):
                    if (gb.DIAG_LEVEL & gb.WIND_DIR_MSG):
                        gb.logging.info("%s: Received %s(%d)" %
                            (self.name, wv.get_wv_msg_str(msgType), msgType))
                    self.send_direction(co_q_out, msg,
                                        wv_r_volts, wv_r_value,
                                        wv_r_dir_str,
                                        wv_hall_volts, wv_hall_value,
                                        magfet_dir_str, true_magfet_degrees,
                                        dir8)

                else:
                    gb.logging.error("Invalid WD message type: %d" % (msgType))
                    gb.logging.error(msg)

                gb.time.sleep(0.1)

            #----------------------------------------
            # chan0 is resistor-based weather vane
            #----------------------------------------
            wv_r_volts = chan0.voltage
            wv_r_value = chan0.value
            #----------------------------------------
            # chan1 is hall sensor (magfet) weather vane
            #----------------------------------------
            wv_hall_volts = chan1.voltage
            wv_hall_value = chan1.value

            wv_r_dir_str = ""
            wv_r_dir_str2 = ""

            #----------------------------------------
            # Get hall sensor (magfet) wind direction
            #----------------------------------------
            degrees_v, degrees_c = self.get_degrees(wv_hall_volts, wv_hall_value)
            # Apply software gain to bring direction up to 360 degrees
            degree_gain = degrees_v * 360.0/SOFT_GAIN_ADJUST
            if degree_gain >= 360.0:
                degree_gain = degree_gain - 360.0
            true_magfet_degrees = self.adjust_declination(degree_gain)
            magfet_dir_str = self.get_magfet_direction_str(
                                                      true_magfet_degrees)

            if (gb.DIAG_LEVEL & gb.WIND_DIR_DETAIL):
                gb.logging.info("wv1 voltage: %.3f, wv1 value %d" %
                                (wv_hall_volts, wv_hall_value))
                gb.logging.info("degrees_v: %.1f, degrees_c %.1f "
                                "degree_gain %.1f" %
                                (degrees_v, degrees_c, degree_gain))
                gb.logging.info("degrees true: %.1f, dir %s" %
                                (true_magfet_degrees, magfet_dir_str))

            #----------------------------------------
            # Determine magnetic 8-point direction for comparison
            # to resistor windvane direction
            #----------------------------------------

            # Get 8-point direction using magfet reading before
            # declination adjustment (i.e., magnetic reading)
            dir8, dir8_int = self.get_8_point_direction_str(degree_gain)

            #----------------------------------------
            # Find/update min/max resistor windvane counts for each
            # 8-point direction. Minimize maximum allowed changed
            # when setting high or low
            #----------------------------------------
            tm_str = gb.get_date_with_seconds(gb.get_localdate_str())
            if R_VAL_L[dir8_int] == R_HL_MAX:
                R_VAL_L[dir8_int] = wv_r_value
                updated = True
                gb.logging.info("%s: %s(%d) low: %d" %
                                (tm_str, dir8, dir8_int, wv_r_value))

            if R_VAL_H[dir8_int] == R_HL_MIN:
                R_VAL_H[dir8_int] = wv_r_value
                updated = True
                gb.logging.info("%s: %s(%d) high: %d" %
                                (tm_str, dir8, dir8_int, wv_r_value))

            if R_VAL_L[dir8_int] == R_HL_MAX or \
                (wv_r_value < R_VAL_L[dir8_int] and \
                wv_r_value > (R_VAL_L[dir8_int] - HL_VARIANCE)):

                R_VAL_L[dir8_int] = wv_r_value
                updated = True
                gb.logging.info("%s: %s(%d) low: %d" %
                                (tm_str, dir8, dir8_int, wv_r_value))

            elif R_VAL_H[dir8_int] == R_HL_MIN or \
                (wv_r_value > R_VAL_H[dir8_int] and \
                wv_r_value < (R_VAL_H[dir8_int] + HL_VARIANCE)):

                R_VAL_H[dir8_int] = wv_r_value
                updated = True
                gb.logging.info("%s: %s(%d) high: %d" %
                                (tm_str, dir8, dir8_int, wv_r_value))
            if updated:
                self.dump_hl(R_VAL_L, R_VAL_H)
                self.store_hl(R_VAL_L, R_VAL_H)
                updated = False

            wv_r_dir_str = self.get_r_magnetic_dir(wv_r_value)

            #gb.logging.info("Wind Dir: %s %s %5d %.5f" %
            #                 (wv_r_dir_str, wv_r_dir_str2,
            #                  wv_r_value, wv_r_volts))
            #gb.time.sleep(5)  # one-second in non-debug

            if (gb.DIAG_LEVEL & gb.WIND_DIR_DETAIL):
                gb.logging.info("Wind Dir: %s %s %5d %.5f" %
                             (wv_r_dir_str, wv_r_dir_str2,
                              wv_r_value, wv_r_volts))
            elif (gb.DIAG_LEVEL & gb.WIND_DIR):
                gb.logging.info("Wind Dir: %s %s" %
                                (wv_r_dir_str, wv_r_dir_str2))

            if alive_counter >= 30:
                self.send_wv_keep_alive(co_q_out)
                alive_counter = 0
            alive_counter += 1

            if (gb.DIAG_LEVEL & gb.WIND_DIR_DETAIL):
                gb.time.sleep(5)
            else:
                gb.time.sleep(1)

        gb.logging.info("Exiting thread %s" % (self.name))
        return
