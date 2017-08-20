# -*- coding: utf-8 -*-
import threading
from time import sleep
from RPi import GPIO

class a3k_btn():

	active = True
	btn_pin = None
	led_pin = None
	main = None
	parent = None
	mode = 1

	thread = None
	_stop = None

	def __init__(self, parent, btn_pin, led_pin=None, **kwargs):
		#threading.Thread.__init__(self)
		self.main = kwargs.get('main')
		self.parent = parent
		self.btn_pin = btn_pin
		self.led_pin = led_pin
		self.init_btn()

	def init_btn(self):
		
		self.main.log.debug('Create BTN, PIN:{} pull_up, LED PIN:{}'.format(self.btn_pin, self.led_pin))
		GPIO.setup(self.btn_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.add_event_detect(self.btn_pin, GPIO.FALLING, callback=self.parent.pushed, bouncetime=150)

		if self.led_pin:
			self.main.log.debug('Init Led Pin:{}'.format(self.led_pin))
			self._stop = threading.Event()
			GPIO.setup(self.led_pin, GPIO.OUT)
			GPIO.output(self.led_pin, GPIO.LOW)
			self.create_thread()
		
		self.start()

	def create_thread(self):
		if self.thread is not None:
			del self.thread
		self.thread = threading.Thread(target=self.run)

	def setMode(self, mode):
		#if self.main.debug:
			#print ('setmode pin:{}, mode:{}'.format(self.btn_pin, mode))
		self.mode = mode
		self._stop.set()
		sleep(0.1)
		self._stop.clear()
		#self._stop = threading.Event()
		return self

	def start(self):
		if self.led_pin:
			self.main.log.debug('Start Thread for Pin:{}'.format(self.btn_pin))
			self.create_thread()
			self.thread.start()

	def run(self):
		while not self._stop.isSet():
			if self.mode == 1:
				GPIO.output(self.led_pin, GPIO.HIGH)
				self._stop.wait(1)
				GPIO.output(self.led_pin, GPIO.LOW)
				self._stop.wait(1)
			elif self.mode ==2:
				GPIO.output(self.led_pin, GPIO.HIGH)
				self._stop.wait(1)
				GPIO.output(self.led_pin, GPIO.LOW)
				self._stop.wait(8)

	def stop(self):
		if self._stop:
			self._stop.set()

	def remove(self):
		self.stop()
		self.active = False # pour pushed function
		GPIO.remove_event_detect(self.btn_pin)
		#self.main.log.info('Remove btn PIN:{}'.format(self.btn_pin))
		
	def getName(self):
		return self.__class__.__name__

	def __del__(self):
		#print ("Deleting BTN:", self.btn_pin)
		self.main.log.debug('Delete btn PIN:{}'.format(self.btn_pin))