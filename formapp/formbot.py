import requests
import time
import socket
import sys

from modules import bgm
from modules import sfx


    #change "userType": "login", to "usertype": "new" on first time use
    def login(self):
        loginAttempt = requests.post(url="http://"+self.host+":"+str(self.port)+"/login", data={"username": self.username, "password": self.password, "userType": "login", "bot": "True", "forward":"/"})



#forbius login

Forbius = FormBot('Forbius', 'Password#1')
