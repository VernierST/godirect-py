import logging
import queue
from uuid import UUID
from bleak import BleakClient
import asyncio
import traceback

from .device import GoDirectDevice

class GoDirectDeviceBleak(GoDirectDevice):
	""" GoDirectDeviceBleak overrides GoDirectDevice with bleak module functions for connecting,
	disconnecting, writing, and reading. The bleak module supports native BLE radios.
	"""
	uuidCommand  = UUID("f4bf14a6-c7d5-4b6d-8aa8-df1a7c83adcb")
	uuidResponse = UUID("b41e6675-a329-40e0-aa01-44d2f444babe")

	def __init__(self, backend):
		""" Create a GoDirectBackendBleak object
		Args:
			backend: the GoDirectBackend object to use with this device, should be
			GoDirectBackendBleak
		"""
		self._logger = logging.getLogger('godirect')
		self._device = None
		self._responses = queue.Queue()
		self._response_buffer = bytearray()
		self._loop = asyncio.get_event_loop()
		super().__init__(backend)
		
	def is_connected(self):
		""" Returns True if connected, False otherwise.
		"""
		return self._device.is_connected
	
	async def _async_connect(self):
		await self._device.connect()
		x = self._device.is_connected
		if not x:
			return False
			
		await self._device.start_notify(self.uuidResponse, self._notify_callback)

	def _connect(self):
		""" Open this device
		Returns:
			True on success, False otherwise
		"""
		self._device = BleakClient(self._id, loop=self._loop)
		self._loop.run_until_complete(self._async_connect())
		return True

	async def _async_disconnect(self):
		await self._device.stop_notify(self.uuidResponse)
		await self._device.disconnect()
		
	def _disconnect(self):
		""" Close this device
		"""
		if self._device != None:
			self._loop.run_until_complete(self._async_disconnect())
		self._device = None

	async def _async_write(self, uuid, data_to_write, wait_for_response):
		data_to_write = bytes(data_to_write)
		await self._device.write_gatt_char(uuid, data_to_write, wait_for_response) 
		
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
				self._loop.run_until_complete(self._async_write(self.uuidCommand, data_to_write, wait_for_response=False))
			except:
				self._logger.debug("ERROR: BLE write failed")
				traceback.print_exc()
				return False

			lengthRemaining = lengthRemaining - lengthChunk
			offset = offset + lengthChunk

			self._logger.debug("lengthRemaining %i offset %i", lengthRemaining, offset)
		return True

	async def _wait(self):
		await asyncio.sleep(0.01, self._loop)

	def _read(self, timeout):
		""" Read data from this device while blocking for up to timeout ms
		Args:
			timeout: ms to wait for data before failing the read
		Returns:
			bytearray: data received from device
		"""

		response = None
		for i in range(0,int(timeout/10)):
			try:
				response = self._responses.get(block=False)
				break
			except:
				self._loop.run_until_complete(self._wait())

		if response == None:
			return bytearray()

		str = "BLE READ: <<<"
		str += " ".join( [ "%02X " % c for c in response ] ).strip()
		self._logger.debug(str)
		return response

	def _discover_services(self):
		return True

	def _notify_callback(self, handle, value):
		str = "BLE NOTIFY: <<<"
		str += " ".join( [ "%02X " % c for c in value ] ).strip()
		self._logger.debug(str)

		self._response_buffer += value
		buflen = len(self._response_buffer)

		# Check if we have received the complete packet
		self._logger.debug("Receive buffer length: %i Expected packet length: %i",buflen,int(self._response_buffer[1]))

		if buflen >= 1 and buflen == int(self._response_buffer[1]):
			self._responses.put(self._response_buffer, block=True, timeout=5000)
			self._response_buffer = bytearray()
