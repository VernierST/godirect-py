class GoDirectSensor:
	""" GoDirectSensor encapsulates the sensor information fetched from the GoDirect
	device for each sensor. This class also maintains a list of measurmenets
	read from the sensor.
	"""

	def __init__(self, info):
		""" Create a GoDirectSensor object.

		Args:
			info: list of sensor information read from the device
		"""
		(number,spare,sensorId,numericMeasType,samplingMode,
		 sensorDescription,sensorUnit,measurementUncertainty,
		 minMeasurement,maxMeasurement,minMeasurementPeriod,maxMeasurementPeriod,typMeasurementPeriod,
		 measurementPeriodGranularity,mutualExclusionMask) = info

		self._sensor_number = number
		self._sensor_description = sensorDescription.decode("utf-8").replace('\x00','')
		self._sensor_id = sensorId
		self._numeric_measurement_type = numericMeasType
		self._sampling_mode = samplingMode
		self._sensor_units = sensorUnit.decode("utf-8").replace('\x00','')
		self._measurement_uncertainty = measurementUncertainty
		self._min_measurement = minMeasurement
		self._max_measurement = maxMeasurement
		self._typ_measurement_period = typMeasurementPeriod / 1000
		self._min_measurement_period = minMeasurementPeriod / 1000
		self._max_measurement_period = maxMeasurementPeriod / 1000
		self._measurement_period_granularity = measurementPeriodGranularity / 1000
		self._mutual_exclusion_mask = mutualExclusionMask
		self._enabled = False
		self._values = []

	def _check_mutual_exclusion_mask(self, sensor_number):
		""" Verify that no other sensors are enabled that are mutually exclusive
		with this sensor.

		Args:
			sensor_number: the sensor number to check
		Returns:
			True if there are no violations, False if a mutually exclusive sensor is enabled
		"""
		if sensor_number == self._sensor_number:
			return True
		mask = 1 << sensor_number
		if (mask & self._mutual_exclusion_mask) == mask:
			return False
		return True

	def __str__(self):
		""" Returns a pretty str for this sensor suitable for printing
		"""
		return str(self.sensor_number)+": "+self.sensor_description+" ("+self.sensor_units+")"

	def clear(self):
		""" Clear the values list
		"""
		self._values.clear()

	@property
	def value(self):
		""" float: get the latest measurment read from the sensor or 0 if no measurments have been read
		"""
		if len(self._values) > 0:
			return self._values[-1]
		return 0.0

	@property
	def values(self):
		""" float[]: a list of values collected from the sensor
		"""
		return self._values

	@property
	def sensor_number(self):
		""" int: the sensor number of this sensor, used for selecting sensors to start data collection
		"""
		return self._sensor_number

	@property
	def sensor_description(self):
		""" str: the name of this sensor, e.g. 'Force'
		"""
		return self._sensor_description

	@property
	def sensor_id(self):
		""" str: the sensor id
		"""
		return self._sensor_id

	@property
	def numeric_measurement_type(self):
		""" int: 0 = Real64, 1 = Int32
		"""
		return self._numeric_measurement_type
 
	@property
	def sampling_mode(self):
		"""  int: 0 = Periodic, 1 = APeriodic
		"""
		return self._sampling_mode

	@property
	def sensor_units(self):
		""" str: the units used for this sensor, e.g. 'N'
		"""
		return self._sensor_units

	@property
	def measurement_uncertainty(self):
		""" float: the expected uncertainty of each measurement in sensor units
		"""
		return self._measurement_uncertainty

	@property
	def min_measurement(self):
		""" float: the smallest measurement expected in sensor units
		"""
		return self._min_measurement

	@property
	def max_measurement(self):
		""" float: the largest measurment expected in sensor units
		"""
		return self._max_measurement

	@property
	def typ_measurement_period(self):
		""" int: the typical measurment period in ms, used by start() method with no
		period specified.
		"""
		return self._typ_measurement_period

	@property
	def min_measurement_period(self):
		""" int: the smallest measurment period allowed, in ms
		"""
		return self._min_measurement_period

	@property
	def max_measurement_period(self):
		""" int: the largest measurment period allowed, in ms
		"""
		return self._max_measurement_period

	@property
	def measurement_period_granularity(self):
		""" int: the granularity of the measurment period allowed, in ms
		"""
		return self._measurement_period_granularity

	@property
	def mutual_exclusion_mask(self):
		""" int: a sensor mask that determines which sensors cannot be enabled
		simultaneously
		"""
		return self._mutual_exclusion_mask

	@property
	def enabled(self):
		""" bool: True if the sensor is enabled, False if it wont be used in data collection
		"""
		return self._enabled
	@enabled.setter
	def enabled(self, value):
		self._enabled = value
