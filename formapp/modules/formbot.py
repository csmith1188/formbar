import requests
import time

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
