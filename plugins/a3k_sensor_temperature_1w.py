
import threading, glob, time, subprocess

# etc/modules add w1-gpio w1-therm
# http://blogmotion.fr/diy/raspberry-ds18b20-14038
# https://learn.adafruit.com/adafruits-raspberry-pi-lesson-11-ds18b20-temperature-sensing/software
# 28-0416a455c7ff


class a3k_sensor_temperature_1w:

	parent              = None
	temp_unit           = None 
	temp_check_interval = None  

	base_dir            = None
	device_folder       = None
	device_file         = None

	last_temp_c         = -100
	last_temp_f         = -100

	def __init__(self, parent):
		self.parent = parent
		self.base_dir = '/sys/bus/w1/devices/'
		devices = glob.glob(self.base_dir + '28*')
		if len(devices) <= 0:
			self.parent.log.warning('Temperature device not detected.')
			return
		self.device_folder = devices[0]
		self.device = self.device_folder[( len(self.base_dir)):]
		self.parent.log.debug('Temperature device used is "{}".'.format(self.device))
		self.device_file = self.device_folder + '/w1_slave'

		self.temp_unit = self.parent.config.get('main.temperature_unit')
		self.temp_check_interval = self.parent.config.get('sensors.temp_check_interval', 10)
	def start(self):
		print ('TODO START')
		
	def read_temp_raw(self):
		catdata = subprocess.Popen(['cat', self.device_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		out,err = catdata.communicate()
		out_decode = out.decode('utf-8')
		lines = out_decode.split('\n')
		return lines
 
	def read_temp(self):
		lines = read_temp_raw()
		while lines[0].strip()[-3:] != 'YES':
			time.sleep(0.2)
			lines = read_temp_raw()
		equals_pos = lines[1].find('t=')
		if equals_pos != -1:
			temp_string = lines[1][equals_pos+2:]
			temp_c = float(temp_string) / 1000.0
			temp_f = temp_c * 9.0 / 5.0 + 32.0
			if self.temp_unit.lower() == 'fahrenheit':
				return temp_f
			else:
				return temp_c
	
	def remove(self):
		self.parent.log.info('Delete {}.'.format(self.getName()))

	def getName(self):
		return self.__class__.__name__

	def __del__(self):
		self.parent.log.debug('Deleting.')