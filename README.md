# godirect

A Python module for reading from [Vernier Go Direct® Sensors](https://www.vernier.com/products/sensors/go-direct-sensors/) using USB or BLE.

Take a look at the [godirect-examples repository](https://github.com/VernierST/godirect-examples) for ideas and a number of helpful examples.

## Requirements

The following Python modules are required for `godirect`. They will be installed
automatically as dependencies when installing `godirect` via pip.

* pexpect

The following Python modules are recommended for `godirect`. They will only be installed if they are specified as `extras` when installing `godirect` via pip. See below.

* vernierpygatt (fork of the pygatt project with a fix for the BGAPI on Windows)
* hidapi (USB HID device support)

## Installation

Automatically install the `extras` support dependencies for both USB and BLE.
```bash
pip install godirect[usb,ble]
```

In order to use the native Windows 10 or Linux BLE stack, Bleak must be installed.  To install:
```bash
pip install bleak
```

## Example Use

Connect to the first available USB device or closest BLE device within the default threshold and collect 10 samples from the default sensor.
```python
from godirect import GoDirect
godirect = GoDirect()
device = godirect.get_device()
if device != None and device.open(auto_start=True):
	sensors = device.get_enabled_sensors()
	print("Connected to "+device.name)
	print("Reading 10 measurements")
	for i in range(0,10):
		if device.read():
			for sensor in sensors:
				print(sensor.sensor_description+": "+str(sensor.value))
	device.stop()
	device.close()
godirect.quit()
```

Note that you can choose to enable USB, BLE, or both. By default both will be enabled.
```python
godirect = GoDirect(use_ble=True, use_usb=True)
```

Here is how to obtain a list of GoDirectDevice objects from the BLE and/or USB backends.
```python
# returns a list of GoDirectDevice objects
devices = godirect.list_devices()
```

Or you can let the library automatically find the nearest device for you.
```python
# returns a GoDirectDevice on success or None on failure
mydevice = godirect.get_device()

# to adjust the BLE threshold pass in a minimum dB value
mydevice = godirect.get_device(threshold=-200)
```

Once a device is found or selected it must be opened. By default only information will be 
gathered on Open. To automatically enable the default sensors and start measurements send 
auto_start=True and skip to getting a list of enabled sensors. 
```python
# returns True on success or False on failure
mydevice.open()
```

Once a device is opened you can obtain a list of sensor objects available on
the device.
```python
# returns a list of Sensor objects
sensors = mydevice.list_sensors()
```

Optionally you can select the sensors you want to collect from, otherwise the
default sensor(s) will be used.
```python
# pass a list of sensor numbers to enable
mydevice.enable_sensors([2,3,4])
```

```python
# start measurements at the typical rate for the enabled sensors
mydevice.start() # returns True on success

# start measurements at 1000ms per sample
mydevice.start(period=1000)

# get a list of the GoDirectSensor objects that are enabled
mysensors = mydevice.get_enabled_sensors()
```

The `read()` method will block until data is returned so it is acceptable to read
in a tight loop.

```python
for i in range(0,10):
  # read() will append the measurement received to the values list in the Sensor object
  if mydevice.read():
    for sensor in mysensors:
			print(sensor.value)
```

The `stop()` method will stop data collection on the device. The `close()` method
will disconnect the USB or BLE device. The `quit()` method will stop the USB or BLE backends gracefully.

## Debugging

godirect uses the standard python logging module. You can set the logging verbosity
to INFO or DEBUG to see more communication detail.

```python
import logging
logging.basicConfig()
logging.getLogger('godirect').setLevel(logging.DEBUG)
logging.getLogger('pygatt').setLevel(logging.DEBUG)
```

## Windows

The pygatt module uses the BGAPI backend to communicate with the BLE dongle.
You might have to specify the COM port assigned to the BLE dongle if the auto-detection fails.

```
python
godirect = GoDirect(ble_com_port='COM9')
```

## Linux

In order to communicate with Go Direct devices over USB on Linux systems, you will need to provide a udev rule to grant the proper permissions for the device. You can create such a rule in the proper directory with this command:

```
sudo su -c 'cat <<EOT >/etc/udev/rules.d/vstlibusb.rules
SUBSYSTEM=="usb", ATTRS{idVendor}=="08f7", MODE="0666"
SUBSYSTEM=="usb_device", ATTRS{idVendor}=="08f7", MODE="0666"
EOT'
```

## License

GNU General Public License v3 (GPLv3)

Vernier products are designed for educational use. Our products are not designed nor are they recommended for any industrial, medical, or commercial process such as life support, patient diagnosis, control of a manufacturing process, or industrial testing of any kind.
