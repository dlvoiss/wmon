import gb

#########################
# Weather Average Defines
#########################

# Weather message types

WAVG_SENSOR_DATA    = 400
WAVG_TODAY_MIN_MAX  = 401
WAVG_DAY_NIGHT_INIT = 402
WAVG_HIGH_LOW_INIT  = 403
WAVG_SUNTIMES       = 404
WAVG_EXIT           = 410 # Keep this message type last

# For testing, use either define below, but NOT BOTH
WAVG_PROPAGATE_NIGHT = 0x1
WAVG_PROPAGATE_DAY   = 0x2
WAVG_DIAG_LEVEL = 0x0

#########################
# Weather Average Label Defines
#########################
maxf_tally  = 'maxf_tally'
maxf_cnt    = 'maxf_cnt'
minf_tally  = 'minf_tally'
minf_cnt    = 'minf_cnt'
df_tally    = 'dayf_tally'
df_cnt      = 'dayf_cnt'
nf_tally    = 'nightf_tally'
nf_cnt      = 'nightf_cnt'
df_mo_tally = 'dayf_mo_tally'
df_mo_cnt   = 'dayf_mo_cnt'
nf_mo_tally = 'nightf_mo_tally'
nf_mo_cnt   = 'nightf_mo_cnt'

DAYTIME   = 1
NIGHTTIME = 0

#########################
# Weather Functions
#########################

def get_wavg_msg_str(wthr_msgType):
    switcher={

        WAVG_SENSOR_DATA:'WAVG_SENSOR_DATA',
        WAVG_TODAY_MIN_MAX:'WAVG_TODAY_MIN_MAX',
        WAVG_DAY_NIGHT_INIT:'WAVG_DAY_NIGHT_INIT',
        WAVG_HIGH_LOW_INIT:'WAVG_HIGH_LOW_INIT',
        WAVG_SUNTIMES:'WAVG_SUNTIMES',
        WAVG_EXIT:'WAVG_EXIT',
    }
    return switcher.get(wthr_msgType, "WAVG MSG TYPE INVALID")
