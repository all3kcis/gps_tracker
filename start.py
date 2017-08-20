#!/usr/bin/python3
# -*- coding: utf-8 -*-
from time import sleep
from utils.a3k_gps_tracker import a3k_gps_tracker

# Init app
app = a3k_gps_tracker()

try:
	# Starting app
	app.start()
	while 1:
		sleep(0.05)
	pass
except KeyboardInterrupt:
	app.stop()
except:
	# why exceptions is not catched here ????
	# sys.exc_info()[0] # import sys
	app.log.exception('Got exception on main handler')
	raise
#finally:
	