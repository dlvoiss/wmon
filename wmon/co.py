import gb

#################
# Coordinator Defines
#################

# Weather message types

# RE-NUMBER MESSAGES SO THEY ARE UNIQUE ACROSS THREADS AND PROCESSES

CO_MP_SHORT_WINDSPEED   = 100
CO_MP_LONG_WINDSPEED    = 101
CO_WIND_DIR             = 102
CO_MP_RAINFALL          = 103
CO_MP_GUST              = 104
CO_MP_MAX_1_HOUR        = 105
CO_MP_MAX_TODAY         = 106
CO_EXIT                 = 120   # Keep this msg type LAST

#################
# Coordinator Functions
#################
def get_co_msg_str(co_msg_type):
    switcher={
        CO_MP_SHORT_WINDSPEED:'CO_MP_SHORT_WINDSPEED',
        CO_MP_LONG_WINDSPEED:'CO_MP_LONG_WINDSPEED',
        CO_WIND_DIR:'CO_WIND_DIR',
        CO_MP_RAINFALL:'CO_MP_RAINFALL',
        CO_MP_GUST:'CO_MP_GUST',
        CO_MP_MAX_1_HOUR:'CO_MP_MAX_1_HOUR',
        CO_MP_MAX_TODAY:'CO_MP_MAX_TODAY',
        CO_EXIT:'CO_EXIT',
    }
    return switcher.get(co_msg_type, "CO MSG TYPE INVALID")


