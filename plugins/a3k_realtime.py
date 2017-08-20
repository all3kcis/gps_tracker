# -*- coding: utf-8 -*-

# requiere pip install websocket-client
# socketIO-client (socketIO-client-2 ?)

import threading
from socketIO_client import SocketIO

from time import time, sleep


class a3k_realtime:

	parent              = None
	activated           = False
	socket_is_open      = False
	authenticated       = False

	server              = None
	port                = None

	_thread             = None
	_thread_event       = None
	socketIO            = None

	def __init__(self, parent):
		self.parent = parent
		self.server = self.parent.config.get('main.server_domain')
		self.port = str(self.parent.config.get('main.realtime_port'))
		self.parent.triggerSub('*', 'newFilteredLoc', callback=self.triggerListener)
		self.parent.triggerSub('a3k_gps_tracker', 'appChangeState', callback=self.triggerListener)
		self.parent.triggerSub('a3k_config', 'setAttr', callback=self.triggerListener)

	def _start_thread(self):
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
		self._thread = threading.Thread(target=self._ws)
		self._thread.start()

	def _ws(self):
		#print ('Start WS thread')
		# TODO check ip:port is accessible
		try:
			# SSL : See : https://pypi.python.org/pypi/socketIO-client
			self.socketIO = SocketIO('https://'+self.server, self.port, verify=False)
			self.socketIO.on('connect', self.on_connect)
			self.socketIO.on('disconnect', self.on_disconnect)
			self.socketIO.on('reconnect', self.on_reconnect)
			self.socketIO.on('auth_result', self.on_auth_result)
			self.socketIO.wait() #seconds=1
		except:
			pass


	def on_connect(self):
		self.socket_is_open=True
		self.parent.log.info('RealTime WS, Is now connected.')
		self._authenticate()

	def on_disconnect(self):
		# TODO real disconnect ...
		self.socket_is_open = False
		self.authenticated = False
		self.parent.log.info('RealTime WS, Is now disconnected.')

	def on_reconnect(self):
		self.socket_is_open=True
		self.parent.log.info('RealTime WS, Is now reconnected.')
		self._authenticate()	

	def on_auth_result(self, data=None):
		if data.get('state') == 'success' and data.get('state_code') == '2' :
			self.authenticated = True
			self.parent.log.info('RealTime WS, Is now authenticated.')
		else:
			print (data)

	def _authenticate(self):
		self.socketIO.emit('auth', {'api_key': self.parent.config.get('main.api_key'), 'device_id':self.parent.config.get('main.device_id')})
		# Server will call "on_auth_result"

	def send(self, name, data):

		if not self.activated:
			self.parent.log.debug('Plugin is not activated.')
			return
		elif not self.socket_is_open:
			self.parent.log.debug('Socket is not opened.')
			return
		elif not self.authenticated:
			self.parent.log.debug('You are not authenticated.')
			return
		else:
			try:
				self.socketIO.emit(name, data)
			except:
				self.parent.log.exception('Error during send data to real time server.')

	def triggerListener(self, kwargs):

		if kwargs.get('class_name') == 'a3k_config':
			if kwargs.get('trigger_name') == 'setAttr':
				if kwargs.get('attr') == 'main.real_time':
					if self.parent.config.get('main.real_time'):
						if self.parent.isRunning():
							self.start()
					else:
						self.stop()


		elif kwargs.get('class_name') == 'a3k_gps_tracker':
			if kwargs.get('trigger_name') == 'appChangeState':				
				if self.parent.isRunning():
					if self.parent.config.get('main.real_time'):
						self.start()
				else:
					self.stop()
		else:
			# registered like *
			# MOVE IN a3k_gps_tracker
			if self.activated:
				if kwargs.get('trigger_name') == 'newFilteredLoc':
					#print (kwargs)
					self.send('setLoc', {'latlng':[kwargs['lat'],kwargs['lon']], 'alt':kwargs['alt']})

	def safeStart(self):
		if self.parent.isRunning():
			self.start()


	def start(self):
		if self.activated:
			return
		if self.parent.isRunning():
			self.activated = True
			self._start_thread()

	def stop(self):
		if not self.activated:
			return
		self.activated = False
		if not self._thread_event:
			self._thread_event.set()
		try:
			self.socketIO.disconnect()
		except:
			pass
		#self._thread.join()
		sleep(0.08)
		del self._thread
	
	def remove(self):
		self.stop()
		self.parent.log.info('Delete {}.'.format(self.getName()))

	def getName(self):
		return self.__class__.__name__

	def __del__(self):
		self.parent.log.debug('Deleting.')