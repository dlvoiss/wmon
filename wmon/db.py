import gb

#####################
# Database Defines
#####################

# DB message types
DB_LOCAL_STATS           = 201
DB_TODAY_MIN_MAX         = 202
DB_REQ_TODAY_MIN_MAX     = 203
DB_24HR_MIN_MAX          = 204
DB_REQ_24HR_MIN_MAX      = 205
DB_30DAY_MIN_MAX         = 206
DB_REQ_30DAY_MIN_MAX     = 207
DB_ALLTIME_MIN_MAX       = 208
DB_REQ_ALL_TIME_MIN_MAX  = 209
DB_MO_YEAR_MIN_MAX       = 210
DB_REQ_MO_YEAR_MIN_MAX   = 211
DB_DAY_HIGH_LOW_AVG      = 212
DB_DAY_NIGHT_AVG         = 213
DB_SUNTIMES              = 214
DB_INIT_DAY_NIGHT_AVG    = 215
DB_CPU_TEMPERATURE       = 216
DB_CPU_FAN               = 217
DB_GUST                  = 218
DB_MAX_1_HOUR            = 219
DB_MAX_TODAY             = 220
DB_READING               = 221
DB_WTHR_ALIVE            = 222
DB_WTHR30_ALIVE          = 223
DB_WAVG_ALIVE            = 224
DB_SNSR_ALIVE            = 225
DB_COORD_ALIVE           = 226
DB_WV_ALIVE              = 227
DB_FAN_ALIVE             = 228
DB_RG_ALIVE              = 229
DB_AN_ALIVE              = 230
DB_INIT_HIGH_LOW_AVG     = 231
DB_TEST                  = 239
DB_EXIT                  = 240   # Keep this msg type LAST (highest integer)

#####################
# Database Functions
#####################

def get_db_msg_str(db_msgType):
    switcher={
        DB_LOCAL_STATS:'DB_LOCAL_STATS',
        DB_TODAY_MIN_MAX:'DB_TODAY_MIN_MAX',
        DB_REQ_TODAY_MIN_MAX:'DB_REQ_TODAY_MIN_MAX',
        DB_24HR_MIN_MAX:'DB_24HR_MIN_MAX',
        DB_REQ_24HR_MIN_MAX:'DB_REQ_24HR_MIN_MAX',
        DB_30DAY_MIN_MAX:'DB_30DAY_MIN_MAX',
        DB_REQ_30DAY_MIN_MAX:'DB_REQ_30DAY_MIN_MAX',
        DB_ALLTIME_MIN_MAX:'DB_ALLTIME_MIN_MAX',
        DB_REQ_ALL_TIME_MIN_MAX:'DB_REQ_ALL_TIME_MIN_MAX',
        DB_MO_YEAR_MIN_MAX:'DB_MO_YEAR_MIN_MAX',
        DB_REQ_MO_YEAR_MIN_MAX:'DB_REQ_MO_YEAR_MIN_MAX',
        DB_DAY_HIGH_LOW_AVG:'DB_DAY_HIGH_LOW_AVG',
        DB_DAY_NIGHT_AVG:'DB_DAY_NIGHT_AVG',
        DB_SUNTIMES:'DB_SUNTIMES',
        DB_INIT_DAY_NIGHT_AVG:'DB_INIT_DAY_NIGHT_AVG',
        DB_CPU_TEMPERATURE:'DB_CPU_TEMPERATURE',
        DB_CPU_FAN:'DB_CPU_FAN',
        DB_GUST:'DB_GUST',
        DB_MAX_1_HOUR:'DB_MAX_1_HOUR',
        DB_MAX_TODAY:'DB_MAX_TODAY',
        DB_READING:'DB_READING',
        DB_WTHR_ALIVE:'DB_WTHR_ALIVE',
        DB_WTHR30_ALIVE:'DB_WTHR30_ALIVE',
        DB_WAVG_ALIVE:'DB_WAVG_ALIVE',
        DB_SNSR_ALIVE:'DB_SNSR_ALIVE',
        DB_COORD_ALIVE:'DB_COORD_ALIVE',
        DB_WV_ALIVE:'DB_WV_ALIVE',
        DB_FAN_ALIVE:'DB_FAN_ALIVE',
        DB_RG_ALIVE:'DB_RG_ALIVE',
        DB_AN_ALIVE:'DB_AN_ALIVE',
        DB_INIT_HIGH_LOW_AVG:'DB_INIT_HIGH_LOW_AVG',
        DB_TEST:'DB_TEST',
        DB_EXIT:'DB_EXIT',
    }
    return switcher.get(db_msgType, "DB MSG TYPE INVALID")

def get_keep_alive_index(db_msgType):
    switcher={
        DB_WTHR_ALIVE: 1,
        DB_WTHR30_ALIVE: 2,
        DB_WAVG_ALIVE: 3,
        DB_SNSR_ALIVE: 4,
        DB_COORD_ALIVE: 5,
        DB_WV_ALIVE: 6,
        DB_FAN_ALIVE: 7,
        DB_RG_ALIVE: 8,
        DB_AN_ALIVE: 9,
    }
    return switcher.get(db_msgType, "KEEP ALIVE MSG TYPE INVALID")
