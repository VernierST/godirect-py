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

## Installation and Usage

Go to our [Getting Started with Vernier Go Direct Sensors and Python document](https://github.com/VernierST/godirect-examples/blob/master/python/readme.md) for detailed information regarding installation and usage of the godirect module.

## License

GNU General Public License v3 (GPLv3)

Vernier products are designed for educational use. Our products are not designed nor are they recommended for any industrial, medical, or commercial process such as life support, patient diagnosis, control of a manufacturing process, or industrial testing of any kind.
