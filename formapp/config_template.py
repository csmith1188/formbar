#Set to True for RPi, False for PC
ONRPi = False
#Enable/Disable dbug() blurbs
DEBUG = True
#Set the maximum number of pixels on the bar
BARPIX = 300
#Set the maximum number of pixels, including pixelpanels
MAXPIX = 812

#import netifaces as ni
#Get internal IP address
#for wireless connections:
#ip = ni.ifaddresses('wlan0')[ni.AF_INET][0]['addr']
#for wired connections
#ip = ni.ifaddresses('eth0')[ni.AF_INET][0]['addr']
#for manual addresses
ip = "127.0.0.1"
