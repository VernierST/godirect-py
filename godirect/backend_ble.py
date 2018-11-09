import pygatt
import logging
from uuid import UUID

from .backend import GoDirectBackend
from .device_ble import GoDirectDeviceBLE

class GoDirectBackendBLE(GoDirectBackend):
	""" Wraper for the pygatt module using the BGAPI backend.
	"""
	def __init__(self, com_port=None):
		""" Create a GoDirectBackendBLE object for managing the pygatt BGAPI backend
		Args:
			com_port (str): None for autodetection, or COM port used by the BLE dongle e.g. 'COM9'
		"""

		self._logger = logging.getLogger('godirect')
		self._adapter = None
		if com_port != None:
			self._adapter = pygatt.BGAPIBackend(serial_port=com_port)
		else:
			self._adapter = pygatt.BGAPIBackend()
		self._adapter.start()
		super().__init__()

	def scan(self):
		""" Find all GoDirect devices
		Returns:
			GoDirectDevice[]: list of discovered GoDirectDevice objects
		"""
		devices = []
		for d in self._adapter.scan(timeout=5):
			if d['name'][0:3] == 'GDX':
				device = GoDirectDeviceBLE(self)
				device.id = d['address']
				device.type = "BLE"
				device.set_name_from_advertisement(d['name'])
				device.rssi = d['rssi']
				devices.append(device)
		return devices

	def scan_auto(self, threshold):
		""" Find strongest GoDirect device with signal stronger than threshold
		Args:
			threshold: minimum rssi value in dB, default is -50
		Returns:
			GoDirectDevice: a GoDirectDevice object or None
		"""
		devices = self.scan()
		strongest_device = None
		strongest_rssi = -1000
		for device in devices:
			self._logger.debug("Found "+device.name+" at "+device.id+" with RSSI "+str(device.rssi))
			if int(device.rssi) > strongest_rssi:
				strongest_rssi = int(device.rssi)
				self._logger.debug("Set strongest RSSI to %i",strongest_rssi)
				strongest_device = device
		if strongest_device != None and int(strongest_device.rssi) > threshold:
			return strongest_device
		return None

	def connect(self, device):
		""" Connect the BGAPI adapter to the device
		Args:
			device: a GoDirectDevice to connect to
		Returns:
			True on success or False
		"""
		return self._adapter.connect(device.id)

	def stop(self):
		""" Stop the BGAPI adapter
		"""
		self._adapter.stop()
