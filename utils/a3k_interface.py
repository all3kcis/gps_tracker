# -*- coding: utf-8 -*-

import os, threading

from time import time, sleep

from utils.a3k_lcd import a3k_lcd
from utils.a3k_btn_manager import a3k_btn_manager


class a3k_interface():


	parent = None
	devices = {}

	_editable_options = None

	_last_interaction = 0
	_watch_last_interaction_event = None # threading event
	_watch_last_interaction_thread = None
	_interface_is_locked = False

	app_is_going_to_stop = False

	last_lat = 0
	last_lon = 0

	def __init__(self, parent):
		self.parent = parent

		# Screen
		self.devices['screen'] = a3k_lcd(self, main=parent)
		self.devices['screen'].start()

		# Buttons
		self.devices['btn_manager'] = a3k_btn_manager(self, main=parent)
		self.devices['btn_manager'].addBtn(
			self.parent.config.get('interface.btn_main_pin_btn'),
			self.parent.config.get('interface.btn_main_pin_led'),
			title='main')
		self.devices['btn_manager'].addBtn(
			self.parent.config.get('interface.btn_prev_pin_btn'),
			title='prev')
		self.devices['btn_manager'].addBtn(
			self.parent.config.get('interface.btn_next_pin_btn'),
			title='next')

		self.parent.triggerSub('a3k_lcd', 'ready', callback=self.triggerListener)
		self.parent.triggerSub('a3k_btn_manager', 'btnPushed', callback=self.triggerListener)
		self.parent.triggerSub('a3k_gps_tracker', 'appChangeState', callback=self.triggerListener)
		self.parent.triggerSub('a3k_gps_tracker', 'interfaceLastInteractionDuration', callback=self.triggerListener)
		self.parent.triggerSub('a3k_interface', 'interfaceChangeState', callback=self.triggerListener)
		self.parent.triggerSub('*', 'newFilteredLoc', callback=self.triggerListener)# GPS sensors

		self.set_interaction()

	def triggerListener(self, kwargs):
		#print (self.getName() + 'trigger listener : ', kwargs)
		if kwargs.get('class_name') == 'a3k_lcd':
			if kwargs.get('trigger_name') == 'ready':
				self.set_interaction()
				self.devices['screen'].display('homeLoop')

		elif kwargs.get('class_name') == 'a3k_interface':
			if kwargs.get('trigger_name') == 'interfaceChangeState':
				if kwargs.get('new_val') == True:
					self.devices['screen'].display('appIsNowLocked')
				else:
					self.devices['screen'].display('appIsNowUnlocked')

		elif kwargs.get('class_name') == 'a3k_gps_tracker':
			if kwargs.get('trigger_name') == 'appChangeState':				
					if self.parent.isRunning():
						self.devices['screen'].display('appIsRunning')
					elif self.parent.isSleeping():
						self.devices['screen'].display('appIsSleeping')		
			if kwargs.get('trigger_name') == 'interfaceLastInteractionDuration':
				if kwargs.get('duration') >= (self.parent.config.get('interface.clear_lcd_interval')-0.2) and kwargs.get('duration') <= (self.parent.config.get('interface.clear_lcd_interval')+1.2):
					if self.devices['screen'].screen_displayed != None:
						self.devices['screen']._clearThread()
						self.devices['screen'].clear(backlight=0)
						self.parent.log.debug('Lcd cleaned up.')
				else:
					if not self.screen_displayed:
						self.display('homeLoop')
		elif kwargs.get('class_name') == 'a3k_btn_manager':
				if kwargs.get('trigger_name') == 'btnPushed':
					#self.parent.log.debug('Btn pushed : pin:{}, Duration:{}, App state:{}'.format(btn_pin, duration, self.app_state))
					timer  = kwargs.get('timer')
					if not self._interface_is_locked:
						self.set_interaction()

						# First, many button->duration, 1 button->duration
						if timer.get('prev') >= 2.5 and timer.get('next') >= 2.5:
							# Lock Interface
							self._interface_is_locked = not self._interface_is_locked
							return
						elif timer.get('prev') >= 0.2 and timer.get('prev') <= 0.9:
							if self.devices['screen'].screen_displayed == 'homeLoop':
								self.devices['screen'].display('homeLoop', direction='prev')
								return
							if self.devices['screen'].screen_displayed == 'menuOptions':
								options = self._getEditableOptions()
								self.devices['screen'].display('menuOptions', options=options, direction='prev')
								pass
								
						elif timer.get('next') >= 0.2 and timer.get('next') <= 0.9:
							if self.devices['screen'].screen_displayed == 'homeLoop':
								self.devices['screen'].display('homeLoop', direction='next')
								return
							if self.devices['screen'].screen_displayed == 'menuOptions':
								options = self._getEditableOptions()
								self.devices['screen'].display('menuOptions', options=options, direction='next')
								pass

						elif timer.get('main') >= 15:
							self.parent.log.info('Reboot in 10 seconds')
							sleep(9)
							os.system("sudo reboot")
							return

						elif timer.get('main') >= 10:
							self.parent.stop(True)
							return

						elif timer.get('main') >= 3:
							if self.devices['screen'].screen_displayed == 'menuOptions':
								self.devices['screen'].display('homeLoop')
								return
							else:
								if self.parent.app_state == self.parent.BOX_IS_SLEEPING:
									self.parent.wakeup()
									return
								elif self.parent.app_state == self.parent.BOX_IS_RUNNING:
									self.parent.asleep()
									return

						elif timer.get('main') >= 0.2 and timer.get('main') <= 0.9:
							options = self._getEditableOptions()
							if self.devices['screen'].screen_displayed == 'menuOptions':
								self.devices['screen'].display('menuOptions', options=options, next_value=True)
								return
							else:
								self.devices['screen'].display('menuOptions', options=options)
								return

						# App is sleeping
						if self.parent.app_state == self.parent.BOX_IS_SLEEPING:
							pass
						# App is running
						elif self.parent.app_state == self.parent.BOX_IS_RUNNING:
							pass

					else:
						if timer.get('prev') >= 2.5 and timer.get('next') >= 2.5:
							# Unlock Interface
							self._interface_is_locked = not self._interface_is_locked
						else:
							self.devices['screen'].display('howToUnlock')
		else:
			if kwargs.get('trigger_name') == 'newFilteredLoc':
				self.last_lat = kwargs['lat']
				self.last_lon = kwargs['lon']

	def _getEditableOptions(self, force_refresh=False):

		return self.parent.config.editables_params
		"""
		if self._editable_options and not force_refresh:
			return self._editable_options
		self._editable_options = []
		for (section_name, attrs) in self.parent.config.default_params.items():
			for (attr_key, attr_obj) in attrs.items():
				if attr_obj.get('editable_in_interface', False) and attr_obj.get('values', False) and len(attr_obj.get('values')) > 1:
					self._editable_options.append(section_name+'.'+ attr_key)

		#print (self._editable_options)
		#print (self._editable_options.sort())
		#print (self._editable_options)

		return self._editable_options
		"""
		
	def _watch_last_interaction(self):
		#print ('Start watch last interaction while')
		while not self._watch_last_interaction_event.isSet():
			if self._last_interaction + self.parent.config.get('interface.lock_interval') <= time():
				if not self._interface_is_locked:
					#self.set_interaction()
					self._interface_is_locked = True
			self._watch_last_interaction_event.wait(1)
			self.parent.trigger(self.getName(), 'interfaceLastInteractionDuration', duration=(time()-self._last_interaction))
		#print ('Stop watch last interaction')

	def _start_watch_last_interaction(self):
		if self._watch_last_interaction_event is None:
			self._watch_last_interaction_event = threading.Event()
		else:
			self._watch_last_interaction_event.clear()

		if self._watch_last_interaction_thread != None:
			self._watch_last_interaction_event.set()
			del self._watch_last_interaction_thread
			sleep(0.1)
			self._watch_last_interaction_event.clear()
			sleep(0.1)
		self._watch_last_interaction_thread = threading.Thread(target=self._watch_last_interaction)
		self._watch_last_interaction_thread.start()

	def set_interaction(self):
		if self.app_is_going_to_stop:
			return

		self._last_interaction = time()
		if self._interface_is_locked:
			self._watch_last_interaction_event.set()
		else:
			self._start_watch_last_interaction()

	def stop(self):
		self.app_is_going_to_stop = True
		self._watch_last_interaction_event.set()
		del self._watch_last_interaction_thread

		# Screen
		self.devices['screen'].remove()

		# Buttons
		self.devices['btn_manager'].remove()
		sleep(0.1)
		del self.devices['btn_manager']
		sleep(0.1)


	def __setattr__(self, attr, val):
		prev_val = getattr(self, attr)
		object.__setattr__(self, attr, val)
		
		if (attr == '_interface_is_locked'):
			self.parent.log.info('Interface is now ' + ('locked' if val else 'unlocked'))
			self.set_interaction()
			self.parent.trigger(self.getName(), 'interfaceChangeState', attr=attr, prev_val=prev_val, new_val=val)

	def getName(self):
		return self.__class__.__name__