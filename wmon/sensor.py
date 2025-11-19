import gb

import smbus2
import board

import bme280
import adafruit_dht

import snsr
import db
import wthr
import wthr30
import wavg

# The SensorThread reads data from the BME280 and DHT-22 sensors
# and then publishes the readings to other threads.  The
# SensorThread also does some data conversion (Centrigrade
# to Farenheith, etc.) and also validates readings obtained
# from the two sensors

COLUMBIA_DR_ALTITUDE_FT = 136    # Feet above sea level at Columbia Dr.
COLUMBIA_DR_ALTITUDE_M = 41.4528 # Meters above sea level at Columbia Dr.

hPa_per_meter = 0.12677457
hPa_per_foot = 0.038640888

#######################################################################
#
# Sensor Thread
# Read BME280 and DHT-22 weather sensors (temperature, humidity and pressure)
#
#######################################################################
class SensorThread(gb.threading.Thread):

    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        gb.threading.Thread.__init__(self, group=group, target=target, name=name)
        self.args = args
        self.kwargs = kwargs
        self.name = name
        self.kill_received = False

        self.need_current_month = True
        self.current_month = 0
        self.db_next_write = gb.datetime.now()

    def get_F_from_C(self, tempC):
        # F = C * 9/5 + 32
        # 9/5 = 1.8
        tempF = (tempC * 1.8) + 32
        return tempF

    def get_kPa(self, hPa):
        kPa = hPa / 10
        return kPa

    def get_Pa(self, hPa):
        Pa = hPa * 100
        return Pa

    def get_inHg(self, hPa):
        inHg = 0.0295300 * hPa
        return inHg

    def get_mmHg(self, hPa):
        mmHg = (7.50062 * hPa)/10
        return mmHg

    def get_psi(self, hPa):
        psi = 0.0145038 * hPa
        return psi

    def get_atm(self, hPa, local_pressure):
        atm = hPa / local_pressure
        return atm

    #----------------------------------
    # pressure reading in hPa, altitude in meters
    #----------------------------------
    def get_adjusted_sea_level(self, hPa, alt):
        hPa_adjust = alt * hPa_per_meter
        gb.logging.debug("Meters: %.2f, hPa Adjustment: %.2f" % (alt, hPa_adjust))
        sea_level = hPa + hPa_adjust
        return(sea_level)

    #----------------------------------
    # pressure reading in hPa, altitude in feet
    #----------------------------------
    def get_ft_adjusted_sea_level(self, hPa, alt):
        hPa_adjust = alt * hPa_per_foot
        gb.logging.debug("Feet: %.2f, hPa Adjustment: %.2f" % (alt, hPa_adjust))
        sea_level = hPa + hPa_adjust
        return(sea_level)

    #----------------------------------
    # hPa in x feet
    #----------------------------------
    def get_hpa_from_feet(self, feet):
        hPa_adjust = feet * hPa_per_foot
        return(hPa_adjust)

    def validate_temperatureF(self, tempF): 
        if tempF < 0.0 or tempF > 120.0:
            return False
        return True

    def validate_pressure_mB(self, pressure):
        if pressure < 970.0 or pressure > 1040.0:
            return False
        return True

    def validate_humidity_pct(self, humidity):
        if humidity < 0.0 or humidity > 100.0:
            return False
        return True

    #----------------------------------
    # Data sent to DB and weather_avg thread every 3 minutes
    # Calculate/set time after next write should occur
    #----------------------------------
    def db_send_time(self, tm_val):
        write_to_db = False
        if tm_val > self.db_next_write:
            write_to_db = True
            self.db_next_write = tm_val + gb.timedelta(minutes=3)
            if (gb.DIAG_LEVEL & gb.SEND_TO_DB):
                gb.logging.info("tm_val: %s, db_next_write: %s" %
                        (gb.cvt_datetime_to_str(tm_val),
                         gb.cvt_datetime_to_str(self.db_next_write)))
        return write_to_db

    #----------------------------------
    # Send sensor data to DB and other threads
    #----------------------------------
    def publish_sensor_data(self, db_q_out, wthr_q_out,
                            wthr30_q_out, wavg_q_out,
                            tm_val, tempF_B,
                            tempC_B, tempF_D, tempC_D,
                            pressure_hPa, sea_level_hPa, columbia_dr_variance,
                            sea_level_inHg, sea_level_mmHg, sea_level_psi,
                            humidity_D):

        if self.db_send_time(tm_val):
            combo_temp = tempF_D
            db_msgType = db.DB_LOCAL_STATS
            dbInfo = []
            dbInfo.append(db_msgType)
            dbInfo.append(str(tm_val))
            dbInfo.append(pressure_hPa)          # hPa/mB
            dbInfo.append(sea_level_inHg)        # inches Hg
            dbInfo.append(sea_level_mmHg)        # mm Hg
            dbInfo.append(sea_level_psi)         # psi
            dbInfo.append(sea_level_hPa)         # hPa/mB
            dbInfo.append(columbia_dr_variance)  # hPa/mB
            dbInfo.append(tempF_B)
            dbInfo.append(tempC_B)
            dbInfo.append(tempF_D)
            dbInfo.append(tempC_D)
            dbInfo.append(humidity_D)
            dbInfo.append(combo_temp)
            if (gb.DIAG_LEVEL & gb.SEND_TO_DB):
                gb.logging.info("Sending %s(%d)" %
                         (db.get_db_msg_str(db_msgType),db_msgType))
            db_q_out.put(dbInfo)

            gb.time.sleep(1)

            wavg_msgType = wavg.WAVG_SENSOR_DATA
            wthrInfo = []
            wthrInfo.append(wavg_msgType)
            wthrInfo.append(tm_val)
            wthrInfo.append(tempF_B)
            wthrInfo.append(tempC_B)
            wthrInfo.append(tempF_D)
            wthrInfo.append(tempC_D)
            wthrInfo.append(pressure_hPa)
            wthrInfo.append(sea_level_hPa)
            wthrInfo.append(columbia_dr_variance)
            wthrInfo.append(humidity_D)
            if gb.DIAG_LEVEL & gb.SENSOR_SND:
                gb.logging.info("Sending %s(%d)" %
                                (wavg.get_wavg_msg_str(wavg_msgType),
                                 wavg_msgType))
            wavg_q_out.put(wthrInfo)

        wthr_msgType = wthr.WTHR_SENSOR_DATA
        wthrInfo = []
        wthrInfo.append(wthr_msgType)
        wthrInfo.append(tm_val)
        wthrInfo.append(tempF_B)
        wthrInfo.append(tempC_B)
        wthrInfo.append(tempF_D)
        wthrInfo.append(tempC_D)
        wthrInfo.append(pressure_hPa)
        wthrInfo.append(sea_level_hPa)
        wthrInfo.append(columbia_dr_variance)
        wthrInfo.append(humidity_D)
        if gb.DIAG_LEVEL & gb.SENSOR_SND:
            gb.logging.info("Sending %s(%d)" %
                            (wthr.get_wthr_msg_str(wthr_msgType),wthr_msgType))
        wthr_q_out.put(wthrInfo)

        gb.time.sleep(1)

        wthr30_msgType = wthr30.WTHR30_SENSOR_DATA
        wthrInfo = []
        wthrInfo.append(wthr30_msgType)
        wthrInfo.append(tm_val)
        wthrInfo.append(tempF_B)
        wthrInfo.append(tempC_B)
        wthrInfo.append(tempF_D)
        wthrInfo.append(tempC_D)
        wthrInfo.append(pressure_hPa)
        wthrInfo.append(sea_level_hPa)
        wthrInfo.append(columbia_dr_variance)
        wthrInfo.append(humidity_D)
        if gb.DIAG_LEVEL & gb.SENSOR_SND:
            gb.logging.info("Sending %s(%d)" %
                            (wthr30.get_wthr30_msg_str(wthr30_msgType),
                             wthr30_msgType))
        wthr30_q_out.put(wthrInfo)

        gb.time.sleep(1)

    #---------------------------------------------------------
    # Send keep-alive (I am alive) message to DB
    #---------------------------------------------------------
    def send_snsr_keep_alive(self, db_q_out):
        db_msgType = db.DB_SNSR_ALIVE
        dbInfo = []
        dbInfo.append(db_msgType)

        if (gb.DIAG_LEVEL & gb.SEND_TO_DB):
            gb.logging.info("Sending %s(%d)" %
                     (db.get_db_msg_str(db_msgType),db_msgType))
        db_q_out.put(dbInfo)

    ####################################################################
    # SensorThread run function
    ####################################################################
    def run(self):

        sensor_q_in = self.args[0]
        db_q_out = self.args[1]
        wthr_q_out = self.args[2]
        wthr30_q_out = self.args[3]
        wavg_q_out = self.args[4]
        end_event = self.args[5]

        gb.logging.info("Running %s" % (self.name))

        # I2C bus and address
        port = 1  # For Raspberry Pi 2/3/4, use 1. For older models, use 0.
        address = 0x76  # Default I2C address for BME280

        # Initial the dht device, with data pin connected to:
        dhtSensor = adafruit_dht.DHT22(board.D25)

        # Initialize I2C bus
        bus = smbus2.SMBus(port)

        ARR_SZ = 10
        C_DHT = [0.0] * ARR_SZ
        C_BME = [0.0] * ARR_SZ
        ix = 0

        alive_counter = 0

        # Load calibration parameters from the sensor
        calibration_params = bme280.load_calibration_params(bus, address)

        try:
            while not end_event.isSet():
                #--------------------------------------
                # Check for incoming sensor messages
                #--------------------------------------
                while not sensor_q_in.empty():
                    sensor_data = sensor_q_in.get()
                    sensor_msgType = sensor_data[0]

                    if gb.DIAG_LEVEL & gb.SENSOR_RCV:
                        gb.logging.info("Recvd: %s(%d)" %
                                        snsr.get_snsr_msg_str(sensor_msgType),
                                        sensor_msgType)

                    if sensor_msgType == snsr.SNSR_EXIT:
                        # Shutdown likely occurs before this message
                        # has a chance to get processed
                        gb.logging.info("Cleaning up before EXIT")
                    else:
                        gb.logging.error("Invalid sensor message type: %d" %
                                         (sensor_msgType))
                        gb.logging.error(sensor_data)

                #--------------------------------------
                # Get sensor readings
                #--------------------------------------
                # NOTE: hPa (hecto Pascals) is same as mB (milliBars)

                tempC_BME = 0.0
                tempF_BME = 0.0
                pressure_BME_hPa = 0.0
                tempC_DHT = 0.0
                tempF_DHT = 0.0
                humidity_DHT = 0.0

                tm_str = gb.get_date_with_seconds(gb.get_localdate_str())
                tm_val = gb.datetime.now()
        
                # Take a single reading and return a compensated_reading object
                bmeData = bme280.sample(bus, address, calibration_params)

                # Extract and print sensor data
                #print(bmeData)
                tempC_BME = bmeData.temperature
                tempF_BME = self.get_F_from_C(tempC_BME)
                pressure_BME_hPa = bmeData.pressure
                # bmeData.humidity not supported by BME
                #humidity_percent = bmeData.humidity


                # Adjust pressure to sea level
                sea_level_hPa = self.get_ft_adjusted_sea_level(
                                    pressure_BME_hPa, COLUMBIA_DR_ALTITUDE_FT)
                sea_level_m = self.get_adjusted_sea_level(
                                    pressure_BME_hPa, COLUMBIA_DR_ALTITUDE_M)
                hPa_inHg = self.get_inHg(pressure_BME_hPa)
                sl_inHg = self.get_inHg(sea_level_hPa)
                columbia_dr_variance_hPa = sea_level_hPa - pressure_BME_hPa


                # Also get PSI and mmHg
                sl_mmHg = self.get_mmHg(sea_level_hPa)
                sl_psi = self.get_psi(sea_level_hPa)

                if gb.DIAG_LEVEL & gb.SENSOR_BME:
                    gb.logging.info(
                            "%s: BME Temp: %.1f F, BME Pressure %.1f mB" %
                            (str(tm_val), tempF_BME, pressure_BME_hPa))
                    gb.logging.info(
                            "%s: Sea Level Adjusted: %.1f mB / %.1f mB" %
                            (str(tm_val), sea_level_hPa, sea_level_m))
                    gb.logging.info(
                            "%s: pressure: %.3f inHg, sea level: %.3f inHg, variance: %1f mB" %
                            (str(tm_val), hPa_inHg, sl_inHg,
                             columbia_dr_variance_hPa))

                try:
                    tempC_DHT = dhtSensor.temperature
                    tempF_DHT = self.get_F_from_C(tempC_DHT)
                    humidity_DHT = dhtSensor.humidity
                    if gb.DIAG_LEVEL & gb.SENSOR_DHT:
                        gb.logging.info(
                            "%s: DHT Temp: %.1f F, DHT Humidity %.1f%%" %
                            (str(tm_val), tempF_D, humidity_D))

                except RuntimeError as error:
                    # Errors happen fairly often, DHT's are hard
                    # to read, just keep going
                    gb.logging.debug("ERROR: %s" % (error))
                    gb.time.sleep(snsr.SENSOR_SLEEPTIME)
                    continue

                except Exception as error:
                    gb.logging.error("DHT ERROR: %s" % (e))
                    dhtSensor.exit()
                    raise error

                # Confirm readings are valid
                err = False
                if not self.validate_temperatureF(tempF_DHT):
                    gb.logging.error("DHT Temperature range ERROR: %.1f F" %
                                     (tempF_DHT))
                    err = True

                if not self.validate_temperatureF(tempF_BME):
                    gb.logging.error("BME Temperature range ERROR: %.1f F" %
                                     (tempF_BME))
                    err = True

                if not self.validate_pressure_mB(pressure_BME_hPa):
                    gb.logging.error("BME Pressure range ERROR: %.1f mB" %
                                     (pressure_BME_hPa))
                    err = True

                if not self.validate_humidity_pct(humidity_DHT):
                    gb.logging.error("DHT Humidity range ERROR: %.1f mB" %
                                     (humidity_DHT))
                    err = True
                if not err:
                    self.publish_sensor_data(db_q_out, wthr_q_out, wthr30_q_out,
                                             wavg_q_out, tm_val,
                                             tempF_BME, tempC_BME,
                                             tempF_DHT, tempC_DHT,
                                             pressure_BME_hPa, sea_level_hPa,
                                             columbia_dr_variance_hPa,
                                             sl_inHg, sl_mmHg, sl_psi,
                                             humidity_DHT)

                else:
                    gb.logging.info("ERROR: Sensor reading out of range")

                if alive_counter >= 3:
                    self.send_snsr_keep_alive(db_q_out)
                    alive_counter = 0
                alive_counter += 1

                gb.time.sleep(snsr.SENSOR_SLEEPTIME)

        except Exception as e:
            gb.logging.error("ERROR: %s" % (e))

        gb.logging.info("Exiting %s" % (self.name))

