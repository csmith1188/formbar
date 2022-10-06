#!/bin/bash

#install packages
sudo apt update
sudo apt upgrade -y
sudo apt-get -y install python3-pip
sudo apt-get -y install libatlas-base-dev
sudo apt-get -y install libsdl-ttf2.0-0
sudo apt-get -y install python3-sdl2
sudo apt-get -y install screen
#install modules

sudo pip3 install flask
sudo pip3 install flask_socketio
sudo pip3 install websocket_server
sudo pip3 install pygame
sudo pip3 install openpyxl
sudo pip3 install netifaces
sudo pip3 install cryptography
sudo pip3 --default-timeout=1000 install pandas
cp formapp/data/database_template.db formapp/data/database.db
cp formapp/key_template.py formapp/key.py
cp formapp/config_template.py formapp/config.py
sudo pip3 install rpi_ws281x adafruit-circuitpython-neopixel
sudo python3 -m pip install --force-reinstall adafruit-blinka
