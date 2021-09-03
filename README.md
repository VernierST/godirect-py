# godirect

A Python module for reading from [Vernier Go Direct® Sensors](https://www.vernier.com/products/sensors/go-direct-sensors/)<sup>1</sup> connected to USB or your system's on-board bluetooth radio. The module has been tested on Windows 10, macOS, and various Linux distros.

Take a look at the [godirect-examples repository](https://github.com/VernierST/godirect-examples/tree/main/python) for ideas and a number of helpful examples.

## Requirements

The following Python modules are required for `godirect`. They will be installed automatically as dependencies when installing `godirect` via pip.

* bleak (native Bluetooth Low Energy stack for Mac, Windows and Linux)
* hidapi (USB HID device support)

## Installation

Automatically install all the dependencies for both USB and native BLE.
```bash
pip install godirect
```

## Installation and Usage

Go to our [Getting Started with Vernier Go Direct Sensors and Python document](https://github.com/VernierST/godirect-examples/blob/main/python/readme.md) for detailed information regarding installation and usage of the godirect module.

## Legacy Support for Bluegiga Dongle

Prior to version 1.1.0, some platforms required a Bluegiga BLE dongle to connect over BLE. While we recommend using the native BLE radio (through bleak), the old functionality has been left in the library. In order to use the Bluegiga BLE dongle, vernierpygatt must be installed. This is a fork of the pygatt project with a fix for the BGAPI on Windows. See [the vernierpygatt PyPi page](https://pypi.org/project/vernierpygatt/) for details.

## License

GNU General Public License v3 (GPLv3)

Vernier products are designed for educational use. Our products are not designed nor are they recommended for any industrial, medical, or commercial process such as life support, patient diagnosis, control of a manufacturing process, or industrial testing of any kind.

<sup>1</sup> Go Direct spectrometers are not supported.