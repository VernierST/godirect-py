from abc import ABC, abstractmethod

class GoDirectBackend(ABC):
	def __init__(self):
		super().__init__()

	@abstractmethod
	def scan(self):
		pass

	@abstractmethod
	def scan_auto(self):
		pass

	@abstractmethod
	def connect(self, device):
		pass

	@abstractmethod
	def stop(self):
		pass
