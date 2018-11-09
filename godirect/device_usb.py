import hid
import logging

from .device import GoDirectDevice

class GoDirectDeviceUSB(GoDirectDevice):
	""" GoDirectDeviceUSB overrides GoDirectDevice with USB specific functions for connecting,
	disconnecting, writing, and reading.
	"""

	VID = 0x08f7
	PID = 0x0010

	def __init__(self, backend):
		""" Create a GoDirectDeviceUSB object
		Args:
			backend: the GoDirectBackend object to use with this device, should be
			GoDirectBackendUSB
		"""
		self._logger = logging.getLogger('godirect')
		self._device = None
		self._connected = False
		super().__init__(backend)

	def is_connected(self):
		""" Returns True if connected, False otherwise.
		"""
		return self._connected

	def _connect(self):
		""" Open this device
		Returns:
			True on success, False otherwise
		"""
		#self._device = hid.device().open(self.VID, self.PID)
		self._connected = False
		self._device = hid.device()
		self._device.open_path(self._id)
		if self._device == None:
			self._connected = False
			return False
		self._connected = True
		return True

	def _disconnect(self):
		""" Close this device
		"""
		self._connected = False
		try:
			self._device.close()
		except:
			self._logger.error("hid close failed")

	def _write(self, buff):
		""" Write data to this device
		Args:
			buff: byte[] data to send
		"""
		packet = []
		# Leading zero is required by hidapi for the Report ID
		packet.append(0)
		# Tell GDX the real packet length
		packet.append(len(buff))
		for i in range(0,len(buff)):
			packet.append(buff[i])

		# hidapi requires 64 byte packets (+ the Report ID leading byte)
		for i in range(len(packet),65):
			packet.append(0)
		self._device.write(packet)

		str = "HID WRITE: >>>"
		str += " ".join( [ "%02X " % c for c in packet ] ).strip()
		self._logger.debug(str)

		return True

	def _read(self, timeout):
		""" Read data from this device while blocking for up to timeout ms
		Args:
			timeout: ms to wait for data before failing the read
		Returns:
			bytearray: data received from device
		"""
		# hidapi requires 64 byte packets (+ the Report ID leading byte)
		buff = self._device.read(65, timeout)

		if len(buff) <= 1:
			print("ERROR: HID read timeout!")
			return bytearray()

		buff = buff[1:] # Remove the Report ID
		packet_len = buff[1]

		# We don't have a full packet yet, fetch more data
		while len(buff) < packet_len:
			buff += self._device.read(65, timeout)[1:buff[0]]
			if len(buff) >= 1 and len(buff) >= packet_len:
				break

		if len(buff) > packet_len:
			buff = buff[:packet_len]

		str = "HID READ: <<<"
		str += " ".join( [ "%02X " % c for c in buff ] ).strip()
		self._logger.debug(str)

		return bytearray(buff)
