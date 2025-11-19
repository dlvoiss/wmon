import gb

#################
# Anemometer Defines
#################

# Weather message types
AN_EXIT = 0   # Keep this msg type LAST

#################
# Anemometer Functions
#################
def get_an_msg_str(an_msg_type):
    switcher={
        AN_EXIT:'AN_EXIT',
    }
    return switcher.get(an_msg_type, "AN MSG TYPE INVALID")


