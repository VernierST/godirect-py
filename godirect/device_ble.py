import logging
import queue
from uuid import UUID

from .device import GoDirectDevice

class GoDirectDeviceBLE(GoDirectDevice):
	""" GoDirectDeviceBLE overrides GoDirectDevice with BLE specific functions for connecting,
	disconnecting, writing, and reading.
	"""

	def __init__(self, backend):
		""" Create a GoDirectBackendBLE object
		Args:
			backend: the GoDirectBackend object to use with this device, should be
			GoDirectBackendBLE
		"""
		self._logger = logging.getLogger('godirect')
		self._device = None
		self._responses = queue.Queue()
		self._response_buffer = bytearray()
		super().__init__(backend)

	def is_connected(self):
		""" Returns True if connected, False otherwise.
		"""
		if self._device == None:
			return False
		return True

	def _connect(self):
		""" Open this device
		Returns:
			True on success, False otherwise
		"""
		self._device = self._backend.connect(self)
		self._discover_services()
		return True

	def _disconnect(self):
		""" Close this device
		"""
		self._device.disconnect()
		self._device = None

	def _write(self, buff):
		""" Write data to this device
		Args:
			buff: byte[] data to send
		"""
		lengthRemaining = int(buff[1])
		offset = 0

		while lengthRemaining > 0:
			lengthChunk = lengthRemaining
			if lengthChunk > 20:
				lengthChunk = 20

			data_to_write = buff[offset:(offset+lengthChunk)]

			str = "BLE WRITE: >>>"
			str += " ".join( [ "%02X " % c for c in data_to_write ] ).strip()
			self._logger.debug(str)

			try:
				self._device.char_write(self._char_command, data_to_write, wait_for_response=False)
			except:
				self._logger.debug("ERROR: BLE write failed")
				return False

			lengthRemaining = lengthRemaining - lengthChunk
			offset = offset + lengthChunk

			self._logger.debug("lengthRemaining %i offset %i", lengthRemaining, offset)
		return True

	def _read(self, timeout):
		""" Read data from this device while blocking for up to timeout ms
		Args:
			timeout: ms to wait for data before failing the read
		Returns:
			bytearray: data received from device
		"""
		try:
			response = self._responses.get(block=True,timeout=timeout)
		except:
			return bytearray()

		str = "BLE READ: <<<"
		str += " ".join( [ "%02X " % c for c in response ] ).strip()
		self._logger.debug(str)
		return response

	def _discover_services(self):
		#uuidService  = "d91714ef-28b9-4f91-ba16-f0d9a604f112"
		uuidCommand  = UUID("f4bf14a6-c7d5-4b6d-8aa8-df1a7c83adcb")
		uuidResponse = UUID("b41e6675-a329-40e0-aa01-44d2f444babe")

		self._logger.debug("Discovering characteristics ...")

		chars = self._device.discover_characteristics()

		if uuidCommand in chars:
			self._logger.debug("Found GDX command characteristic %s", uuidCommand)
			self._char_command = uuidCommand
		else:
			self._logger.error("ERROR: GDX command characteristic discovery failed!")
			return False

		if uuidResponse in chars:
			self._logger.debug("Found GDX response characteristic %s", uuidResponse)
			self._char_response = uuidResponse
		else:
			self._logger.error("ERROR: GDX response characteristic discovery failed!")
			return False

		try:
			self._device.subscribe(uuidResponse, callback=self._notify_callback)
			self._logger.debug("Subscribed to GDX response notifications")
		except:
			self._logger.error("ERROR: subscribe to GDX response failed!")
			return False

		return True

	def _notify_callback(self, handle, value):
		str = "BLE NOTIFY: <<<"
		str += " ".join( [ "%02X " % c for c in value ] ).strip()
		self._logger.debug(str)

		self._response_buffer += value
		buflen = len(self._response_buffer)

		# Check if we have received the complete packet
		self._logger.debug("Recieve buffer length: %i Expected packet length: %i",len,int(self._response_buffer[1]))

		if buflen >= 1 and buflen == int(self._response_buffer[1]):
			self._responses.put(self._response_buffer, block=True, timeout=5000)
			self._response_buffer = bytearray()
