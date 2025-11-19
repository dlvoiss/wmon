import gb

#################
# Rain Gauge Defines
#################

# Rain Gauge message types
RG_GET_RAINFALL = 300
RG_EXIT         = 301  # Always keep as LAST message ID

#################
# Rain Gauge Functions
#################
def get_rg_msg_str(rg_msg_type):
    switcher={
        RG_GET_RAINFALL:'RG_GET_RAINFALL',
        RG_EXIT:'RG_EXIT',
    }
    return switcher.get(rg_msg_type, "RG MSG TYPE INVALID")


