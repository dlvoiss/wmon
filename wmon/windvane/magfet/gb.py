import logging
import time

WV_RANGE    = 0x1
WV_DETAIL   = 0x2
WV_ALL_CHAN = 0x4

DIAG_LEVEL = WV_RANGE|WV_DETAIL
#DIAG_LEVEL = 0x0

logging.basicConfig(level=logging.INFO,
                    format='(%(threadName)-10s) %(message)s',
                    )
