# -*- coding: utf-8 -*-

import os, importlib, socket, copy, random, string

from RPi import GPIO
from time import time, sleep

from utils.a3k_config import a3k_config
from utils.a3k_interface import a3k_interface
from utils.a3k_logger import a3k_logger
from utils.a3k_db import a3k_db
from utils.a3k_sync import a3k_sync


"""
TODO :

 gyro, real_time, log_gps_data, low battery, reed sensor,

 GYRO, filtre sur 3 secondes + raw

 TODO implemente pause auto (gyro ou distance)
 TODO Generate and display Device code ( a ajouter sur le compte(siteweb) pour authentifier le device)

La classe principal gere le fonctionnement general

"""

class a3k_gps_tracker():

	# Constants
	BOX_IS_SLEEPING=0
	BOX_IS_RUNNING =1

	app_version    = 'dev'
	config         = None
	logger         = None   # a3k_gps_logger object
	log            = None   # logging object
	db             = None   # a3k_db object
	sync           = None   # a3k_sync object
	app_state      = 0      # see BOX_IS_...

	# Triggers
	triggersSaved = {}

	# Sensors activation in config.ini
	interface = None
	devices = {}
	plugins = {}

	#Others
	availables_plugins = []
	db_cache = {}

	def __init__(self):
		os.system('cls' if os.name=='nt' else 'clear')
		print ('-' * 10 + ' Launching tracker ' + '-' * 10)

	def start(self):
		self._init_config()
		self._init_logger()
		self.log.info('Starting configuration')
		self._startConfig()
		self._init_app()
		self.log.info('GPIO...')
		GPIO.setmode(GPIO.BOARD) # Init GPIO
		self._init_interface()
		self._init_db()
		self._init_devices()
		self._init_plugins()
		self._init_main()
		self.log.info('App launched ! Sleeping mode.')

		# Init tracking
		self.triggerSub('*', 'newFilteredLoc', callback=self.triggerListener)

		
	def _init_config(self):
		self.config = a3k_config(self)
		self.triggerSub('a3k_config', 'setAttr', callback=self.triggerListener)


	def _init_logger(self):

		self.logger = a3k_logger(self)
		self.log = self.logger.getLog()
		self.log.info('Logger is ready !')
		#self._logger_ready = True

	def _init_interface(self):
		if self.config.get('main.interface'):
			self.log.info('Interface...')
			self.interface = a3k_interface(self)
		else:
			self.log.info('Interface is disabled.')

	def _init_db(self):
		self.log.info('Database...')
		self.db = a3k_db(self)

	def _init_devices(self):
		self.log.info('Devices...')

		pin = self.config.get('gpio.low_battery_pin')
		if pin:
			GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
			GPIO.add_event_detect(pin, GPIO.FALLING, callback=self.low_battery, bouncetime=1000)
			#print (GPIO.input(pin))

	def _init_plugins(self):
		self.log.info('Plugins...')
		self.availables_plugins = self._getAvailablePlugins('/a3k_gps_tracker/plugins')
		self.triggerSub(self.getName(), 'pluginChangeState', callback=self._triggerPluginChangeState)
		
		for plugin_name in self.availables_plugins:
			obj_param = {
				'name':plugin_name.capitalize(),
				'default_value':False,
				'type':'bool',
				'values':['True', 'False'],
			}
			if not self.config.addEditableParam('plugins.'+plugin_name, obj_param):
				self.log.warning('Plugins "{}", error when add editable.'.format(plugin_name))
			if self.config.get('plugins.'+plugin_name):
				self._loadPlugin(plugin_name)
				plugin_value = True
			else:
				plugin_value = False
				self.log.info('Plugin "{}" is available.'.format(plugin_name))

	def _init_main(self):
		self.log.info('Main...')
		#self.isReachable(self.config.get('main.server_domain'))
		#self.config.get('main.real_time')
		self.sync = a3k_sync(self)


	def _getAvailablePlugins(self, plugins_dirs):
		plugs = []
		for path in plugins_dirs.split(os.pathsep):
			for filename in os.listdir(path):
				name, ext = os.path.splitext(filename)
				if ext.endswith(".py"):
					plugs.append(name)
			return plugs

	def _loadPlugin(self, plugin_name):
		self.plugins[plugin_name] = getattr(importlib.import_module('plugins.'+plugin_name), plugin_name)(self)
		
		self.log.info('Plugin "{}" is now activated.'.format(plugin_name))
		self.plugins[plugin_name].start()

	def _removePlugins(self):
		for plugin_name in list(self.plugins.keys()):
			self._removePlugin(plugin_name)

	def _removePlugin(self, plugin_name):
		
		if 'remove' in dir(self.plugins[plugin_name]):
			try :
				self.plugins[plugin_name].remove()
				sleep(0.1)
			except:
				self.log.exception('Plugin {} error during "remove".'.format(plugin_name))
		else:
			self.log.error('Plugin {} does not have method "remove".'.format(plugin_name))

		del self.plugins[plugin_name]

	def _startConfig(self):

		print ('Loading configuration')
		self.config.start()
		print ('Configuration succesful loaded.')

	def _init_app(self):
		if not self.config.get('main.device_id'):
			device_id = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(8))
			self.config.set('main.device_id', device_id, source='internal')

	def isReachable(self, url, port=80, delay=5):
		try:
			socket.create_connection((url, port), delay)
			self.log.info('URL : "{}:{}" is reachable.'.format(url, port))
			return True
		except OSError:
			self.log.info('URL : "{}:{}" is not reachable.'.format(url, port))
		return False

	# Subscrive to a trigger
	def triggerSub(self, class_name, trigger_name, **kwargs):
		if kwargs.get('callback') is None:
			self.log.error('Attr callback is not defined.')
			return

		if not self.triggersSaved.get(class_name):
			self.triggersSaved[class_name] = {} # dict
		if not self.triggersSaved.get(class_name).get(trigger_name):
			self.triggersSaved[class_name][trigger_name] = [] # List

		self.triggersSaved[class_name][trigger_name].insert(0,{'callback':kwargs.get('callback')})

	def triggerRemoveSub(self):
		pass
		# TODO

	def trigger(self, class_name, trigger_name, **kwargs):
		# TODO, lancer dans un thread puis chaque callback dans un nouveau thread
		if not class_name or not trigger_name or class_name == '*' or trigger_name == '*':
			self.log.error('Bad class_name or trigger_name for "{}.{}"'.format(class_name, trigger_name))
			return

		for ts_class_name in list(self.triggersSaved.keys()):
			if class_name == ts_class_name or ts_class_name == '*':
				for ts_trigger_name in list(self.triggersSaved[ts_class_name].keys()):
					if trigger_name == ts_trigger_name or ts_trigger_name == '*':
						for subs in self.triggersSaved.get(ts_class_name).get(ts_trigger_name):
							kwargs['class_name']=class_name
							kwargs['trigger_name']=trigger_name
							subs['callback'](kwargs) # send trigger to registered callback

	def triggerListener(self, kwargs):
		#print (self.getName() + 'trigger listener : ', kwargs)
		if kwargs.get('class_name') == 'a3k_config':
			if kwargs.get('trigger_name') == 'setAttr':
				attr = kwargs.get('attr')
				value = kwargs.get('value')
				splitted_attr = attr.split('.', 2)
				if len(splitted_attr) >= 2:
					if splitted_attr[0] == 'plugins':
						if splitted_attr[1] in self.availables_plugins:
							self.trigger(self.getName(), 'pluginChangeState', plugin_name=splitted_attr[1], value=value)
				#if attr == 'main.real_time':
				#	self._updateRealTime(value)
		else:
			if kwargs.get('trigger_name') == 'newFilteredLoc':
				if self.isRunning():
					#print (kwargs)
					# TODO config get INT value
					mode = {'walk': 1, 'bike': 2, 'car':3}[self.config.get('main.mode')]
					item = {
						'cols':['lat','lon', 'speed', 'alt', 'sats', 'fix', 'timestamp', 'mode'],
						'values':[float(kwargs.get('lat')), float(kwargs.get('lon')), float(kwargs.get('rawSpeed')), float(kwargs.get('alt')), kwargs.get('sats'), kwargs.get('fix'), int(time()), mode]
					}
					self._insertWithCache('tracks', item)


	def _triggerPluginChangeState(self, kwargs):
		plugin_name = kwargs.get('plugin_name')
		#print (kwargs.get('value'), kwargs.get('value') == True)
		#print (self.plugins.get(plugin_name))
		if kwargs.get('value') == True and not self.plugins.get(plugin_name):
			self._loadPlugin(plugin_name)
		elif kwargs.get('value') == False and self.plugins.get(plugin_name):
			self._removePlugin(plugin_name)


	def _insertWithCache(self, table_name, data):
		
		if not self.db_cache.get(table_name):
			self.db_cache[table_name]={}
			self.db_cache[table_name]['cols']=data.get('cols')
			self.db_cache[table_name]['values']=[data.get('values')]
		else:
			if len(self.db_cache[table_name]['cols']) != len(data.get('cols')):
				# TODO better...
				self.log.error('Cols not match.')
				return
			self.db_cache[table_name]['values'].append(data.get('values'))

		if  len(self.db_cache[table_name].get('values')) >= self.config.get('main.'+ table_name +'_cache_nb', 10):
			self.log.debug('Insert cached elements in '+table_name)
			values = copy.deepcopy(self.db_cache[table_name])
			del self.db_cache[table_name]
			self.db.insertMany(table_name, values)

	#def _updateRealTime(self, value):
	#	print ('REALTIME STATUS UPDATE')
	#	if value:
	#		pass
	#	else:
	#		pass


	def getState(self):
		return self.app_state

	def isRunning(self):
		return self.app_state == self.BOX_IS_RUNNING

	def isSleeping(self):
		return self.app_state == self.BOX_IS_SLEEPING

	def wakeup(self):
		self.log.info('App is now Running !')
		self.app_state = self.BOX_IS_RUNNING
		
	def asleep(self):
		self.log.info('App is now Sleeping.')
		self.app_state = self.BOX_IS_SLEEPING

	def low_battery(self, channel):
		self.log.warning('/!\ Battery level is low !')
		#print (GPIO.input(channel))


	def getWebServerUrl(self):	
		return ( 'https' if self.config.get('main.use_https') else 'http' ) + '://'+self.config.get('main.server_domain')+self.config.get('main.webserver_url')

	def __setattr__(self, attr, val):
		prev_val = getattr(self, attr)
		object.__setattr__(self, attr, val)
			
		#if not (attr == '_logger_ready') and self._logger_ready is True:
		#	self.log.debug('Attribut "{}", value "{}" change to {}'.format(attr, prev_val, val))
		if attr == 'app_state':
			self.trigger(self.getName(), 'appChangeState', attr=attr, prev_val=prev_val, new_val=val)
		else:
			self.trigger(self.getName(), 'attrChangeState', attr=attr, prev_val=prev_val, new_val=val)

	def stop(self, shutdown=False):
		self.log.info('Stopping app in progress ... ')

		# Stop plugins
		self._removePlugins()

		# Stop interface
		if self.config.get('main.interface'):
			self.interface.stop()

		# Clean Gpio
		GPIO.cleanup()

		if shutdown:
			self.log.info('Shutting down in 60 seconds')
			os.system("sudo shutdown -t 1")
		self.log.info('App is stopped !')

	def getName(self):
		return self.__class__.__name__