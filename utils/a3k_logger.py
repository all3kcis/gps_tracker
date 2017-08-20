# -*- coding: utf-8 -*-

import logging
from logging.handlers import TimedRotatingFileHandler


class a3k_logger():


	parent              = None
	log                 = None
	stream_handler      = None
	time_rotate_handler = None


	def __init__(self, parent):
		self.parent = parent
		self.log = logging.getLogger()
		self.log.setLevel("DEBUG")

		if 'main' in self.parent.config.conf.sections() and self.parent.config.conf['main'].get('console_log_level'):
			stream_level = self.parent.config.conf['main'].get('console_log_level')
		else:
			stream_level = self.parent.config.default_params['main']['console_log_level']['default_value']

		if 'main' in self.parent.config.conf.sections() and self.parent.config.conf['main'].get('file_log_level'):
			file_level = self.parent.config.conf['main'].get('file_log_level')
		else:
			file_level = self.parent.config.default_params['main']['file_log_level']['default_value']

		if 'main' in self.parent.config.conf.sections() and self.parent.config.conf['main'].get('logfile'):
			log_file = self.parent.config.conf['main'].get('logfile')
		else:
			log_file = self.parent.config.default_params['main']['logfile']['default_value']

		self.stream_handler = logging.StreamHandler()
		self.stream_handler.setLevel(stream_level)
		self.log.addHandler(self.stream_handler)
		
		self.time_rotate_handler = TimedRotatingFileHandler(
			log_file,
			when='midnight',
			backupCount=7,
			utc = True
			)
		self.time_rotate_handler.setFormatter(logging.Formatter('%(asctime)-15s %(levelname)s (%(module)s:%(lineno)s) : %(message)s')) # %(device)s

		self.time_rotate_handler.setLevel(file_level)
		self.log.addHandler(self.time_rotate_handler)

		self.parent.triggerSub('a3k_config', 'setAttr', callback=self.triggerListener)

		self.log.info('-' * 10 + ' New log session ' + '-' * 10)

	def getLog(self):
		return self.log

	def triggerListener(self, kwargs):
		#print (self.getName() + 'trigger listener : ', kwargs)
		if kwargs.get('class_name') == 'a3k_config':
			if kwargs.get('trigger_name') == 'setAttr':
				if kwargs.get('attr') == 'main.file_log_level':
					self.time_rotate_handler.setLevel(self.parent.config.get(kwargs.get('attr')))