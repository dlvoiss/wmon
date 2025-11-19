import gb

#########################
# Weather Defines
#########################

# Weather message types

WTHR_SENSOR_DATA     = 100
WTHR_TODAY_MIN_MAX   = 101
WTHR_24HR_MIN_MAX    = 102
WTHR_EXIT            = 110 # Keep this message type last

#########################
# Weather Functions
#########################

def get_wthr_msg_str(wthr_msgType):
    switcher={

        WTHR_SENSOR_DATA:'WTHR_SENSOR_DATA',
        WTHR_TODAY_MIN_MAX:'WTHR_TODAY_MIN_MAX',
        WTHR_24HR_MIN_MAX:'WTHR_24HR_MIN_MAX',
        WTHR_EXIT:'WTHR_EXIT',
    }
    return switcher.get(wthr_msgType, "WTHR MSG TYPE INVALID")
