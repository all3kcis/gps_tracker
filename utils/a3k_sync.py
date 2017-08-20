
import requests, json, copy
# Todo Sync Auto


class a3k_sync:

	parent = None
	params = {}

	duplicate_rows = 0

	def __init__(self, parent):
		self.parent = parent

		self.params = {
			'device_id':self.parent.config.get('main.device_id'),
			'api_key':self.parent.config.get('main.api_key')
		}
		#self.parent.get('main.auto_sync') 
		#self.parent.get('main.auto_sync_interval')

		self.sync()

	def sync(self):
		try:
			r = requests.post(self.parent.getWebServerUrl()+'getLastSyncID', self.params)
			if (r.status_code != 200):
				self.parent.log.error('Server is down or inaccessible.')
				return False
		except:
			self.parent.log.exception('Domain does not respond in delay, please check your connection.')
			return False


		result = r.json()
		if result['result']=='success':
			last_timestamp = result['data']['last_timestamp']
			#print (last_timestamp)
		else:
			self.parent.log.error(str(result))
			return False



		row_count = self.parent.db.selectCount('tracks', ' WHERE timestamp >= '+ str(last_timestamp))
		#print (row_count)
		if (row_count):
			self.duplicate_rows = 0
			row_batch = 0
			while row_batch < (row_count/10):

				res = self.parent.db.select('tracks', ['*'], 'WHERE timestamp >= '+str(last_timestamp)+' LIMIT '+str(row_batch*10)+',10')
				cols = res[0]
				data = res[1]

				if not self._sendSyncData(cols, data):
					self.parent.log.info('Error while sync RowCount:{}, RowBatch:{}, LastTimestamp:{} '.format(row_count,row_batch, last_timestamp))
					return False

				row_batch += 1

			#print (row_count, self.duplicate_rows)
			row_count = row_count - self.duplicate_rows
			self.parent.log.info('Succesfull sync '+ str(row_count) + ' tracks')
			return True

		self.parent.log.info('Nothing to sync')
		return True

	def _sendSyncData(self, cols, data):

		params = copy.deepcopy(self.params)
		params['cols'] = json.JSONEncoder().encode(cols)
		params['data'] = json.JSONEncoder().encode(data)

		try:
			r = requests.post(self.parent.getWebServerUrl()+'sync', params)
			if (r.status_code != 200):
				self.parent.log.error('Server is down or inaccessible.')
				return False
		except:
			self.parent.log.exception('Domain does not respond in delay, please check your connection.')
			return False

		result = r.json()
		if result['result']=='success':
			if result['duplicate'] > 0:
				self.duplicate_rows += result['duplicate']
			return True
		else:
			self.parent.log.error('Error :'+ str(r.text))
			return False
		