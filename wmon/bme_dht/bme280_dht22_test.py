import smbus2
import bme280
import time

import board
import adafruit_dht

#import adafruit_ads1x15.ads1115 as ADS
#from adafruit_ads1x15.analog_in import AnalogIn


# I2C bus and address
port = 1  # For Raspberry Pi 2/3/4, use 1. For older models, use 0.
address = 0x76  # Default I2C address for BME280, check your sensor's documentation

# Initial the dht device, with data pin connected to:
dhtDevice = adafruit_dht.DHT22(board.D25)

# Initialize I2C bus
bus = smbus2.SMBus(port)
#ads = (ADS.ADS1115(bus))

# DHT22 can provide data once every 2 seconds
# Use twice that interval for sleep time
SLEEP_TIME = 4.0

ARR_SZ = 10
C_DHT = [0.0] * ARR_SZ
C_BME = [0.0] * ARR_SZ
ix = 0

# Load calibration parameters from the sensor
calibration_params = bme280.load_calibration_params(bus, address)

try:
    while True:
        tempC_BME = 0.0
        tempF_BME = 0.0
        pressure_BME = 0.0
        tempC_DHT = 0.0
        tempF_DHT = 0.0
        humidity_DHT = 0.0
        
        # Take a single reading and return a compensated_reading object
        data = bme280.sample(bus, address, calibration_params)

        # Extract and print sensor data
        #print(data)
        tempC_BME = data.temperature
        tempF_BME = (tempC_BME * 9/5) + 32
        pressure_BME = data.pressure
        # data.humidity not supported by BME
        #humidity_percent = data.humidity

        try:
            tempC_DHT = dhtDevice.temperature
            tempF_DHT = tempC_DHT * (9 / 5) + 32
            humidity_DHT = dhtDevice.humidity

        except RuntimeError as error:
            # Errors happen fairly often, DHT's are hard
            # to read, just keep going
            print("-" * 20)
            print(error.args[0])
            time.sleep(SLEEP_TIME)
            continue

        except Exception as error:
            print(f"DHT ERROR: {error}")
            dhtDevice.exit()
            raise error

        print("-" * 20)
        print(f"{data.timestamp}")
        print(f"BME ID: {data.id}")
        print(f"BME Temperature: {tempF_BME:.1f} F, {tempC_BME:.1f} °C")
        print(f"BME Pressure: {pressure_BME:.1f} hPa\n")
        print(f"DHT Temperature: {tempF_DHT:.1f} F, {tempC_DHT:.1f} °C")
        print(f"DHT Humidity: {humidity_DHT:.1f}%")

        C_DHT[ix] = tempC_DHT
        C_BME[ix] = tempC_BME
        ix += 1
        if ix == ARR_SZ:
            ix = 0
            avg_t_D = 0
            avg_t_B = 0
            for iy in range(ARR_SZ):
                avg_t_D += C_DHT[iy]
                avg_t_B += C_BME[iy]
            avg_t_D = avg_t_D / ARR_SZ
            avg_t_B = avg_t_B / ARR_SZ
            print("=" * 20)
            print(f"Avg T: {avg_t_D:.1f} C, {avg_t_B:.1f} C")

        time.sleep(SLEEP_TIME)

except KeyboardInterrupt:
    print("Script terminated by user.")
except Exception as e:
    print(f"ERROR: {e}")
finally:
    bus.close()
