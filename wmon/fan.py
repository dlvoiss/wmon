
######################################
# CPU FAN message types
######################################
FAN_THRESH = 0

FAN_TEMPERATURE_DIFF    = 1.5
FAN_TEMPERATURE_DIFF_DB = 2.5

######################################
# GLOBAL GENERIC FUNCTIONS
######################################

def get_fan_msg_type_str(fan_msgType):
    switcher={
        FAN_THRESH:'FAN_THRESH',
    }
    return switcher.get(fan_msgType, "FAN MSG TYPE INVALID")

