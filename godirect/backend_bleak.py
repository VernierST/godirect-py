import logging
from uuid import UUID
import asyncio
from bleak import discover

from .backend import GoDirectBackend
from .device_bleak import GoDirectDeviceBleak

class GoDirectBackendBleak(GoDirectBackend):
	""" Wraper for the bleak module.
	"""
	def __init__(self):
		""" Create a GoDirectBackendBleak object for scanning
		"""
		self._logger = logging.getLogger('godirect')
		
		super().__init__()

	async def _async_scan(self):
		devices = []
		bleak_devices = await discover()
		for d in bleak_devices:
			if d.name[0:3] == 'GDX':
				device = GoDirectDeviceBleak(self)
				device.id = d.address
				device.type = "BLE"
				device.set_name_from_advertisement(d.name)
				device.rssi = d.rssi
				devices.append(device)
		return devices
		
	def scan(self):
		""" Find all GoDirect devices
		Returns:
			GoDirectDevice[]: list of discovered GoDirectDevice objects
		"""
		loop = asyncio.get_event_loop()
		devices = loop.run_until_complete(self._async_scan())
				
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
		""" Connect the device
		Args:
			device: a GoDirectDevice to connect to
		Returns:
			True on success or False
		"""
		return device.connect()

	def stop(self):
		pass
