import hid
import logging

from .backend import GoDirectBackend
from .device_usb import GoDirectDeviceUSB

class GoDirectBackendUSB(GoDirectBackend):
	VID = 0x08f7
	PID = 0x0010

	def __init__(self):
		""" Create a GoDirectBackendUSB object for wrapping the hidapi module.
		"""
		self._logger = logging.getLogger('godirect')

	def scan(self):
		""" Find all GoDirect devices
		Returns:
			GoDirectDevice[]: list of discovered GoDirectDevice objects
		"""
		devices = []
		for d in hid.enumerate(self.VID, self.PID):
			device = GoDirectDeviceUSB(self)
			device.id = d['path']
			device.vid = self.VID
			device.pid = self.PID
			device.type = "USB"
			device.name = d['product_string']
			devices.append(device)
		return devices

	def scan_auto(self, threshold):
		pass

	def connect(self, device):
		pass

	def stop(self):
		pass
