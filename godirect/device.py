from abc import ABC, abstractmethod
from .sensor import GoDirectSensor

import struct
import logging
import time

class GoDirectDevice(ABC):
	""" GoDirectDevice encapsulates the device information fetched from the GoDirect
	device and also maintains a list of GoDirectSensors objects available on this device.
	Use this class to interact with a GoDirect device.
	"""

	CMD_ID_GET_STATUS                         = 0x10
	CMD_ID_START_MEASUREMENTS                 = 0x18
	CMD_ID_STOP_MEASUREMENTS                  = 0x19
	CMD_ID_INIT                               = 0x1A
	CMD_ID_SET_MEASUREMENT_PERIOD             = 0x1B
	CMD_ID_GET_SENSOR_INFO                    = 0x50
	CMD_ID_GET_SENSOR_AVAILABLE_MASK          = 0x51
	CMD_ID_DISCONNECT                         = 0x54
	CMD_ID_GET_DEVICE_INFO                    = 0x55
	CMD_ID_GET_DEFAULT_SENSORS_MASK           = 0x56

	MEASUREMENT_TYPE_NORMAL_REAL32            = 0x06
	MEASUREMENT_TYPE_WIDE_REAL32              = 0x07
	MEASUREMENT_TYPE_SINGLE_CHANNEL_REAL32    = 0x08
	MEASUREMENT_TYPE_SINGLE_CHANNEL_INT32     = 0x09
	MEASUREMENT_TYPE_APERIODIC_REAL32         = 0x0a
	MEASUREMENT_TYPE_APERIODIC_INT32          = 0x0b
	MEASUREMENT_TYPE_START_TIME               = 0x0c
	MEASUREMENT_TYPE_DROPPED                  = 0x0d
	MEASUREMENT_TYPE_PERIOD                   = 0x0e
	RESPONSE_MEASUREMENT                      = 0x20

	CHARGER_STATE_IDLE     = 0
	CHARGER_STATE_CHARGING = 1
	CHARGER_STATE_COMPLETE = 2
	CHARGER_STATE_ERROR    = 3

	def __init__(self, backend):
		""" This is an abstract base class and cannot be instantiated directly.
		Create a GoDirectDeviceBLE or GoDirectDeviceUSB object instead.
		Args:
			backend: the GoDirectBackend object to use with this device, either
			GoDirectBackendBLE or GoDirectBackendUSB
		"""
		self._backend = backend
		self._rolling_counter = 0xFF
		self._id = None
		self._name = ""
		self._type = None
		self._vid = ""
		self._pid = ""
		self._rssi = ""
		self._status = ""
		self._master_cpu_version = ""
		self._slave_cpu_version = ""
		self._battery_level_percent = 0
		self._charger_state = self.CHARGER_STATE_ERROR
		self._serial_number = ""
		self._order_code = ""
		self._description = ""
		self._mfg_id = ""
		self._mfg_date = ""
		self._ble_addr = ""
		self._nvram_size = 0
		self._sample_period_in_milliseconds = 100000
		self._sensors = {}
		super().__init__()

	def __str__(self):
		""" Returns a pretty str for this device suitable for printing
		"""
		return self._name+" "+self._type+" "+str(self._rssi)

	@abstractmethod
	def is_connected(self):
		pass

	@abstractmethod
	def _connect(self):
		pass

	@abstractmethod
	def _disconnect(self):
		pass

	@abstractmethod
	def _write(self, buff):
		pass

	@abstractmethod
	def _read(self, timeout):
		pass

	def open(self, auto_start = False):
		""" Connect this device and read status/info data to populate the properties
		in this class.
		"""

		if not self._connect():
			return False

		if not self._GDX_init():
			return False
		if not self._GDX_get_status():
			return False
		if not self._GDX_get_device_info():
			return False
		if auto_start:
			self.start()
		return True

	def enable_default_sensors(self):
		""" Enable Default Sensors
		The device's default sensors will be enabled.
		"""
		availableMask = self._GDX_get_available_sensors()
		defaultMask = self._GDX_get_default_sensors()
		testMask = 1
		if not availableMask or not defaultMask:
			return False
		# Select the first sensor number that is called out in the default mask
		for i in range(0,32):
			if testMask & defaultMask & availableMask:
				sensorNumbers = [i]
				break
			testMask = testMask << 1
		if i == 32:
			return False
		self._logger.info("Autoset sensor mask: %i", i)

		for i in sensorNumbers:
			if self._GDX_get_sensor_info(i):
				self.get_sensor(i).enabled =True

		self._check_mutual_exclusion_masks()


	def start(self, period=None):
		""" Start data collection.
		Optionally set the data collection period or use the sensor's typical period.
		If no call to enable_sensors([]) has been made then the device's default sensors
		will be enabled.

		Args:
			Period (int): Set to None to use the typical data rate for the sensor, otherwise pass in the period in ms, e.g. 1000
		Returns:
			bool: True on success or False on failure
		"""

		if len(self.get_enabled_sensors()) == 0:
			self.enable_default_sensors()

		if period == None:
			period = self.get_default_period()
			if period < 100:
			   period = 100
			self._logger.info("Autoset sample period (ms): %i", period)
		self._sample_period_in_milliseconds = period

		for i in self._sensors:
			self._sensors[i].clear()

		if not self._GDX_set_measurement_period(self._sample_period_in_milliseconds):
			return False
		if not self._GDX_start_measurements(self._get_sensor_mask()):
			return False
		return True

	def read(self, timeout=5000):
		""" Once data collection is started the GoDirect device will begin sending data at the specified
		period. You must call read at least as fast as the period, e.g. once per second for a period of 1000 (ms).
		The collected data will be added to a values list for each enabled GoDirectSensor object. The read is blocking so
		you may call this function in a tight loop.

		Returns:
			bool: True on success or False on failure
		"""
		return self._GDX_read_measurement(timeout)

	def stop(self):
		""" Stop data collection on the enabled sensors.

		Returns:
			bool: True on success or False on failure
		"""
		if not self._GDX_stop_measurements():
			return False
		return True

	def close(self):
		""" Disconnect the USB or BLE device handle if a device is open
		"""
		self._GDX_disconnect()
		self._disconnect()

	def list_sensors(self):
		""" List the sensors available on the opened GoDirect device.

		Returns:
			a list of GoDirectSensor objects
		"""
		if not self._GDX_get_sensor_info_all():
			return False
		return self._sensors

	def get_sensor(self, sensor_number):
		""" Add a sensor to the dict of sensors on this device

		Args:
			sensor_number (int): the sensor number to fetch
		"""
		return self._sensors[sensor_number]

	def enable_sensors(self, sensors):
		""" Enable one or more sensors for data collection

		Args:
			sensors (int[]): a list of sensor numbers to enable, e.g. [2,3,4]
		"""
		for i in sensors:
			if self._GDX_get_sensor_info(int(i)):
				self.get_sensor(int(i)).enabled =True

		self._check_mutual_exclusion_masks()

	def get_enabled_sensors(self):
		""" Returns an array of GoDirectSensor objects which are enabled for data collection.
		"""
		sensors = []
		for i in self._sensors:
			if self._sensors[i].enabled:
				sensors.append(self._sensors[i])
		return sensors

	def get_default_period(self):
		""" Returns the typical period (ms) of the first enabled sensor
		"""

		rate = 0
		for i in self._sensors:
			if self._sensors[i].enabled:
				rate = self._sensors[i].typ_measurement_period
				break
		return rate

	def set_name_from_advertisement(self, name):
		""" BLE devices advertise their name, order code, and serial so we can set
		those properties before we even connect. This only sets the name for USB.

		Args:
			name (str): the name from the adverstisement or USB enumeration
		"""

		self._name = name
		parts = self._name.split(" ")
		if len(parts) == 2:
			self._order_code = parts[0]
			self._serial_number = parts[1]

	###########################################################################
	# GDX internal
	###########################################################################

	def _get_sensors_with_mask(self, sensor_mask):
		sensors = {}
		mask = 1
		for i in range(0,32):
			if (mask & sensor_mask) == mask:
				sensors[i] = self._sensors[i]
			mask = mask << 1
		return sensors

	def _get_sensor_mask(self):
		sensor_mask = 0
		for i in self._sensors:
			if self._sensors[i].enabled:
				sensor_mask += (1 << self._sensors[i].sensor_number)
		return sensor_mask

	def _check_mutual_exclusion_masks(self):
		enabled_sensors = self.get_enabled_sensors()
		for sensor in enabled_sensors:
			#sensor = enabled_sensors[s]
			for sensor2 in enabled_sensors:
				#sensor2 = enabled_sensors[s2]
				if not sensor._check_mutual_exclusion_mask(sensor2.sensor_number):
					self._logger.info("This sensor should be disabled: %i",sensor2.sensor_number)
					sensor2.enabled = False

	def _GDX_get_sensor_info_all(self):
		availableMask = self._GDX_get_available_sensors()
		testMask = 1
		if not availableMask:
			return False
		for i in range(0,32):
			if testMask & availableMask:
				if not self._GDX_get_sensor_info(i):
					return False
			testMask = testMask << 1;
		return True

	def _GDX_dec_rolling_counter(self):
		self._rolling_counter -= 1
		# Roll over to behave like an unsigned byte
		if self._rolling_counter == -1:
			self._rolling_counter = 0xFF
		return self._rolling_counter

	def _GDX_calculate_checksum(self, buff):
		length = int(buff[1])
		checksum = -1 * int(buff[3])

		for i in range(0,length):
			checksum += int(buff[i])
			checksum = checksum & 0xFF

		if checksum < 0 or checksum > 255:
			self._logger.error("Checksum failed!")
			return 0

		return checksum;

	def _GDX_dump(self, strPrefix, buff):
		str = strPrefix
		str += " ".join( [ "%02X " % c for c in buff ] ).strip()
		self._logger.debug(str)

	def _GDX_write(self, buff):
		self._GDX_dump("GDX >> ", buff);
		return self._write(buff)

	def _GDX_read_blocking(self, timeout=5000):
		response = self._read(timeout)
		self._GDX_dump("GDX << ", response);
		return response

	def _GDX_write_and_get_response(self, buff):
		if not self._GDX_write(buff):
			return False
		timeout = 5000
		start_time = time.time()
		while True:
			timeout = timeout - (time.time() - start_time) * 1000
			if timeout < 1:
				self._logger.info("Timeout in _GDX_write_and_get_response")
				break
			response = self._GDX_read_blocking(timeout=timeout)
			if len(response) < 2:
				continue
			if response[0] == self.RESPONSE_MEASUREMENT:
				self._GDX_handle_measurement(response)
				continue
			return response
		return None

	def _GDX_write_and_check_response(self, buff):
		if not self._GDX_write(buff):
			return False
		timeout = 5000
		start_time = time.time()
		while True:
			timeout = timeout - (time.time() - start_time)*1000
			if timeout < 1:
				self._logger.info("Timeout in _GDX_write_and_check_response")
				break
			response = self._GDX_read_blocking(timeout=timeout)
			if len(response) < 2:
				continue
			if response[0] == self.RESPONSE_MEASUREMENT:
				self._GDX_handle_measurement(response)
				continue
			return True
		return False

	def _GDX_read_measurement(self, timeout):
		start_time = time.time()
		timedout = False
		while True:
			timeout = timeout - (time.time() - start_time) * 1000
			if timeout < 1:
				self._logger.info("Timeout in _GDX_read_measurement")
				timedout = True
				break
			response = self._GDX_read_blocking(timeout)
			if len(response) < 5:
				self._logger.info("Packet too short")
				continue
			if response[0] != self.RESPONSE_MEASUREMENT:
				self._logger.info("Not a measurement packet")
				continue
			measurement_type = response[4]
			if measurement_type == self.MEASUREMENT_TYPE_START_TIME or measurement_type == self.MEASUREMENT_TYPE_DROPPED or measurement_type == self.MEASUREMENT_TYPE_PERIOD:
				self._logger.info("Ignoring non-supported measurement type")
				continue
			break
		if timedout == True:
			return False
		return self._GDX_handle_measurement(response)

	def _GDX_handle_measurement(self, response):
		self._GDX_dump("MEASUREMENT: ", response)

		value_count = 0
		sensors = []
		format_str = "<f"
		index = 0

		measurement_type = response[4]
		if measurement_type == self.MEASUREMENT_TYPE_NORMAL_REAL32:
			self._GDX_dump("REAL32: ", response[9:])
			sensor_mask = struct.unpack("<H",response[5:7])[0]
			value_count = struct.unpack("<b",response[7:8])[0]
			sensors = self._get_sensors_with_mask(sensor_mask)
			index = 9
		elif measurement_type == self.MEASUREMENT_TYPE_WIDE_REAL32:
			self._GDX_dump("WIDE REAL32: ", response[11:])
			sensor_mask = struct.unpack("<HH",response[5:9])[0]
			value_count = struct.unpack("<b",response[9:10])[0]
			sensors = self._get_sensors_with_mask(sensor_mask)
			index = 11
		elif measurement_type == self.MEASUREMENT_TYPE_SINGLE_CHANNEL_REAL32 or measurement_type == self.MEASUREMENT_TYPE_APERIODIC_REAL32:
			self._GDX_dump("SINGLE REAL32: ", response[8:])
			sensor_number = struct.unpack("<b",response[6:7])[0]
			value_count = struct.unpack("<b",response[7:8])[0]
			index = 8
			sensors[0] = self._sensors[sensor_number]
		elif measurement_type == self.MEASUREMENT_TYPE_SINGLE_CHANNEL_INT32 or measurement_type == self.MEASUREMENT_TYPE_APERIODIC_INT32:
			self._GDX_dump("SINGLE INT32: ", response[8:])
			sensor_number = struct.unpack("<b",response[6:7])[0]
			value_count = struct.unpack("<b",response[7:8])[0]
			index = 8
			format_str = "<i"
			sensors[0] = self._sensors[sensor_number]
		else:
			self._logger.info("Unknown measurement type")
			return False

		count = 0 
		while count < value_count:
			for i in sensors:
				measurement = struct.unpack(format_str,response[index:index+4])[0]
				sensors[i].values.append(measurement)
				index += 4
			count += 1

		return True

	############################################################################
	# GDX Commands
	############################################################################

	def _GDX_init(self):
		command = [
				   0x58, 0x00, 0x00, 0x00, self.CMD_ID_INIT,
				   0xa5, 0x4a, 0x06, 0x49,
				   0x07, 0x48, 0x08, 0x47,
				   0x09, 0x46, 0x0a, 0x45,
				   0x0b, 0x44, 0x0c, 0x43,
				   0x0d, 0x42, 0x0e, 0x41
				   ]

		# Reset the rolling packet counter
		self._rolling_counter = 0xFF

		# Populate the packet header bytes
		command[1] = len(command)
		command[2] = self._GDX_dec_rolling_counter()
		command[3] = self._GDX_calculate_checksum(command)

		return self._GDX_write_and_check_response(command)

	def _GDX_set_measurement_period(self, measurementPeriodInMilliseconds):
		command = [
			0x58, 0x00, 0x00, 0x00, self.CMD_ID_SET_MEASUREMENT_PERIOD,
			0xFF, 0x00,
			0x00, 0x00, 0x00, 0x00,
			0x00, 0x00, 0x00, 0x00
		]

		# Convert to milliseconds and populate the payload
		measurementPeriodInMicroseconds =int(measurementPeriodInMilliseconds * 1000)
		command[7]  = (measurementPeriodInMicroseconds >> 0)  & 0xFF
		command[8]  = (measurementPeriodInMicroseconds >> 8)  & 0xFF
		command[9]  = (measurementPeriodInMicroseconds >> 16) & 0xFF
		command[10] = (measurementPeriodInMicroseconds >> 24) & 0xFF

		# Populate the packet header bytes
		command[1] = len(command)
		command[2] = self._GDX_dec_rolling_counter()
		command[3] = self._GDX_calculate_checksum(command)

		return self._GDX_write_and_check_response(command)

	def _GDX_get_available_sensors(self):
		command = [0x58, 0x00, 0x00, 0x00, self.CMD_ID_GET_SENSOR_AVAILABLE_MASK]

		# Populate the packet header bytes
		command[1] = len(command)
		command[2] = self._GDX_dec_rolling_counter()
		command[3] = self._GDX_calculate_checksum(command)

		response = self._GDX_write_and_get_response(command)
		if response == None:
			return False

		# Extract the sensor mask from the packet
		mask = struct.unpack("<I", response[6:])[0]
		sensors = str(format(mask,'032b')).count('1')
		self._logger.info("Available sensors: %i", sensors)
		return mask

	def _GDX_get_default_sensors(self):
		command = [0x58, 0x00, 0x00, 0x00, self.CMD_ID_GET_DEFAULT_SENSORS_MASK]

		# Populate the packet header bytes
		command[1] = len(command)
		command[2] = self._GDX_dec_rolling_counter()
		command[3] = self._GDX_calculate_checksum(command)

		response = self._GDX_write_and_get_response(command)
		if response == None:
			return False

		# Extract the sensor mask from the packet
		mask = struct.unpack("<I", response[6:])[0]
		default = str(format(mask,'032b')).count('1')
		self._logger.info("Default sensor: %i", default)
		return mask

	def _GDX_get_sensor_info(self, sensor_number):
		command = [0x58, 0x00, 0x00, 0x00, self.CMD_ID_GET_SENSOR_INFO, 0x00]

		# Specify the sensor number parameter
		command[5] = sensor_number

		# Populate the packet header bytes
		command[1] = len(command)
		command[2] = self._GDX_dec_rolling_counter()
		command[3] = self._GDX_calculate_checksum(command)

		response = self._GDX_write_and_get_response(command)
		if response == None:
			return False

		info_struct = "<bBIBB60s32sdddIQIII"
		info = struct.unpack(info_struct, response[6:])
		(sensorNumber,spare,sensorId,numericMeasType,samplingMode,
		 sensorDescription,sensorUnit,measurementUncertainty,
		 minMeasurement,maxMeasurement,minMeasurementPeriod,maxMeasurementPeriod,typMeasurementPeriod,
		 measurementPeriodGranularity,mutualExclusionMask) = info

		sensor = GoDirectSensor(info)
		self._sensors[sensor._sensor_number] = sensor

		self._logger.info("Sensor[%i] info:",sensorNumber)
		self._logger.info("  Description: %s", sensorDescription.decode("utf-8"))
		self._logger.info("  ID: %s", sensorId)
		self._logger.info("  Measurement type: %s", numericMeasType)
		self._logger.info("  Sampling mode: %s", samplingMode)
		self._logger.info("  Units: %s", sensorUnit.decode("utf-8"))
		self._logger.info("  Measurement uncertainty: %i", measurementUncertainty)
		self._logger.info("  Measurement min: %i", minMeasurement)
		self._logger.info("  Measurement max: %i", maxMeasurement)
		self._logger.info("  Period typical %i", typMeasurementPeriod)
		self._logger.info("  Period min: %i", minMeasurementPeriod)
		self._logger.info("  Period max: %i", maxMeasurementPeriod)
		self._logger.info("  Period granularity: %i", measurementPeriodGranularity)
		self._logger.info("  Mutual exclusion mask: 0x%i", mutualExclusionMask)

		return True

	def _GDX_start_measurements(self, sensor_mask):
		command = [
			0x58, 0x00, 0x00, 0x00, self.CMD_ID_START_MEASUREMENTS,
			0xFF,
			0x01,
			0x00, 0x00, 0x00, 0x00,
			0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
		]

		command[7]  = (sensor_mask >> 0)  & 0xFF
		command[8]  = (sensor_mask >> 8)  & 0xFF
		command[9]  = (sensor_mask >> 16) & 0xFF
		command[10] = (sensor_mask >> 24) & 0xFF

		# Populate the packet header bytes
		command[1] = len(command)
		command[2] = self._GDX_dec_rolling_counter()
		command[3] = self._GDX_calculate_checksum(command)

		return self._GDX_write_and_check_response(command)

	def _GDX_stop_measurements(self):
		command = [
			0x58, 0x00, 0x00, 0x00, self.CMD_ID_STOP_MEASUREMENTS,
			0xFF,
			0x00,
			0xFF, 0xFF, 0xFF, 0xFF
		]

		# Populate the packet header bytes
		command[1] = len(command)
		command[2] = self._GDX_dec_rolling_counter()
		command[3] = self._GDX_calculate_checksum(command)

		return self._GDX_write_and_check_response(command)

	def _GDX_get_status(self):
		command = [0x58, 0x00, 0x00, 0x00, self.CMD_ID_GET_STATUS]

		# Populate the packet header bytes
		command[1] = len(command)
		command[2] = self._GDX_dec_rolling_counter()
		command[3] = self._GDX_calculate_checksum(command)

		response = self._GDX_write_and_get_response(command)
		if response == None:
			return False

		status_struct = '<xxxxxxBBBBHBBHBB'
		info = struct.unpack(status_struct, response)
		(status,spare,
		 majorVersionMasterCPU,minorVersionMasterCPU,buildNumMasterCPU,
		 majorVersionSlaveCPU,minorVersionSlaveCPU,buildNumSlaveCPU,
		 batteryLevelPercent,chargerState) = info

		self._status = status
		self._master_cpu_version = str(majorVersionMasterCPU)+'.'+str(minorVersionMasterCPU)+'.'+str(buildNumMasterCPU)
		self._slave_cpu_version = str(majorVersionSlaveCPU)+'.'+str(minorVersionSlaveCPU)+'.'+str(buildNumSlaveCPU)
		self._battery_level_percent = batteryLevelPercent
		self._charger_state = chargerState

		self._logger.info("Device status:")
		self._logger.info("  Status: %i", status)
		self._logger.info("  Master FW version: %i%s%i%s%i", majorVersionMasterCPU,".",minorVersionMasterCPU,".",buildNumMasterCPU)
		self._logger.info("  Slave FW version: %i%s%i%s%i", majorVersionSlaveCPU,".",minorVersionSlaveCPU,".",buildNumSlaveCPU)
		self._logger.info("  Battery percent: %i%s", batteryLevelPercent,'%')
		self._logger.info("  Charger state: %i", chargerState)

		return True

	def _GDX_get_device_info(self):
		command = [0x58, 0x00, 0x00, 0x00, self.CMD_ID_GET_DEVICE_INFO]

		# Populate the packet header bytes
		command[1] = len(command)
		command[2] = self._GDX_dec_rolling_counter()
		command[3] = self._GDX_calculate_checksum(command)

		response = self._GDX_write_and_get_response(command)
		if response == None:
			return False

		info_struct = "<xxxxxx16s16s32sHHBBBBHBBHBBBBBBI64s"
		info = struct.unpack(info_struct, response)
		(OrderCode,SerialNumber,DeviceName,
		 manufacturerId,manufacturedYear,ManufacturedMonth,ManufacturedDay,
		 majorVersionMasterCPU,minorVersionMasterCPU,buildNumMasterCPU,
		 majorVersionSlaveCPU,minorVersionSlaveCPU,buildNumSlaveCPU,
		 Addr5,Addr4,Addr3,Addr2,Addr1,Addr0,
		 NVMemSize,DeviceDescription) = info

		self._description = DeviceDescription.decode("utf-8").replace('\x00','')
		self._order_code = OrderCode.decode("utf-8").replace('\x00','')
		self._serial_number = SerialNumber.decode("utf-8").replace('\x00','')
		self._mfg_id = manufacturerId
		self._name = DeviceName.decode("utf-8").replace('\x00','')
		self._mfg_date = str(ManufacturedMonth)+"/"+str(ManufacturedDay)+"/"+str(manufacturedYear)
		self._ble_addr = format(Addr0,'02x')+":"+format(Addr1,'02x')+":"+format(Addr2,'02x')+":"+format(Addr3,'02x')+":"+format(Addr4,'02x')+":"+format(Addr5,'02x')
		self._nvram_size = NVMemSize

		self._logger.info("Device info:")
		self._logger.info("  Description: %s", DeviceDescription.decode("utf-8"))
		self._logger.info("  Order code: %s", OrderCode.decode("utf-8"))
		self._logger.info("  Serial number: %s", SerialNumber.decode("utf-8"))
		self._logger.info("  Device name: %s", DeviceName.decode("utf-8"))
		self._logger.info("  Mfg ID: %s", manufacturerId)
		self._logger.info("  Mfg Date: %i%s%i%s%i",ManufacturedMonth,"/",ManufacturedDay,"/",manufacturedYear)
		self._logger.info("  Master FW version: %i%s%i%s%i",majorVersionMasterCPU,".",minorVersionMasterCPU,".",buildNumMasterCPU)
		self._logger.info("  Slave FW version: %i%s%i%s%i",majorVersionSlaveCPU,".",minorVersionSlaveCPU,".",buildNumSlaveCPU)
		self._logger.info("  BLE address: %s%s%s%s%s%s%s%s%s%s%s",format(Addr0,'02x'),":",format(Addr1,'02x'),":",format(Addr2,'02x'),":",format(Addr3,'02x'),":",format(Addr4,'02x'),":",format(Addr5,'02x'))
		self._logger.info("  NVRAM size: %i%s",NVMemSize, 'bytes')

		return True

	def _GDX_disconnect(self):
		command = [
			0x58, 0x00, 0x00, 0x00, self.CMD_ID_DISCONNECT
		]

		# Populate the packet header bytes
		command[1] = len(command)
		command[2] = self._GDX_dec_rolling_counter()
		command[3] = self._GDX_calculate_checksum(command)

		return self._GDX_write_and_check_response(command)



	# Properties

	@property
	def sensors(self):
		""" dict: {sensor_number => GoDirectSensor}
		"""
		return self._sensors

	@property
	def id(self):
		""" object: unique ID for this device used by the backends to list/open devices.
				The USB backend uses the HID path while the BLE backend uses the MAC address.
		"""
		return self._id
	@id.setter
	def id(self, value):
		self._id = value

	@property
	def name(self):
		""" str: the name of the device. For BLE this is the GoDirect sensor name, but USB devcies all have the same name.
		"""
		return self._name
	@name.setter
	def name(self, value):
		self._name = value

	@property
	def type(self):
		""" str: 'BLE' or 'USB'
		"""
		return self._type
	@type.setter
	def type(self, value):
		self._type = value

	@property
	def vid(self):
		""" int: the USB VID, only valid for USB devices
		"""
		return self._vid
	@vid.setter
	def vid(self, value):
		self._vid = value

	@property
	def pid(self):
		""" int: the USB PID, only valid for USB devices
		"""
		return self._pid
	@pid.setter
	def pid(self, value):
		self._pid = value

	@property
	def rssi(self):
		""" int: the BLE RSSI signal strength in dB
		"""
		return self._rssi
	@rssi.setter
	def rssi(self, value):
		self._rssi = value

	@property
	def status(self):
		return self._status

	@property
	def master_cpu_version(self):
		""" str: the device firmware version
		"""
		return self._master_cpu_version

	@property
	def slave_cpu_version(self):
		""" str: the BLE firmware version
		"""
		return self._slave_cpu_version

	@property
	def battery_level_percent(self):
		""" int: % of battery remaining
		"""
		return self._battery_level_percent

	@property
	def charger_state(self):
		""" int:  0 = Idle, 1 = Charging, 2 = Complete, 3 = Error
		"""
		return self._charger_state

	@property
	def serial_number(self):
		""" str: the device serial number
		"""
		return self._serial_number

	@property
	def order_code(self):
		""" str: the Vernier order code for this device
		"""
		return self._order_code

	@property
	def description(self):
		""" str: device description
		"""
		return self._description

	@property
	def mfg_id(self):
		return self._mfg_id

	@property
	def mfg_date(self):
		return self._mfg_date

	@property
	def ble_addr(self):
		""" str: BLE MAC address
		"""
		return self._ble_addr

	@property
	def nvram_size(self):
		return self._nvram_size

	@property
	def sample_period_in_milliseconds(self):
		""" int: the period that will be used for data collection (ms)
		"""
		return self._sample_period_in_milliseconds
	@sample_period_in_milliseconds.setter
	def sample_period_in_milliseconds(self, value):
		self._sample_period_in_milliseconds = value
