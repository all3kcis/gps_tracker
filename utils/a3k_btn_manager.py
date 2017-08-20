# -*- coding: utf-8 -*-
import threading
from time import sleep
from RPi import GPIO
from utils.a3k_btn import a3k_btn

class a3k_btn_manager():

	main   = None
	parent = None
	#mode = 1

	#thread = None
	#_stop = None
	btns = {}
	btns_pin = {}

	def __init__(self, parent, **kwargs):
		self.main = kwargs.get('main')
		self.parent = parent
		self.main.triggerSub('a3k_gps_tracker', 'appChangeState', callback=self.triggerListener)

	def addBtn(self, btn_pin, led_pin=None, **kwargs):
		if not self.btns.get(kwargs.get('title')):
			self.btns[kwargs.get('title')] = a3k_btn(self, btn_pin, led_pin, main=self.main)
			self.btns_pin[btn_pin] = self.btns[kwargs.get('title')]
		else:
			self.main.log.error('Btn title:{} is already used.'.format(kwargs.get('title')))

	def getBtnState(self, title):

		if self.btns[title]:
			return GPIO.input(self.btns[title].btn_pin)
		else:
			return None

	def pushed(self, channel):
		btn_press_timer = {}
		tt = 0
		channel_is_not_main = False
		if not channel in [self.btns['prev'].btn_pin, self.btns['main'].btn_pin, self.btns['next'].btn_pin]:
			btn_press_timer[channel] = 0
			channel_is_not_main = True
		btn_press_timer['prev'] = 0
		btn_press_timer['main'] = 0
		btn_press_timer['next'] = 0


		#self.main.log.debug('Pushed Pin:{}'.format(channel))
		while True:
			if (GPIO.input(channel) == False) : # is pushing
				#
				tt += 0.1
				if channel_is_not_main:
					btn_press_timer[channel] += 0.1 # save time
					continue
				
				#if self.btns.get('prev') and channel != self.btns['prev'].btn_pin:
				if self.getBtnState('prev') == 0:
					btn_press_timer['prev'] += 0.1
				#if self.btns.get('main') and channel != self.btns['main'].btn_pin:
				if self.getBtnState('main') == 0:
					btn_press_timer['main'] += 0.1
				#if self.btns.get('next') and channel != self.btns['next'].btn_pin:
				if self.getBtnState('next') == 0:
					btn_press_timer['next'] += 0.1

			else:
				if tt >= 0.2:
					self.main.log.debug('Pushed Pin:{} D:{}'.format(channel, round(tt,1)))
					self.main.log.debug(btn_press_timer)
					self.main.trigger(self.getName(), 'btnPushed', timer=btn_press_timer)
					#btn_press_timer[channel] = 0
				return
			sleep(0.1)


	def triggerListener(self, kwargs):
		#print (self.getName() + 'trigger listener : ', kwargs)
		if kwargs.get('class_name') == 'a3k_gps_tracker':
			if kwargs.get('trigger_name') == 'appChangeState':
					if self.main.isRunning():
						self.btns['main'].setMode(2).start()
					elif self.main.isSleeping():
						self.btns['main'].setMode(1).start()
			

	def remove(self):
		#for key, btn in self.btns.items():
		for key in list(self.btns.keys()):
			self.btns[key].remove()
		self.btns.clear()
		self.btns_pin.clear()
		
	def getName(self):
		return self.__class__.__name__

	def __del__(self):
		pass
		#print ("Deleting BTN:", self.btn_pin)
		#self.main.log.info('Delete btn PIN:{}'.format(self.btn_pin))