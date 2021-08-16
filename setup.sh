#!/bin/bash

sudo apt install python3-pip
sudo pip3 install rpi_ws281x adafruit-circuitpython-neopixel
sudo python3 -m pip install --force-reinstall adafruit-blinka
#install modules
sudo pip3 install flask
sudo pip3 install websocket_server
sudo pip3 --default-timeout=1000 install pandas
sudo apt-get install libatlas-base-dev
sudo pip3 openpyxl