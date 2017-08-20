# -*- coding: utf-8 -*-
# depend pip3 install gpsd-py3

import threading, gpsd

from time import time, sleep
from math import radians, cos, sin, asin, sqrt


class a3k_sensor_gps:

	parent              = None

	is_fixed = False

	refresh_interval = None

	_thread = None
	_thread_event = None
	gps = None
	gps_fix = -1

	data = {'lat':0.0,'lon':0.0,'last_lat':0.0,'last_lon':0.0,'speed':0,'sats':0}
	plugin_types = []

	def __init__(self, parent):
		self.parent = parent

		self.refresh_interval = self.parent.config.get('main.gps_refresh_interval', 1)
		# stty -F /dev/ttyS0 raw 38400 cs8 -cstopb -echo
		#self.parent.registerLike('gps')
		#self.parent.registerLike('altimeter')
		self.plugin_types.append('sensor.gps') # TODO implemente ...
		self.plugin_types.append('sensor.altimeter')

		self.parent.triggerSub('a3k_gps_tracker', 'appChangeState', callback=self.triggerListener)

	def triggerListener(self, kwargs):
		if kwargs.get('class_name') == 'a3k_gps_tracker':
			if kwargs.get('trigger_name') == 'appChangeState':				
				if self.parent.isRunning():
					self.start()
				else:
					self.stop()

	def _startTracking(self):

		self.gps = gpsd.connect()

		try:
			self.parent.log.info('Gps device : '+ str(gpsd.device()))
		except:
			self.parent.log.info('Gps device : Unknown')
			self.parent.log.info('Retry in 0.5s...')
			sleep(0.5)
			self._startTracking()
			return

		if self._thread_event is None:
			self._thread_event = threading.Event()
		else:
			self._thread_event.clear()

		if self._thread != None:
			self._thread_event.set()
			del self._thread
			sleep(0.1)
			self._thread_event.clear()
			sleep(0.1)
		self._thread = threading.Thread(target=self._readData)
		self._thread.start()

	def _stopTracking(self):
		if self._thread_event != None:
			self._thread_event.set()
			sleep(0.08)

	def _readData(self):

		good_fix_nb = 0

		print ('Tracking will be started')
		while not self._thread_event.isSet():
			data = gpsd.get_current()
			gps_fix = data.mode

			if gps_fix != self.gps_fix:
				self.gps_fix = gps_fix
				if gps_fix == 3:
					pass
					#self.parent.log.info('Gps is now 3d fix.')
				elif gps_fix == 2:
					pass
					#self.parent.log.info('Gps is now 2d fix.')
				else:
					good_fix_nb = 0
					self.parent.log.info('Gps is not fixed.')

			# TODO, implemente GYROSCOPE		
			if gps_fix >= 2:

				good_fix_nb += 1
				if good_fix_nb >= 3 :
					pass
					# Gps is now fixed

				self.data['sats'] = data.sats
				self.data['speed'] = data.speed()
				# data.time_utc()

				if gps_fix == 3:
					self.data['alt'] = data.altitude()
				else:
					self.data['alt'] = 0

				lat, lon = data.position()
				self.data['lat'], self.data['lon'] = lat, lon
				#print (lat, lon)
				#self.parent.trigger(self.getName(), 'newRawLoc', lat=lat, lon=lon)
				distance = self.calculeDistance(self.data['last_lat'], self.data['last_lon'], lat, lon)
				#print ('Distance : ', distance, 'meters')


				# TODO test: distance > mode_min_distance_per_secondes*self.refresh_interval
				if distance > 1.1:
					# TEST with 0.5 ? (if GYRO)
					#print ('Send distance   :'+ str(distance))
					self.data['last_lat'], self.data['last_lon'] = lat, lon
					self.parent.trigger(self.getName(), 'newFilteredLoc', lat=lat, lon=lon, sats=self.data['sats'], rawSpeed=self.data['speed'], distance=distance, alt=self.data['alt'], fix=gps_fix)
				else:
					pass
					#print ('Ignore distance :'+ str(distance))
			else:
				pass
				#print ('GPS : NO Fix')

			self._thread_event.wait(self.refresh_interval)
		print ('Tracking stoped.')


	def calculeDistance(self, lat1, lon1, lat2, lon2):
		"""
		Calculate the great circle distance between two points 
		on the earth (specified in decimal degrees)
		"""
		# convert decimal degrees to radians 
		lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
		# haversine formula 
		dlon = lon2 - lon1 
		dlat = lat2 - lat1 
		a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
		c = 2 * asin(sqrt(a)) 
		km = 6378.137 * c
		return km * 1000

	def start(self):
		if self.parent.isRunning():
			self._startTracking()

	def stop(self):
		self._stopTracking()
	
	def remove(self):
		self.stop()
		self.parent.log.info('Delete {}.'.format(self.getName()))

	def getName(self):
		return self.__class__.__name__

	def __del__(self):
		self.parent.log.debug('Deleting.')