import requests
import time

#Importing external modules
from flask import Flask, redirect, url_for, request, render_template, session, copy_current_request_context
from flask_socketio import SocketIO, emit, disconnect
from threading import Lock
from werkzeug.utils import secure_filename
from websocket_server import WebsocketServer
from cryptography.fernet import Fernet
import pandas, json, csv
import random, sys, os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
import time, math
import threading
import logging
import traceback
import sqlite3
import board, neopixel

# Change the built-in logging for flask
flasklog = logging.getLogger('werkzeug')
flasklog.setLevel(logging.ERROR)

#Start up pygame for sfx and bgm
pygame.init()

#Start the neopixel tracker

#Create a list of neopixels if we are on an RPi
pixels = neopixel.NeoPixel(board.D21, MAXPIX, brightness=1.0, auto_write=False)

class FormBot():
    def __init__(self, username, password, timeout=0, host='127.0.0.1', port=420)       :
        self.host = '192.168.10.69'
        self.port = 420
        self.username = username
        self.password = password
        self.loggedin = False
        time.sleep(timeout)
        self.login()
        print('logged in as', username)


    #change "userType": "login", to "usertype": "new" on first time use
    def login(self):
        loginAttempt = requests.post(url="http://"+self.host+":"+str(self.port)+"/login", data={"username": self.username, "password": self.password, "userType": "new", "bot": "True", "forward":"/"})



#forbius login

Forbius = FormBot('Forbius', 'Password#1')
