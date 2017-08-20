import configparser

class a3k_config:

	parent = None
	conf   = None

	params = None
	default_params = None

	def __init__(self, parent):
		self.parent = parent
		self.conf = configparser.ConfigParser()
		self.conf.read('./config.ini') # TODO, create conf file if not exist, use config.sample.ini
		self._getDefaultParams()
	
	def start(self):
		self._loadParams()
		self._checkConfig()
		
	def get(self, attr, default_value=None, **kwargs):
		splitted_attr = attr.split('.', 2)
		if len(splitted_attr) >= 2:
			if len(splitted_attr) > 2:
				self.parent.log.warning('{} is ignored'.format(splitted_attr[2]))

			if self.params.get(splitted_attr[0]):
				if self.params[splitted_attr[0]].get(splitted_attr[1]):
					if kwargs.get('raw', False):
						return self.params[splitted_attr[0]][splitted_attr[1]]['value']
					if str(self.params[splitted_attr[0]][splitted_attr[1]]['value']).lower() == 'default':
						if self.default_params[splitted_attr[0]][splitted_attr[1]]['default_value'] == None:
							raise Exception('No default values for section:{} attr:{}'.format(splitted_attr[0], splitted_attr[1]))
						value = self.default_params[splitted_attr[0]][splitted_attr[1]]['default_value']
					else:
						value = self.params[splitted_attr[0]][splitted_attr[1]]['value']
					if self.default_params.get(splitted_attr[0]) and self.default_params[splitted_attr[0]].get(splitted_attr[1]):
						if self.default_params[splitted_attr[0]][splitted_attr[1]]['type'] in ['int','integer']:
							return int(value)
						elif self.default_params[splitted_attr[0]][splitted_attr[1]]['type'] == 'float':
							return float(value)
						elif self.default_params[splitted_attr[0]][splitted_attr[1]]['type'] in ['bool','boolean']:
							return str(value).lower() in ['true', '1', 'oui', 'y', 'o']
					return str(value)
				else:
					self.parent.log.warning('Attr does not exist:{}.{}'.format(splitted_attr[0], splitted_attr[1]))
			else:
				self.parent.log.warning('Section does not exist:{}'.format(splitted_attr[0]))
		else:
			self.parent.log.warning('Please use format section.attr_name')
		
		return default_value

	def set(self, attr, value, source='interface'):
		# TODO : self.parent.hook('beforeSetAttr')
		deleted_in_conf = False
		splitted_attr = attr.split('.', 2)
		if len(splitted_attr) >= 2:
			if len(splitted_attr) > 2:
				pass

			if not self.params.get(splitted_attr[0]):
				self.params[splitted_attr[0]]={}

			if not self.params[splitted_attr[0]].get(splitted_attr[1]):
				self.params[splitted_attr[0]][splitted_attr[1]]={}


			if self.default_params.get(splitted_attr[0]) and self.default_params[splitted_attr[0]].get(splitted_attr[1]):
				if source == 'interface' and not splitted_attr[0]+'.'+splitted_attr[1] in self.editables_params:
					# and not self.default_params[splitted_attr[0]][splitted_attr[1]].get('editable_in_interface', False):
					self.parent.log.warning('Attr:{}.{} is not updatable in interface.'.format(splitted_attr[0], splitted_attr[1]))
					return False

			if str(value).lower() == 'default':
				if not self.default_params.get(splitted_attr[0]) or not self.default_params[splitted_attr[0]].get(splitted_attr[1]) or not self.default_params[splitted_attr[0]][splitted_attr[1]].get('default_value'):
					self.parent.log.warning('No default values for section:{} attr:{}'.format(splitted_attr[0], splitted_attr[1]))
					return False
				else:
					if splitted_attr[0] in self.conf.sections() and self.conf[splitted_attr[0]].get(splitted_attr[1]):
						del self.conf[splitted_attr[0]][splitted_attr[1]]
						self._saveConfig()
			else:
				if self.default_params.get(splitted_attr[0]) and self.default_params[splitted_attr[0]].get(splitted_attr[1]):
					if self.default_params[splitted_attr[0]][splitted_attr[1]].get('values'):
						if not value in self.default_params[splitted_attr[0]][splitted_attr[1]].get('values'):
							self.parent.log.warning('Forbidden value  for key:{}.{}'.format(splitted_attr[0], splitted_attr[1]))
							return False
					if str(value).lower() == str(self.default_params[splitted_attr[0]][splitted_attr[1]].get('default_value')).lower():
						deleted_in_conf = True
						del self.conf[splitted_attr[0]][splitted_attr[1]]
						self._saveConfig()

				if not deleted_in_conf:
					if not splitted_attr[0] in self.conf.sections():
						self.conf[splitted_attr[0]] = {}
					#if not self.conf[splitted_attr[0]].get(splitted_attr[1]):
					#if splitted_attr[0] in self.conf.sections() and self.conf[splitted_attr[0]].get(splitted_attr[1]):
					self.conf[splitted_attr[0]][splitted_attr[1]] = str(value)
					self._saveConfig()

			if self.default_params.get(splitted_attr[0]) and self.default_params[splitted_attr[0]].get(splitted_attr[1]):
				if self.default_params[splitted_attr[0]][splitted_attr[1]]['type'] in ['int','integer']:
					value = int(value)
				elif self.default_params[splitted_attr[0]][splitted_attr[1]]['type'] == 'float':
					value = float(value)
				elif self.default_params[splitted_attr[0]][splitted_attr[1]]['type'] in ['bool','boolean']:
					value = str(value).lower() in ['true', '1', 'oui', 'y', 'o']

			self.params[splitted_attr[0]][splitted_attr[1]]['value']=value
			self.parent.log.debug('Attr {}, value change to {}'.format(attr, value))
			self.parent.trigger(self.getName(), 'setAttr', attr=attr, value=value)
			return True
		return False

	def getDefault(self, attr, **kwargs):
		splitted_attr = attr.split('.', 2)
		if len(splitted_attr) >= 2:
			if len(splitted_attr) > 2:
				self.parent.log.warning('{} is ignored'.format(splitted_attr[2]))

			if self.default_params.get(splitted_attr[0]):
				if self.default_params[splitted_attr[0]].get(splitted_attr[1]):
						return self.default_params[splitted_attr[0]][splitted_attr[1]]
		return None

	def _saveConfig(self):
		with open('./config.ini','w') as configfile:
			self.conf.write(configfile)
			return True
		print ('Erreur while saving configuration file.')
		return False

	
	def addEditableParam(self, params_name, obj_param):
		splitted_attr = params_name.split('.', 2)
		if len(splitted_attr) >= 2:
			if len(splitted_attr) > 2:
				self.parent.log.warning('{} is ignored'.format(splitted_attr[2]))

			if obj_param.get('default_value') == None:
				self.parent.log.error('{} is ignored, no default value'.format(params_name))
				return False

			if self.default_params.get(splitted_attr[0]) == None:
				self.default_params[splitted_attr[0]] = {}

			if self.default_params[splitted_attr[0]].get(splitted_attr[1]):
				return False

			self.default_params[splitted_attr[0]][splitted_attr[1]] = obj_param
			self.editables_params.append(params_name)

			if not self.params.get(splitted_attr[0]):
				self.params[splitted_attr[0]] = {}
			if not self.params[splitted_attr[0]].get(splitted_attr[1]):
				self.params[splitted_attr[0]][splitted_attr[1]] = {}
				self.params[splitted_attr[0]][splitted_attr[1]]['value']=obj_param['default_value']

			return True

	def _loadParams(self):
		"""
		Charge la config depuis fichier de conf
		"""
		self._setDefaultParams()
		for section in self.conf.sections():
			for (key, value) in self.conf.items(section):
				#print (section, key, value)
				if self.params.get(section) == None:
					self.parent.log.warning('Section {} does not exist.'.format(section))
					self.params[section] = {}

				if not self.params[section].get(key):
					#self.parent.log.warning('Key {} does not exist for section {}.'.format(key, section))
					self.params[section][key] = {}

				if self.params[section].get(key).get('values'):
					if value in self.params[section][key].get('values'):
						self.params[section][key]['value'] = value
					else:
						self.parent.log.warning('Forbidden value  for key {}'.format(key))
				else:
					self.params[section][key]['value'] = value		

	def _checkConfig(self):
		return True
		#raise 'error config'
		# check values is correct (default pramas, values)

	def _setDefaultParams(self):
		if self.params:
			return
		self.params = {}
		for (section_name, sections_values) in self.default_params.items():
			self.params[section_name] = {}
			for (attr_name, attr_params) in sections_values.items():
				if attr_params.get('default_value') != None:
					self.params[section_name][attr_name] = {}
					if attr_params.get('value'):
						self.params[section_name][attr_name]['value'] = str(attr_params['value'])
					else:
						self.params[section_name][attr_name]['value'] = str(attr_params['default_value'])
				else:
					raise Exception('No default values for section:{} attr:{}'.format(section_name, attr_name))

	def _getDefaultParams(self):
		if self.default_params:
			return
		# value = 'default' # Mode auto ( pour garder la valeur par defaut )
		#self.params = copy.deepcopy(self.default_params)
		self.editables_params = ['main.real_time', 'main.mode', 'main.file_log_level', 'main.time_difference', 'main.temperature_unit']

		self.default_params = {
			'main':{
				'device_id':{
					'name':'ID Device',
					'default_value':'',
					'type': 'string'
				},
				'real_time':{
					'name':'Real time',
					'default_value':'False',
					'type': 'bool',
					'values':['True','False']
				},
				'server_domain':{
					'name':'Server URL',
					'default_value':'gps-tracking.all-3kcis.fr',
					'type': 'string',
				},
				'use_https':{
					'name':'Server use secure connection',
					'default_value':True,
					'type': 'bool',
				},
				'webserver_url':{
					'name':'Web Server URL',
					'default_value':'/',
					'type': 'string',
				},

				'realtime_port':{
					'name':'Port for realtime server',
					'default_value':9541,
					'type': 'int',
				},
				'api_key':{
					'name':'Access key for server',
					'default_value':'PLEASE_CONFIGURE_YOUR_API_KEY',
					'type': 'string',
				},
				#TODO deprecated (utilisation du Device ID dans server web)
				#'realtime_instance_name':{
				#	'name':'Instance name for realtime server',
				#	'default_value':'DEFAULT',
				#	'type': 'string',
				#},
				'mode':{
					'name':'Mode',
					'default_value':'walk',
					'type': 'string',
					'values':['walk','bike','car']
				},
				'interface':{
					'name':'Interface',
					'default_value':'True',
					'type': 'bool',
					'values':['True','False']
				},
				'console_log_level':{
					'name':'console_log_level',
					'default_value':'INFO',
					'type': 'string',
					'values':[
						'DEBUG',
						'INFO'
					]
				},
				'file_log_level':{
					'name':'Niveau de log', # fichier
					'value': 'Default',
					'default_value':'DEBUG',
					'type': 'string',
					'values':[
						'Default',
						'DEBUG',
						'INFO'
					]
				},
				'logfile':{
					'name':'logfile',
					'default_value':'/a3k_gps_tracker/logs/a3k_gps_tracker.log',
					'type': 'string'
				},
				# Dur a gerer .... to many timezones ...
				'local_tz':{
					'name':'Time zone',
					'default_value':'Europe/Paris',
					'type': 'string',
					'values':[
						'Europe/Paris',
						'Other'
					],
				},
				'time_difference':{
					'name':'Time difference',
					'value': 'Default',
					'default_value':2,
					'type': 'int',
					'values':[
						-12,-11,-10,-9,-8,-7,-6,-5,-4,-3,-2,-1,0,1,'Default',2,3,4,5,6,7,8,9,10,11,12
					],
				},
				'temperature_unit':{
					'name':'Temperature',
					'default_value':'Celsius',
					'type': 'string',
					'values':[
						'Celsius', 'Fahrenheit'
					],
				},
				'gps_refresh_interval':{
					'name':'gps_refresh_interval',
					'default_value':1,
					'type': 'int',
				},
				'tracks_cache_nb':{
					'name':'tracks_cache_nb',
					'default_value':10,
					'type': 'int',
				},
			},
			'gpio':{
				'low_battery_pin':{
					'name':'low_battery_pin',
					'default_value':'15',
					'type': 'int'
				}
			},
			'interface':{
				'screen_address':{
					'name':'screen_address',
					'default_value':'0x27',
					'type': 'int' # hexa ?
				},
				'btn_main_pin_btn':{
					'name':'btn_main_pin_btn',
					'default_value':'38',
					'type': 'int'
				},
				'btn_main_pin_led':{
					'name':'btn_main_pin_led',
					'default_value':'40',
					'type': 'int'
				},
				'btn_prev_pin_btn':{
					'name':'btn_prev_pin_btn',
					'default_value':'35',
					'type': 'int'
				},
				'btn_next_pin_btn':{
					'name':'btn_next_pin_btn',
					'default_value':'37',
					'type': 'int'
				},
				'clear_lcd_interval':{
					'name':'clear_lcd_interval',
					'default_value':20,
					'type': 'int'
				},
				'lock_interval':{
					'name':'lock_interval',
					'default_value':35,
					'type': 'int'
				},
			},
			'tracking':{
				# ex : passkey node.js account1 
				#'attr_name':{}
			},
			'plugins':{
				# empty
			},
			'sensors':{
				'temp_check_interval':{
					'name': 'Temp interval',
					'default_value': 10,
					'type': 'int'
				}
			}
		}
		
	def getName(self):
		return self.__class__.__name__