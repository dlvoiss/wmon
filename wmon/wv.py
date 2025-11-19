import gb

#################
# Wind Vane Defines
#################

# Wind Direction message types
WV_GET_DIRECTION = 400
WV_EXIT          = 401   # Keep this as LAST message type

NORTH = "North"
NNE = "NNE"
NORTH_EAST = "North-East"
ENE = "ENE"
EAST = "East"
ESE = "ESE"
SOUTH_EAST = "South-East"
SSE = "SSE"
SOUTH = "South"
SSW = "SSW"
SOUTH_WEST = "South-West"
WSW = "WSW"
WEST = "West"
WNW = "WNW"
NORTH_WEST = "North-West"
NNW = "NNW"

INVALID        = 0
NORTH_INT      = 1
NORTH_EAST_INT = 2
EAST_INT       = 3
SOUTH_EAST_INT = 4
SOUTH_INT      = 5
SOUTH_WEST_INT = 6
WEST_INT       = 7
NORTH_WEST_INT = 8

#################
# Wind Vane Functions
#################
def get_wv_msg_str(wv_msg_type):
    switcher={
        WV_GET_DIRECTION:'WV_GET_DIRECTION',
        WV_EXIT:'WV_EXIT',
    }
    return switcher.get(wv_msg_type, "WV MSG TYPE INVALID")

#------------
# Convert resistor based weather vane directions string to integer value
#------------
def wind_dir_str_to_int(wind_dir_str):
    if (wind_dir_str == NORTH):
       return NORTH_INT
    elif (wind_dir_str == NORTH_EAST):
       return NORTH_EAST_INT
    elif (wind_dir_str == EAST):
       return EAST_INT
    elif (wind_dir_str == SOUTH_EAST):
       return SOUTH_EAST_INT
    elif (wind_dir_str == SOUTH):
       return SOUTH_INT
    elif (wind_dir_str == SOUTH_WEST):
       return SOUTH_WEST_INT
    elif (wind_dir_str == WEST):
       return WEST_INT
    elif (wind_dir_str == NORTH_WEST):
       return NORTH_WEST_INT
    return 0

#------------
# Convert integer to resistor based weather vane directions string
#------------
def wind_dir_int_to_str(wind_dir_int):
    if (wind_dir_int == NORTH_INT):
       return NORTH
    elif (wind_dir_int == NORTH_EAST_INT):
       return NORTH_EAST
    elif (wind_dir_int == EAST_INT):
       return EAST
    elif (wind_dir_int == SOUTH_EAST_INT):
       return SOUTH_EAST
    elif (wind_dir_int == SOUTH_INT):
       return SOUTH
    elif (wind_dir_int == SOUTH_WEST_INT):
       return SOUTH_WEST
    elif (wind_dir_int == WEST_INT):
       return WEST
    elif (wind_dir_int == NORTH_WEST_INT):
       return NORTH_WEST
    return "Invalid"

