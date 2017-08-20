# -*- coding: utf-8 -*-

# depends RPi_I2C_driver (is included)
# depends pip install arrow
# but for smbus in python3 : apt-get install python3-smbus

import threading
import utils.RPi_I2C_driver
from time import *
from datetime import datetime
import arrow


class a3k_lcd():

	parent              = None
	lcd                 = None
	display_sleep       = True
	screen_displayed    = None
	screen_displayed_nb = None
	last_displayed      = None
	screen_option_displayed_nb = 1

	thread              = None
	threading_event     = None

	def __init__(self, parent, **kwargs):
		self.main = kwargs.get('main')
		self.parent = parent # a3k_interface
		self.lcd = utils.RPi_I2C_driver.lcd()
		self.clear(backlight=0)
		self.threading_event = threading.Event()

	def clear(self, **kwargs):
		if kwargs.get('backlight', 1):
			self.display_sleep = False
		else:
			self.display_sleep = True
		if kwargs.get('clear_screen_displayed', True):
			if self.screen_displayed != None:
				self.last_displayed = self.screen_displayed
				self.screen_displayed = None
				self.screen_displayed_nb = None
				self.screen_option_displayed_nb = 1
				self.main.log.debug('Reinit screen_displayed')
		self.lcd.lcd_clear()
		self.lcd.backlight(kwargs.get('backlight', 1))

	def start(self):
		self.display('welcome')

	def display(self, name, **kwargs):
		if self.screen_displayed == 'welcome':
			return False

		try:
			if callable(getattr(self, '_d_' + name)):
				if self.screen_displayed != name or name in ['homeLoop', 'menuOptions']:
					if name != self.screen_displayed:
						self.clear()
					self.main.log.debug('Display : '+name)
					self.screen_displayed = name
					self._clearThread()
					#self.thread = threading.Thread(target=self._displayThread, args=(name,))
					self.thread = threading.Thread(target=getattr(self, '_d_' + name), kwargs=kwargs)
					self.thread.start()
					self.main.log.debug('Starting thread : {}'.format(self.thread))
					# Screen interaction pour sleep mode (stop backlight 10s et clear display 20s)
				else:
					self.main.log.debug('Display : {} is already displayed.'.format(name))
		except AttributeError:
			self.main.log.exception('Function display "{}" does not exist.'.format('_d_' + name))

	def _clearThread(self):
		if self.thread is not None:
			self.main.log.debug('Deleting thread : {}'.format(self.thread))
			del self.thread
			self.threading_event.set()
			sleep(0.1) # augmenter si bug ecran
			self.threading_event.clear()
			sleep(0.1)
			#sleep(1)

	def _display(self, screens, clear=True, **kwargs):

		nb = kwargs.get('nb', 0)
		for screen in enumerate(screens):
			if nb and screen[0]+1 < nb:
				continue
			self.screen_displayed_nb = screen[0]+1
			#if screen[1].get('duration') < 0.1:
			#	continue
			if screen[1].get('clear', True):
				self.clear(clear_screen_displayed=False)
				self.threading_event.wait(0.1)
			
			if screen[1].get('line1'):
				if not screen[1].get('clear', True):
					if len(screen[1].get('line1')) < 16:
						screen[1]['line1'] = screen[1]['line1'] + ' ' * (16 - len(screen[1].get('line1')))
				self.lcd.lcd_display_string(screen[1].get('line1'), 1)
			if screen[1].get('line2'):
				if not screen[1].get('clear', True):
					if len(screen[1].get('line2')) < 16:
						screen[1]['line2'] = screen[1]['line2'] + ' ' * (16 - len(screen[1].get('line2')))
				self.lcd.lcd_display_string(screen[1].get('line2'), 2)
			if self.threading_event.wait(screen[1].get('duration')-0.1):
				return False
		if clear:
			self.clear(backlight=0)
		return True

	def _d_welcome(self):

		screens = [
			{
				'line1':"   Welcome to   ",
				'line2':" A3k GPS Tracker",
				'duration':1.2
			},
			{
				#'clear': False,
				'line1':"        by      ",
				'line2':"     All3kcis   ",
				'duration':1.2
			},
			{
				'line1':"Version :       ",
				'line2':self.main.app_version,
				'duration':1.2
			},
			{
				'line1':"Device ID :     ",
				'line2':self.main.config.get('main.device_id'),
				'duration':4
			}


		]
		
		self._display(screens, False)
		self.clear()
		self.main.trigger(self.getName(), 'ready')
		return

	def _d_homeLoop(self, **kwargs):

		duration = 5
		first=True
		screen_nb = kwargs.get('screen_nb', 0)
		if kwargs.get('direction',None):
			if kwargs.get('direction') == 'prev':
				if self.screen_displayed_nb == 1:
					screen_nb = 3
				else:
					screen_nb = self.screen_displayed_nb-1
			elif kwargs.get('direction') == 'next':
				if self.screen_displayed_nb == 3:
					screen_nb = 1
				else:
					screen_nb = self.screen_displayed_nb+1
		
		while not self.threading_event.isSet():

			lat = self.parent.last_lat
			lon = self.parent.last_lon

			screens = [
				{
					'line1':"Date :",
					#'line2':arrow.utcnow().to(self.main.config.get('main.local_tz')).format('DD-MM-YYYY HH:mm'),
					'line2':arrow.utcnow().replace(hours=self.main.config.get('main.time_difference')).format('DD-MM-YYYY HH:mm'),
					
					'duration':duration
				},
				{
					'line1':"Lat : {}".format(lat),
					'line2':"Lon : {}".format(lon),
					'duration':duration
				},
				{
					'line1':"Mode : {}".format(self.main.config.get('main.mode').capitalize()),
					'line2':'',
					'duration':duration
				}
			]
			if first and screen_nb > 0:
				screens[screen_nb-1]['duration']=10
				first=False

			if not self._display(screens, False, nb=screen_nb):
				return

	def _d_menuOptions(self, **kwargs):
		options = kwargs.get('options')
		next_value = kwargs.get('next_value', False)
		"""
		i=1
		tmp_options = {}
		for k in options:
			tmp_options[k]=i
			i+=1
		len_options = i-1
		"""
		len_options = len(options)
		if kwargs.get('direction', None):
			#print ('scnb', self.screen_option_displayed_nb)
			if kwargs.get('direction') == 'prev':
				if self.screen_option_displayed_nb == 1:
					self.screen_option_displayed_nb = len_options 
				else:
					self.screen_option_displayed_nb -= 1
			elif kwargs.get('direction') == 'next':
				if self.screen_option_displayed_nb == len_options:
					self.screen_option_displayed_nb = 1
				else:
					self.screen_option_displayed_nb += 1

		param_obj = self.main.config.getDefault(options[self.screen_option_displayed_nb-1])
		name = param_obj['name'].capitalize()
		value = self.main.config.get(options[self.screen_option_displayed_nb-1], raw=True)
		
		#print (value)
		if next_value:
			nb_values = len(param_obj['values'])
			#print ('-' * 20)
			#print ('nb_values', nb_values)
			#print ('values', param_obj['values'])
			#print ('value', value)
			i=0
			for k in param_obj['values']:
				if str(k) == str(value):
					break
				i+=1
			# i = indice value
			#print ('i', i)
			if i >= nb_values-1:
				new_i_value = 0
			else:
				new_i_value =i+1
			#print ('new i', new_i_value)
			new_value = param_obj['values'][new_i_value]
			#print ('new_value', new_value)
			if self.main.config.set(options[self.screen_option_displayed_nb-1], new_value):
				value = new_value
			#print ('new_value_value', value)
			##del screens[0]['line1']
			##screens[0]['line2'] = str(value).capitalize()
			

		if str(value).lower() == 'default':
			real_value = self.main.config.get(options[self.screen_option_displayed_nb-1])
			f_value = value + ' ({})'.format(real_value)
		else:
			f_value = value

		screens = [
			{
				'line1':name, #16
				'line2':str(f_value).capitalize(),#16
				'duration':0
			}
		]

		if next_value:
			screens[0]['clear'] = False

		self._display(screens, False)


	def _d_howToUnlock(self):
		screens = [
			{
				'line1':"App is locked.  ",
				'line2':"",
				'duration':2
			},
			{
				'line1':"Press prev&next ",
				'line2':" 3s  to unlock. ",
				'duration':4
			}
		]
		self._display(screens)

	def _d_appIsNowLocked(self):
		screens = [
			{
				'line1':"App is now :",
				'line2':"      Locked",
				'duration':4
			}
		]
		self._display(screens)

	def _d_appIsNowUnlocked(self):
		screens = [
			{
				'line1':"App is now :",
				'line2':"    Unlocked",
				'duration':1.5
			}
		]
		self._display(screens, False)
		self.display('homeLoop') # menu

	def _d_appIsRunning(self):
		screens = [
			{
				'line1':" Tracker is now ",
				'line2':"    running  :) ",
				'duration':3
			}
		]
		self._display(screens, False)
		self.display('homeLoop')

	def _d_appIsSleeping(self):
		screens = [
			{
				'line1':" Tracker is now ",
				'line2':"  sleeping :'(  ",
				'duration':3
			}
		]
		self._display(screens, False)
		self.display('homeLoop')

	def triggerListener(self, kwargs):		
		#print (self.getName() + 'trigger listener : ', kwargs)
		pass
		
	def _d_bye(self):
		#self.threading_event.set()
		#if self.thread is not None:
		#	del self.thread
		self.clear()
		self._clearThread()
		self.lcd.lcd_display_string("     Bye bye    ", 1)
		self.lcd.lcd_display_string(" Have a nice day", 2)
		sleep(2) # important

	def remove(self):
		self._d_bye()
		self.clear(backlight=0)

	def getName(self):
		return self.__class__.__name__