import gb

#########################
# Sensor Defines
#########################

# Sensor message types

SNSR_EXIT = 10 # Keep this message type last


# DHT22 can provide data once every 2 seconds
# But using 10.0 seconds here
SENSOR_SLEEPTIME = 10

#########################
# Sensor Functions
#########################

def get_snsr_msg_str(snsr_msgType):
    switcher={
        SNSR_EXIT:'SNSR_EXIT',
    }
    return switcher.get(snsr_msgType, "SNSR MSG TYPE INVALID")
