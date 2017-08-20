# -*- coding: utf-8 -*-
# http://apprendre-python.com/page-database-data-base-donnees-query-sql-mysql-postgre-sqlite

import sqlite3, time


class a3k_db():


	parent              = None
	db                  = None

	lock                = False


	def __init__(self, parent):
		self.parent = parent
		self.parent.log.info('SQLITE version : {}'.format(sqlite3.version))
		self._initDB()

	def _initDB(self):
		# Create tables
		tables = self._getTables()
		for table in tables:
			self.createTable(table.get('name'), table.get('cols'))

	def _openDB(self):
		# TODO : relative url
		self.db = sqlite3.connect('/a3k_gps_tracker/db/a3k_gps_database.sqlite3') # ':memory:'
		# , check_same_thread=False
		self.cursor = self.db.cursor()

	def _closeDB(self):
		self.db.close()

	def createTable(self, table_name, table_cols):
		cols=[]
		for col in table_cols:
			cols.append('"'+col.get('name')+'" '+col.get('type'))

		sql = "CREATE TABLE IF NOT EXISTS "+table_name
		sql += " ("
		sql += ', '.join(cols)
		sql += ")"

		while True:
			if self.lock:
				time.sleep(0.05)
			else:
				self.lock = True
				self._openDB()
				self.cursor.execute(sql)
				self.db.commit()
				self._closeDB()
				self.lock = False
				return True


	def select(self, table_name, cols, sql):
		if len(cols) < 1:
			return

		cols = ', '.join(cols)

		while True:
			if self.lock:
				time.sleep(0.05)
			else:
				self.lock = True
				self._openDB()
				self.cursor.execute('SELECT '+ cols +' FROM '+ table_name +' '+sql)
				rows = self.cursor.fetchall()
				names = [description[0] for description in self.cursor.description]
				self.db.commit()
				self._closeDB()
				self.lock = False
				return [names, rows]

	def selectCount(self, table_name, sql):

		while True:
			if self.lock:
				time.sleep(0.05)
			else:
				self.lock = True
				self._openDB()
				self.cursor.execute('SELECT COUNT(*) FROM '+ table_name +' '+sql)
				rowcount = self.cursor.fetchone()[0]
				self.db.commit()
				self._closeDB()
				self.lock = False
				return rowcount


	def insert(self, table_name, data):
		if not data.get('cols'):
			return
		if not data.get('values'):
			return

		values = data.get('values')
		data['values']=[values]
		return self.insertMany(table_name, data)
	
		
	"""
		Usage exemple : 
		many = {
			'cols':['lat','lng'],
			'values':[
				[12.5465, 415.6978],
				[12.578925, 47.6978]
			]
		}
		self.insertMany('tracks', many)
	"""
	def insertMany(self, table_name, data):

		if not data.get('cols'):
			return
		if not data.get('values'):
			return

		cols = ', '.join(data.get('cols'))
		cols_nb = len(data.get('cols'))


		while True:
			if self.lock:
				time.sleep(0.05)
			else:
				self.lock = True
				self._openDB()
				for line in data.get('values'):
					if len(line) != cols_nb:
						return

				self.cursor.executemany('INSERT INTO '+ table_name +'('+ cols +') VALUES('+(cols_nb * '?,')[:-1]+')', data.get('values'))
				self.db.commit()
				self._closeDB()
				self.lock = False
				return True

	

	def _getTables(self):
		tables = [
			{'name':'tracks',
			'cols':[
				{'name':'id','type':'INTEGER PRIMARY KEY  AUTOINCREMENT  NOT NULL  UNIQUE'},
				{'name':'lat', 'type':'FLOAT'},
				{'name':'lon', 'type':'FLOAT'},
				{'name':'speed', 'type':'FLOAT'},
				{'name':'alt', 'type':'FLOAT'},
				{'name':'sats', 'type':'INTEGER'},
				{'name':'fix', 'type':'INTEGER'},
				{'name':'temp', 'type':'INTEGER'},
				{'name':'mode', 'type':'INTEGER'},
				#{'name':'origin', 'type':'CHAR'},
				{'name':'timestamp', 'type':'INTEGER'},
				{'name':'other', 'type':'TEXT'}, # json data
				#{'name':'sync', 'type':'INTEGER DEFAULT 0'}
			]
			}
		]
		return tables