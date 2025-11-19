import time
import board
import busio

# ADS1115
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# I2C bus and address
#port = 1  # For Raspberry Pi 2/3/4, use 1. For older models, use 0.
#address = 0x48  # Default I2C address for ADS1115
address = 0x49   # I2C address ADS1115 ADDR connected to VCC

# ADS115 is 16-bit ADC
i2c = busio.I2C(board.SCL, board.SDA)
# Create the ADS object and specify the gain
#ads = ADS.ADS1115(i2c)  # For default I2C address 0x48
ads = ADS.ADS1115(i2c, address=0x49)

# Can change based on the voltage signal - Gain of 1 is typically
# enough for a lot of sensors
#ads.gain = 1
# Need to use 2/3 gain to get full 0-5v range and
# varying voltage through all 360 degrees
# Gain of 1 results in max voltage of 4.0x and about
# 1/4 of the hall effect sensor rotation pegs at 4.096v 
ads.gain = 2.0/3.0

chan0 = AnalogIn(ads, ADS.P0)  # Unused
chan1 = AnalogIn(ads, ADS.P1)  # Hall Effect Sensor
chan2 = AnalogIn(ads, ADS.P2)  # Unused
chan3 = AnalogIn(ads, ADS.P3)  # Unused
print("ADS1115 (i2c) initialized")

SLEEP_TIME = 0.5

exit = False

while not exit:
    try:

        # Get data from ADS1115 (ADC)
        raw_value0 = chan0.value
        voltage0 = chan0.voltage
        raw_value1 = chan1.value
        voltage1 = chan1.voltage
        raw_value2 = chan2.value
        voltage2 = chan2.voltage
        raw_value3 = chan3.value
        voltage3 = chan3.voltage

        print("-" * 20)
        print(f"ADS Raw Value: {raw_value0}, Voltage: {voltage0:.3f}V")
        print(f"ADS Raw Value: {raw_value1}, Voltage: {voltage1:.3f}V")
        print(f"ADS Raw Value: {raw_value2}, Voltage: {voltage2:.3f}V")
        print(f"ADS Raw Value: {raw_value3}, Voltage: {voltage3:.3f}V")

    except KeyboardInterrupt:
        print("Script terminated by user.")
        exit = True
    except Exception as e:
        print(f"An error occurred: {e}")

    time.sleep(SLEEP_TIME)
