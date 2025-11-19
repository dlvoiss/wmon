import gb

#########################
# Weather Defines
#########################

# Weather message types

WTHR30_SENSOR_DATA      = 300
WTHR30_30DAY_MIN_MAX    = 301
WTHR30_MO_YEAR_MIN_MAX  = 302
WTHR30_ALL_TIME_MIN_MAX = 303
WTHR30_EXIT             = 310 # Keep this message type last

#########################
# Weather Functions
#########################

def get_wthr30_msg_str(wthr_msgType):
    switcher={

        WTHR30_SENSOR_DATA:'WTHR30_SENSOR_DATA',
        WTHR30_30DAY_MIN_MAX:'WTHR30_30DAY_MIN_MAX',
        WTHR30_MO_YEAR_MIN_MAX:'WTHR30_MO_YEAR_MIN_MAX',
        WTHR30_ALL_TIME_MIN_MAX:'WTHR30_ALL_TIME_MIN_MAX',
        WTHR30_EXIT:'WTHR30_EXIT',
    }
    return switcher.get(wthr_msgType, "WTHR30 MSG TYPE INVALID")
