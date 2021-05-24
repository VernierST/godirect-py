# -*- coding: utf-8 -*-
import logging
import importlib.util
import platform

from .device import GoDirectDevice
from .sensor import GoDirectSensor
from .backend import GoDirectBackend

class GoDirect:
	""" The godirect module wraps the hidapi and bleak modules to create an easy way to
	interact with Vernier GoDirect devices.
	"""

	VERSION = "1.1.0"

	BLE_AUTO_CONNECT_RSSI_THRESHOLD = -50  #closer to zero is a stronger signal

	def __init__(self, use_ble=True, use_ble_bg=False, use_usb=True, ble_com_port=None):
		""" Construct a new 'GoDirect' object and initialize backends
		
		Uses Bleak for BLE. HIDAPI is used for USB.

		Args:
	        use_ble (bool): set to False to disable the BLE backend
			use_ble_bg (bool): manual override to force use of BlueGiga (vernierpygatt over Bleak)
        	use_usb (bool): set to False to disable the USB backend
			ble_com_port (str): set to a COM port to override the auto detection in windows, e.g. 'COM9'
		Returns:
	        returns nothing
        """

		self._logger = logging.getLogger(__name__)
		self._ble_backend = None
		self._usb_backend = None
		self._devices = []
		if use_ble == True:

			if use_ble_bg == False:
				from .backend_bleak import GoDirectBackendBleak
				self._ble_backend = GoDirectBackendBleak()
			else:
				from .backend_ble import GoDirectBackendBLE
				self._ble_backend = GoDirectBackendBLE(ble_com_port)

		if use_usb == True:
			try:
				from .backend_usb import GoDirectBackendUSB
				self._usb_backend = GoDirectBackendUSB()
			except:
				self._logger.error("USB will not work until hidapi is installed.")


	def get_version(self):
		""" Get the library version

		Returns:
			godirect version number (int)
		"""
		return self.VERSION

	def list_devices(self):
		""" List GoDirect devices found by the enabled backends

		Returns:
			GoDirectDevice[]: a list of GoDirectDevice objects
		"""

		self._devices = []
		if self._usb_backend != None:
			self._devices += self._usb_backend.scan()
		if self._ble_backend != None:
			self._devices += self._ble_backend.scan()
		return self._devices

	def get_device(self, threshold=None):
		""" Find first USB device, or if none, the strongest BLE device with
		signal stronger than the threshold

		Args:
			threshold: minimum rssi (-50 is default)

		Returns:
			a GoDirectDevice or None
		"""
		if threshold == None:
			threshold = self.BLE_AUTO_CONNECT_RSSI_THRESHOLD
		if self._usb_backend != None:
			devices = self._usb_backend.scan()
			if len(devices) > 0:
				return devices[0]
		if self._ble_backend != None:
			return self._ble_backend.scan_auto(threshold)
		return None

	def quit(self):
		""" Stop the USB and/or BLE backends

		Returns:
			returns nothing
		"""
		if self._ble_backend != None:
			self._ble_backend.stop()
		if self._usb_backend != None:
			self._usb_backend.stop()
