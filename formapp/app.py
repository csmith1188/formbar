# ███████  ██████  ██████  ███    ███ ██████   █████  ██████
# ██      ██    ██ ██   ██ ████  ████ ██   ██ ██   ██ ██   ██
# █████   ██    ██ ██████  ██ ████ ██ ██████  ███████ ██████
# ██      ██    ██ ██   ██ ██  ██  ██ ██   ██ ██   ██ ██   ██
# ██       ██████  ██   ██ ██      ██ ██████  ██   ██ ██   ██


'''
    Formbar: An interactive classroom management tool focused on lesson pacing
        and formative assessment. Formbar excels in a Computer Science class
        environment, but provides tools to any class with web-enabled devices
        with a network connection to the Formbar host for each student.

        Formbar was designed for Raspberry Pi 4, but can run without physical
        add-ons on a Windows PC.
'''


#  ██████  ██████  ███    ██ ███████ ██  ██████  ██    ██ ██████   █████  ████████ ██  ██████  ███    ██
# ██      ██    ██ ████   ██ ██      ██ ██       ██    ██ ██   ██ ██   ██    ██    ██ ██    ██ ████   ██
# ██      ██    ██ ██ ██  ██ █████   ██ ██   ███ ██    ██ ██████  ███████    ██    ██ ██    ██ ██ ██  ██
# ██      ██    ██ ██  ██ ██ ██      ██ ██    ██ ██    ██ ██   ██ ██   ██    ██    ██ ██    ██ ██  ██ ██
#  ██████  ██████  ██   ████ ██      ██  ██████   ██████  ██   ██ ██   ██    ██    ██  ██████  ██   ████


from config import *

#Permission levels are as follows:
# 0 - teacher
# 1 - mod
# 2 - student
# 3 - anyone
# 4 - banned

NEWACCOUNTPERMISSIONS = 3

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
import datetime
import traceback
import sqlite3
if ONRPi:
    import board, neopixel

#Importing customs modules
from modules import letters
from modules import sfx
from modules import bgm
from modules.colors import colors, hex2dec
from modules import lessons
from modules import sessions
from key import key
if ONRPi:
    from modules import ir

# Change the built-in logging for flask
flasklog = logging.getLogger('werkzeug')
flasklog.setLevel(logging.ERROR)

#Display IP address to console for user connection. Updates the Time as well
def logFile(type, message):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    f = open('log.txt', 'a')
    f.write("[" + str(now) + "]" + " [" + type + "] " + message + "\n")
    f.close()
    print("[" + str(now) + "]" + " [" + type + "] " + message)
#This import allows for the time to be printed to console. If you need to add a new print line the 2nd line is an example of how to use the logFile() function to make it print to console and to the log file
#logFile("Info", "Bot successful login. Made them a guest: " + username)

logFile('Info', "Running formbar on ip: " + ip)


# ██       ██████   █████  ██████  ██ ███    ██  ██████
# ██      ██    ██ ██   ██ ██   ██ ██ ████   ██ ██
# ██      ██    ██ ███████ ██   ██ ██ ██ ██  ██ ██   ███
# ██      ██    ██ ██   ██ ██   ██ ██ ██  ██ ██ ██    ██
# ███████  ██████  ██   ██ ██████  ██ ██   ████  ██████


#Scan the sfx and bgm folders
sfx.updateFiles()
bgm.updateFiles()
#Start up pygame for sfx and bgm
pygame.init()

#Start the neopixel tracker
if ONRPi:
    #Create a list of neopixels if we are on an RPi
    pixels = neopixel.NeoPixel(board.D21, MAXPIX, brightness=1.0, auto_write=False)
else:
    #Create an empty list as long as our MAXPIX if not on RPi
    pixels = [(0,0,0)]*MAXPIX

async_mode = None
#Start a new flask server for http service
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socket_ = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock()

apinamespace = '/apisocket'
chatnamespace = '/chat'

sD = sessions.Session(ip)

#Start encryption tools
cipher = Fernet(key)

# Dictionary words for hangman game
words = json.loads(open(os.path.dirname(os.path.abspath(__file__)) + "/data/words.json").read())

banList = []
newPasswords = {}
blockList = []
colorDict = {
        '14': (255, 255, 0),
        '15': (196, 150, 128),
        '16': (255, 96, 0),
        '56': (0, 192, 192),
        }

#Set pollID based on the number of polls in the database
db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
dbcmd = db.cursor()
pollCount = dbcmd.execute("SELECT COUNT(*) FROM polls").fetchone()
if pollCount:
    sD.pollID = pollCount[0] + 1
db.close()

#Get settings from database
db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
dbcmd = db.cursor()
data = dbcmd.execute("SELECT * FROM settings").fetchone()
db.close()
sD.settings['perms']['say'] = data[0]
sD.settings['perms']['games'] = data[1]
sD.settings['perms']['bar'] = data[2]
sD.settings['perms']['sfx'] = data[3]
sD.settings['perms']['bgm'] = data[4]
sD.settings['perms']['api'] = data[5]
sD.settings['locked'] = data[6]
sD.settings['blind'] = data[7]
sD.settings['showinc'] = data[8]


# ███████ ██    ██ ███    ██  ██████ ████████ ██  ██████  ███    ██ ███████
# ██      ██    ██ ████   ██ ██         ██    ██ ██    ██ ████   ██ ██
# █████   ██    ██ ██ ██  ██ ██         ██    ██ ██    ██ ██ ██  ██ ███████
# ██      ██    ██ ██  ██ ██ ██         ██    ██ ██    ██ ██  ██ ██      ██
# ██       ██████  ██   ████  ██████    ██    ██  ██████  ██   ████ ███████


'''
#For testing potential animation features
def aniTest():
    if not ONRPi:
        global pixels
    fillBar((0,0,0))
    for i in range(0, BARPIX - 40):
        pixRange = range(i+20, i + 40)
        pixRange2 = range(i, i + 20)
        for j, pix in enumerate(pixRange):
            pixels[pix] = blend(pixRange, j, colors['blue'], colors['red'])
        for j, pix in enumerate(pixRange2):
            pixels[pix] = blend(pixRange2, j, colors['green'], colors['blue'])
        if ONRPi:
            pixels.show()

@app.route('/anitest')
def endpoint_anitest():
    if len(threading.enumerate()) < 5:
        threading.Thread(target=aniTest, daemon=True).start()
        return render_template("message.html", message = 'testing...')
    else:
        return render_template("message.html", message = 'Too many threads')
'''

def dbug(message='Checkpoint Reached'):
    global DEBUG
    if DEBUG:
        logFile(" [DEBUG] " + str(message))

def newStudent(remote, username, bot=False):
    global NEWACCOUNTPERMISSIONS
    if not remote in sD.studentDict:
        sD.studentDict[remote] = {
            'name': username,
            'thumb': '',
            'letter': '',
            'essay': '',
            'perms': 3,
            'oldPerms': 3,
            'progress': [],
            'complete': False,
            'tttGames': [],
            'quizRes': [],
            'essayRes': '',
            'bot': bot,
            'help': {
                'type': '',
                'time': None,
                'message': ''
            },
            'excluded': False,
            'preferredHomepage': None,
            'sid': ''
        }
        #Track if the teacher is logged in
        teacher = False

        #Check each student so far to make sure that none of them have teacher perms
        for user in sD.studentDict:
            if sD.studentDict[user]['perms'] == 0:
                teacher = True

        #Login bots as guest
        if bot:
            logFile("Info", "Bot successful login. Made them a guest: " + username)
            sD.studentDict[remote]['perms'] = sD.settings['perms']['anyone']

        #Login as teacher if there is no teacher yet
        elif not teacher:
            logFile("Info", username + " logged in. Made them the teacher...")
            sD.studentDict[remote]['perms'] = sD.settings['perms']['admin']

        #Login other users as guests (students until database is installed)
        else:
            logFile("Info", username + " logged in.")
            sD.studentDict[remote]['perms'] = NEWACCOUNTPERMISSIONS

        #Overwrite permissions with those retrieved from database here
        #Open and connect to database
        db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
        dbcmd = db.cursor()
        userFound = dbcmd.execute("SELECT * FROM users WHERE username=:uname", {"uname": username}).fetchall()
        db.close()
        for user in userFound:
            if username in user:
                if not teacher:
                    sD.studentDict[remote]['perms'] = sD.settings['perms']['admin']
                else:
                    sD.studentDict[remote]['perms'] = int(user[3])

        socket_.emit('alert', json.dumps(packMSG('all', 'server', sD.studentDict[request.remote_addr]['name'] + " logged in...")), namespace=chatnamespace)
        playSFX("sfx_up02")

def flushUsers():
    for user in list(sD.studentDict):
        if not sD.studentDict[user]['perms'] == sD.settings['perms']['admin']:
            del sD.studentDict[user]
    playSFX("sfx_splash01")

#Erases student(s) answer(s) by name and category
#Returns True if successful, and False if it failed
def refreshUsers(selectedStudent='', category=''):
    for student in sD.studentDict:
        if selectedStudent:
            student = selectedStudent
        if category:
            try:
                sD.studentDict[student][category] = ''
                return True
            except Exception as e:
                logFile("Error", + e)
                return False
        else:
            sD.studentDict[student]['thumb'] = '',
            sD.studentDict[student]['letter'] = '',
            sD.studentDict[student]['progress'] = [],
            sD.studentDict[student]['complete'] = False,
            sD.studentDict[student]['quizRes'] = [],
            sD.studentDict[student]['essayRes'] = ''
            return True

def changeMode(newMode='', direction='next'):
    clearString()
    sD.pollType = None
    # Clear answers
    for student in sD.studentDict:
        sD.studentDict[student]['thumb'] = ''
        sD.studentDict[student]['letter'] = ''
        sD.studentDict[student]['essay'] = ''
    index = sD.settings['modes'].index(sD.settings['barmode'])
    if newMode in sD.settings['modes']:
        sD.settings['barmode'] = newMode
    elif newMode:
        return render_template("message.html", message = "[warning] " + 'Invalid mode.')
    else:
        if direction == 'next':
            index += 1
        elif direction == 'prev':
            index -= 1
        else:
            return render_template("message.html", message = "[warning] " + 'Invalid direction. Needs next or prev.')
        if index >= len(sD.settings['modes']):
            index = 0
        elif index < 0:
            index =len(sD.settings['modes']) - 1
        sD.settings['barmode'] = sD.settings['modes'][index]
    if sD.settings['barmode'] == 'tutd':
        tutdBar()
    elif sD.settings['barmode'] == 'abcd':
        abcdBar()
    elif sD.settings['barmode'] == 'text':
        textBar()
    elif sD.settings['barmode'] == 'essay' or sD.settings['barmode'] == 'quiz':
        completeBar()
    elif sD.settings['barmode'] == 'progress':
        if sD.lesson:
            percFill(sD.lesson.checkProg(stripUser('admin')))
    elif sD.settings['barmode'] == 'playtime':
        clearString()
        showString(sD.activePhrase)
    socket_.emit('modeChanged', {'mode': sD.settings['barmode']}, namespace=apinamespace)
    return render_template("message.html", message = 'Changed mode to ' + (newMode or direction) + '.')

#This function Allows you to choose and play whatever sound effect you want
def playSFX(sound):
    try:
        pygame.mixer.Sound(sfx.sound[sound]).play()
        return "Successfully played: "
    except Exception as e:
        logFile("Error", + e)
        return "Invalid format: "

def stopSFX():
    pygame.mixer.Sound.stop()

# This function allows you to choose wich background music you want
def startBGM(bgm_filename, volume=sD.bgm['volume']):
    sD.bgm['paused'] = True
    pygame.mixer.music.load(bgm.bgm[bgm_filename])
    pygame.mixer.music.set_volume(volume)
    pygame.mixer.music.play(loops=-1)
    playSFX("sfx_pickup01")

#This function stops BGM
def stopBGM():
    sD.bgm['paused'] = False
    pygame.mixer.music.stop()
    sD.bgm['nowplaying'] = ''
    playSFX("sfx_pickup01")

#This function stops BGM
def rewindBGM():
    pygame.mixer.music.rewind()
    playSFX("sfx_pickup01")

def playpauseBGM(state='none'):
    if pygame.mixer.music.get_busy():
        if type(state) is bool:
            sD.bgm['paused'] = state
        sD.bgm['paused'] = not sD.bgm['paused']
        if sD.bgm['paused']:
            pygame.mixer.music.pause()
        else:
            pygame.mixer.music.unpause()
    playSFX("sfx_pickup01")

def volBGM(value):
    sD.bgm['volume'] = pygame.mixer.music.get_volume()
    if value == 'up':
        sD.bgm['volume'] += 0.1
    elif value == 'down':
        sD.bgm['volume'] -= 0.1
    else:
        sD.bgm['volume'] = value
    if sD.bgm['volume'] > 1.0:
        sD.bgm['volume'] = 1.0
    if sD.bgm['volume'] < 0:
        sD.bgm['volume'] = 0.0
    pygame.mixer.music.set_volume(sD.bgm['volume'])
    playSFX("sfx_pickup01")

def str2bool(strng):
    strng.lower()
    if strng == 'true':
        return True
    elif strng == 'false':
        return False
    else:
        return strng

def fadein(irange, current, color):
    return [int(x * (current / len(irange))) for x in color]

def fadeout(irange, current, color):
    return [int(x * ((len(irange) - current) / len(irange))) for x in color]

def blend(irange, current, color1, color2):
    blendColor = fadein(irange, current, color2)
    for i, rgb in enumerate(blendColor):
        blendColor[i] += fadeout(irange, current, color1)[i]
    return blendColor

def addBlock():
    if not ONRPi:
        global pixels
    if blockList[-1][0] in colorDict:
        pixels[len(blockList)-1] = colorDict[blockList[-1][0]]
    else:
        pixels[len(blockList)-1] = colors['default']
    if ONRPi:
        pixels.show()

def fillBlocks():
    if not ONRPi:
        global pixels
    for i, block in enumerate(blockList):
        if block[0] in colorDict:
            pixels[i] = colorDict[block[0]]
        else:
            pixels[i] = colors['default']
    if ONRPi:
        pixels.show()

def percFill(amount, fillColor=colors['green'], emptyColor=colors['red']):
    if not ONRPi:
        global pixels
    if amount > 100 and amount < 0 and type(amount) is not int:
        raise TypeError("Out of range. Must be between 0 - 1 or 0 - 100.")
    else:
        pixRange = math.ceil(BARPIX * (amount * 0.01))
        for pix in range(0, BARPIX):
            if pix <= pixRange:
                pixels[pix] = fillColor
            else:
                pixels[pix] = emptyColor
        if ONRPi:
            pixels.show()
    if sD.settings['captions']:
        clearString()
        showString("PROG " + str(sD.lesson.checkProg(stripUser('admin'))))
    if ONRPi:
        pixels.show()

def fillBar(color=colors['default'], stop=BARPIX, start=0):
    if not ONRPi:
        global pixels
    #If you provide no args, the whole bar is made the default color
    #If you provide one arg, the whole bar will be that color
    #If you provide two args, the bar will be that color until the stop point
    #If you provide three args, pixels between the stop and start points will be that color
    for pix in range(start, stop):
        pixels[pix] = color

def repeatMode():
    # Clear answers
    for student in sD.studentDict:
        sD.studentDict[student]['thumb'] = ''
        sD.studentDict[student]['letter'] = ''
        sD.studentDict[student]['essay'] = ''
    if sD.settings['barmode'] == 'tutd':
        tutdBar()
    elif sD.settings['barmode'] == 'abcd':
        abcdBar()
    elif sD.settings['barmode'] == 'text':
        textBar()
    elif sD.settings['barmode'] == 'essay' or sD.settings['barmode'] == 'quiz' :
        # Clear thumbs
        for student in sD.studentDict:
            sD.studentDict[student]['complete'] = ''
        completeBar()
    elif sD.settings['barmode'] == 'progress':
        for student in sD.studentDict:
            for task in sD.lesson.progList[step['Prompt']]['task']:
                sD.studentDict[student]['progress'].append(False)
        percFill(sD.lesson.checkProg(stripUser('admin')))
    elif sD.settings['barmode'] == 'playtime':
        sD.activePhrase = ''
        clearString()
        showString(sD.activePhrase)
    playSFX("sfx_success01")
    
def endMode():
    clearBar()
    showString(ip + "  Idle")

#This function clears(default) the color from the formbar
def clearBar():
    if not ONRPi:
        global pixels
    #fill with default color to clear bar
    for pix in range(0, BARPIX):
        pixels[pix] = colors['default']

def clearString():
    if not ONRPi:
        global pixels
    for i in range(BARPIX, MAXPIX):
        pixels[i] = colors['bg']

def showString(toShow, startLocation=0, fg=colors['fg'], bg=colors['bg']):
    for i, letter in enumerate(toShow.lower()):
        printLetter(letter, (i * (8 * 6)) + ((startLocation * 48) + BARPIX), fg, bg)
    if ONRPi:
        pixels.show()

def printLetter(letter, startLocation, fg=colors['fg'], bg=colors['bg']):
    if not ONRPi:
        global pixels
    if (MAXPIX - startLocation) >= 48:
        if letter in letters.ASCIIdict:
            for i, pull_row in enumerate(letters.ASCIIdict[letter]):
                #temporary variable (keeps it from permanently flipping letter pixels)
                row = []
                for pix in pull_row:
                    row.append(pix)
                # If this is an even row, reverse direction
                if not i%2:
                    row.reverse()
                for j, pixel in enumerate(row):
                    pixPoint = startLocation + (i*8)
                    if pixel:
                        pixels[pixPoint + j] = fg
                    else:
                        pixels[pixPoint + j] = bg
                pixPoint = startLocation + (i + (8*5))
                for j in range(pixPoint, pixPoint + 4):
                    pixels[j] = bg

        else:
            logFile(" [warning] ", "Warning! Letter " + letter + " not found.")
    else:
        logFile(" [warning] ", "Warning! Not enough space for this letter!")

#Shows results of test when done with abcdBar
def abcdBar():
    if not ONRPi:
        global pixels
    results = [] # Create empty results list
    clearBar()
    #Go through IP list and see what each IP sent as a response
    for student in sD.studentDict:
        #if the poll answer is a valid a, b, c, or d:
        if sD.studentDict[student]['letter'] in ['a', 'b', 'c', 'd']:
            #add this result to the results list
            results.append(sD.studentDict[student]['letter'])
    #The number of results is how many have complete the poll
    complete = len(results)
    #calculate the chunk length for each student
    chunkLength = math.floor(BARPIX / sD.settings['numStudents'])
    #Sort the results by "alphabetical order"
    results.sort()
    #Loop through each result, and show the correct color
    for index, result in enumerate(results):
        #Calculate how long this chunk will be and where it starts
        pixRange = range((chunkLength * index), (chunkLength * index) + chunkLength)
        #Fill in that chunk with the correct color
        if result == 'a':
            answerColor = colors['red']
        elif result == 'b':
            answerColor = colors['blue']
        elif result == 'c':
            answerColor = colors['yellow']
        elif result == 'd':
            answerColor = colors['green']
        else:
            answerColor = colors['default']
        for i, pix in enumerate(pixRange):
            #If it's the first pixel of the chunk, make it a special color
            if i == 0:
                pixels[pix] = colors['student']
            else:
                if sD.settings['blind'] and complete != sD.settings['numStudents']:
                    pixels[pix] = fadein(pixRange, i, colors['blind'])
                else:
                    pixels[pix] = fadein(pixRange, i, answerColor)

    if sD.settings['captions']:
        clearString()
        showString("ABCD " + str(complete) + "/" + str(sD.settings['numStudents']))
    if ONRPi:
        pixels.show()

#it takes the students picked answer and puts the required color for that specific choice
def tutdBar():
    if not ONRPi:
        global pixels
    if sD.settings['autocount']:
        autoStudentCount()
    upFill = upCount = downFill = downCount = wiggleFill = wiggleCount = 0
    complete = 0
    for x in sD.studentDict:
        if sD.studentDict[x]['perms'] == sD.settings['perms']['student'] and sD.studentDict[x]['thumb']:
            if sD.studentDict[x]['thumb'] == 'up':
                upFill += 1
                upCount += 1
            elif sD.studentDict[x]['thumb'] == 'down':
                downFill += 1
                downCount += 1
            elif sD.studentDict[x]['thumb'] == 'wiggle':
                wiggleFill += 1
                wiggleCount += 1
            complete += 1
    for pix in range(0, BARPIX):
        pixels[pix] = colors['default']
    if sD.settings['showinc']:
        chunkLength = math.floor(BARPIX / sD.settings['numStudents'])
    else:
        chunkLength = math.floor(BARPIX / complete)
    for index, ip in enumerate(sD.studentDict):
        pixRange = range((chunkLength * index), (chunkLength * index) + chunkLength)
        if upFill > 0:
            for i, pix in enumerate(pixRange):
                if i == 0:
                    pixels[pix] = colors['student']
                else:
                    if sD.settings['blind'] and complete != sD.settings['numStudents']:
                        pixels[pix] = fadein(pixRange, i, colors['blind'])
                    else:
                        pixels[pix] = fadein(pixRange, i, colors['green'])
            upFill -= 1
        elif wiggleFill > 0:
            for i, pix in enumerate(pixRange):
                if i == 0:
                    pixels[pix] = colors['student']
                else:
                    if sD.settings['blind'] and complete != sD.settings['numStudents']:
                        pixels[pix] = fadein(pixRange, i, colors['blind'])
                    else:
                        pixels[pix] = fadein(pixRange, i, colors['cyan'])
            wiggleFill -= 1
        elif downFill > 0:
            for i, pix in enumerate(pixRange):
                if i == 0:
                    pixels[pix] = colors['student']
                else:
                    if sD.settings['blind'] and complete != sD.settings['numStudents']:
                        pixels[pix] = fadein(pixRange, i, colors['blind'])
                    else:
                        pixels[pix] = fadein(pixRange, i, colors['red'])
            downFill -= 1
    if sD.settings['captions']:
        clearString()
        showString("TUTD " + str(complete) + "/" + str(sD.settings['numStudents']))
        if ONRPi:
            pixels.show()
    if upCount >= sD.settings['numStudents']:
        if ONRPi:
            pixels.fill((0,0,0))
        else:
            pixels = [(0,0,0)] * MAXPIX
        playSFX("sfx_success01")
        for i, pix in enumerate(range(0, BARPIX)):
                pixels[pix] = blend(range(0, BARPIX), i, colors['blue'], colors['red'])
        if sD.settings['captions']:
            clearString()
            showString("MAX GAMER!", 0, colors['purple'])
    elif downCount >= sD.settings['numStudents']:
        playSFX("wompwomp")
    elif wiggleCount >= sD.settings['numStudents']:
        playSFX("bruh")
    #The Funny Number
    elif sD.settings['numStudents'] == 9 and complete == 6:
        playSFX("clicknice")
    elif complete:
        playSFX("sfx_blip01")
    if ONRPi:
        pixels.show()

#Show how many students have submitted Essays
def textBar():
    if not ONRPi:
        global pixels
    if sD.settings['autocount']:
        autoStudentCount()
    complete = fill = 0
    for x in sD.studentDict:
        if sD.studentDict[x]['perms'] == sD.settings['perms']['student'] and sD.studentDict[x]['essay']:
            complete += 1
            fill += 1
    for pix in range(0, BARPIX):
        pixels[pix] = colors['default']
    if sD.settings['showinc']:
        chunkLength = math.floor(BARPIX / sD.settings['numStudents'])
    else:
        chunkLength = math.floor(BARPIX / complete)
    for index, ip in enumerate(sD.studentDict):
        pixRange = range((chunkLength * index), (chunkLength * index) + chunkLength)
        if fill > 0:
            for i, pix in enumerate(pixRange):
                if i == 0:
                    pixels[pix] = colors['student']
                else:
                    pixels[pix] = fadein(pixRange, i, colors['blind'])
            fill -= 1
    if sD.settings['captions']:
        clearString()
        showString("TEXT " + str(complete) + "/" + str(sD.settings['numStudents']))
        if ONRPi:
            pixels.show()
    if complete >= sD.settings['numStudents']:
        if ONRPi:
            pixels.fill((0,0,0))
        else:
            pixels = [(0,0,0)] * MAXPIX
        playSFX("sfx_success01")
        for i, pix in enumerate(range(0, BARPIX)):
                pixels[pix] = blend(range(0, BARPIX), i, colors['blue'], colors['red'])
        if sD.settings['captions']:
            clearString()
            showString("MAX GAMER!", 0, colors['purple'])
    #The Funny Number
    elif sD.settings['numStudents'] == 9 and complete == 6:
        playSFX("clicknice")
    elif complete:
        playSFX("sfx_blip01")
    if ONRPi:
        pixels.show()

def countComplete():
    complete = 0
    for student in sD.studentDict:
        if sD.studentDict[student]['complete']:
            complete += 1
    return complete

def completeBar():
    complete = countComplete()
    if sD.settings['captions']:
        clearString()
        showString("DONE " + str(complete) + "/" + str(sD.settings['numStudents']))
    if ONRPi:
        pixels.show()

def autoStudentCount():
    sD.settings['numStudents'] = 0
    for user in sD.studentDict:
        if sD.studentDict[user]['perms'] == 2:
            sD.settings['numStudents'] += 1
    if sD.settings['numStudents'] == 0:
        sD.settings['numStudents'] = 1

def stripUser(perm, exclude=True):
    newList = {}
    for student in sD.studentDict:
        if sD.studentDict[student]['perms'] > sD.settings['perms'][perm]:
            if exclude and sD.studentDict[student]['perms'] < 4:
                newList[student] = sD.studentDict[student]
    return newList

def stripUserData(perm='', sList={}):
    newList = sList
    for student in sD.studentDict:
        newList[student] = {}
        newList[student]['name'] = sD.studentDict[student]['name']
        newList[student]['perms'] = sD.studentDict[student]['perms']
        newList[student]['complete'] = sD.studentDict[student]['complete']
    return newList

def chatUsers():
    newList = {}
    for student in sD.studentDict:
        if 'sid' in sD.studentDict[student].keys():
            newList[student] = {}
            newList[student]['name'] = sD.studentDict[student]['name']
            newList[student]['perms'] = sD.studentDict[student]['perms']
            newList[student]['sid'] = sD.studentDict[student]['sid']
    return newList

def updateStep():
    step = sD.lesson.steps[sD.currentStep]
    if step['Type'] == 'Resource':
        sD.wawdLink = sD.lesson.links[int(step['Prompt'])]['URL']
    elif step['Type'] == 'TUTD':
        sD.settings['barmode'] = 'tutd'
        sD.activePrompt = step['Prompt']
    elif step['Type'] == 'Essay': ##
        sD.settings['barmode'] = 'essay'
        sD.activePrompt = step['Prompt']
    elif step['Type'] == 'poll':
        sD.settings['barmode'] = 'poll'
        sD.activeQuiz = sD.lesson.quizList[step['Prompt']]
        pollIndex = int(sD.activeQuiz['name'].split(' ', 1))
        sD.activePrompt = sD.activeQuiz['questions'][pollIndex]
    elif step['Type'] == 'Quiz':
        sD.activeQuiz = sD.lesson.quizList[step['Prompt']]
        sD.settings['barmode'] = 'quiz'
        sD.wawdLink = '/quiz'
    elif step['Type'] == 'Progress':
        sD.settings['barmode'] = 'progress'
        sD.activeProgress = sD.lesson.progList[step['Prompt']]
        for student in sD.studentDict:
            sD.studentDict[student]['progress'] = []
            for task in sD.activeProgress['task']:
                sD.studentDict[student]['progress'].append(False)
        sD.wawdLink = '/progress'
    changeMode(sD.settings['barmode'])


def loginCheck(remAdd, perm=False): 
    if not remAdd in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    elif perm != False and sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms'][perm]:
        return render_template("message.html", message = "You do not have high enough permissions to do this right now.")
    else:
        return False

# ███████ ███    ██ ██████  ██████   ██████  ██ ███    ██ ████████ ███████
# ██      ████   ██ ██   ██ ██   ██ ██    ██ ██ ████   ██    ██    ██
# █████   ██ ██  ██ ██   ██ ██████  ██    ██ ██ ██ ██  ██    ██    ███████
# ██      ██  ██ ██ ██   ██ ██      ██    ██ ██ ██  ██ ██    ██         ██
# ███████ ██   ████ ██████  ██       ██████  ██ ██   ████    ██    ███████

@app.errorhandler(404)
def page_not_found(e):
    return render_template("message.html", message = e), 404

'''
    /
    Redirect to the user's preferred homepage
'''
@app.route('/')
def endpoint_root():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login')
    username = sD.studentDict[request.remote_addr]['name']
    #If no preferred homepage is set, check the database
    if not sD.studentDict[request.remote_addr]['preferredHomepage']:
        db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
        dbcmd = db.cursor()
        dbData = dbcmd.execute("SELECT * FROM users WHERE username=:uname", {"uname": username}).fetchall()
        db.close()
        if len(dbData):
            pm = dbData[0][6]
            sD.studentDict[request.remote_addr]['preferredHomepage'] = pm
    if sD.studentDict[request.remote_addr]['preferredHomepage'] == 'standard':
        return redirect('/home')
    if sD.studentDict[request.remote_addr]['preferredHomepage'] == 'advanced':
        return redirect('/advanced')
    if sD.studentDict[request.remote_addr]['preferredHomepage'] == 'quickpanel':
        return redirect('/quickpanel')
    return redirect('/setdefault')

@app.route('/2048')
def endpoint_2048():
    if request.args.get('advanced'):
        advanced = '?advanced=true'
    else:
        advanced = ''
    return redirect('/games/2048' + advanced)

#  █████
# ██   ██
# ███████
# ██   ██
# ██   ██


'''
/abcd
'''
@app.route('/abcd')
def endpoint_abcd():
    loginResult = loginCheck(request.remote_addr, request.path, 'student')
    if loginResult:
        return loginResult
    else:
        ip = request.remote_addr
        vote = request.args.get('vote')
        if vote:
            if sD.settings['barmode'] == 'abcd':
                if vote in ["a", "b", "c", "d"]:
                    if sD.studentDict[request.remote_addr]['letter'] != vote:
                        sD.studentDict[request.remote_addr]['letter'] = vote
                        playSFX("sfx_blip01")
                        abcdBar()
                        socket_.emit('letter', {'name': sD.studentDict[request.remote_addr]['name'], 'letter': vote}, namespace=apinamespace)
                        return render_template("message.html", message = "Thank you for your tasty bytes... (" + vote + ")")
                    else:
                        return render_template("message.html", message = "You've already submitted an answer... (" + sD.studentDict[request.remote_addr]['letter'] + ")")
                elif vote == 'oops':
                    if sD.studentDict[request.remote_addr]['letter']:
                        sD.studentDict[request.remote_addr]['letter'] = ''
                        playSFX("sfx_hit01")
                        abcdBar()
                        socket_.emit('letter', {'name': sD.studentDict[request.remote_addr]['name'], 'letter': ''}, namespace=apinamespace)
                        return render_template("message.html", message = "I won\'t mention it if you don\'t")
                    else:
                        return render_template("message.html", message = "You don't have an answer to erase.")
                else:
                    return render_template("message.html", message = "Bad arguments...")
            else:
                return render_template("message.html", message = "Not in ABCD mode.")
        else:
            return render_template("thumbsrental.html")

'''
    /addfighteropponent
'''
@app.route('/addfighteropponent', methods = ['POST'])
def endpoint_addfighteropponent():
    code = request.args.get('code')
    name = request.args.get('name')
    sD.fighter['match' + code]['opponent'] = name #Set "opponent" of object to arg "name"
    return render_template("message.html", message = "Opponent added.")


'''
/addfile
'''
@app.route('/addfile')
def endpoint_addfile():
    loginResult = loginCheck(request.remote_addr)
    if loginResult:
        return loginResult
    else:
        if request.method == 'POST':
            title = request.form['title']
            file = request.form['file']
            list = request.form['list']
            logFile(" Title: ", + title)
            logFile(" Filename: ", + file)
            logFile(" List: ", + list)
            return render_template("message.html", message = 'File submitted to teacher.')
        else:
            return render_template('addfile.html')

@app.route('/advanced')
def endpoint_advanced():
    loginResult = loginCheck(request.remote_addr)
    if loginResult:
        return loginResult
    else:
        page = request.args.get('page') or ''
        mainPage = sD.mainPage.lstrip("/")
        username = sD.studentDict[request.remote_addr]['name']
        sfx.updateFiles()
        sounds = []
        music = []
        for key, value in sfx.sound.items():
            sounds.append(key)
        for key, value in bgm.bgm.items():
            music.append(key)
        return render_template('advanced.html', page = page, mainPage = mainPage, username = username, sfx = sounds, bgm = music)

@app.route('/api')
def endpoint_api():
    loginResult = loginCheck(request.remote_addr)
    if loginResult:
        return loginResult
    else:
        if request.args.get('advanced'):
            advanced = '?advanced=true'
        else:
            advanced = ''
        return redirect('/debug' + advanced)

@app.route('/api/bgm')
def endpoint_api_bgm():
    loginResult = loginCheck(request.remote_addr, 'api')
    if loginResult:
        return loginResult
    else:
        return '{"bgm": "' + str(sD.bgm['nowplaying']) + '", "paused": "' + str(sD.bgm['paused']) + '", "volume": "' + str(sD.bgm['volume']) + '"}'

@app.route('/api/fightermatches')
def endpoint_api_fightermatches():
    loginResult = loginCheck(request.remote_addr, 'api')
    if loginResult:
        return loginResult
    else:
        return json.dumps(sD.fighter)

@app.route('/api/ip')
def endpoint_api_ip():
    # loginResult = loginCheck(request.remote_addr, 'api')
    # if loginResult:
    #     return loginResult
    # else:
        return '{"ip": "'+ ip +'"}'

#Sends back your student information
@app.route('/api/me')
def endpoint_api_me():
    loginResult = loginCheck(request.remote_addr, 'api')
    if loginResult:
        return loginResult
    else:
        return json.dumps(sD.studentDict[request.remote_addr])

@app.route('/api/mode')
def endpoint_api_mode():
    loginResult = loginCheck(request.remote_addr, 'api')
    if loginResult:
        return loginResult
    else:
        return '{"mode": "'+ str(sD.settings['barmode']) +'"}'

@app.route('/api/newpasswords')
def endpoint_api_newpasswords():
    loginResult = loginCheck(request.remote_addr, 'api')
    if loginResult:
        return loginResult
    else:
        return json.dumps(newPasswords)

@app.route('/api/permissions')
def endpoint_api_permissions():
    loginResult = loginCheck(request.remote_addr, 'api')
    if loginResult:
        return loginResult
    else:
        return json.dumps(sD.settings['perms'])

@app.route('/api/phrase')
def endpoint_api_phrase():
    loginResult = loginCheck(request.remote_addr, 'api')
    if loginResult:
        return loginResult
    else:
        return '{"phrase": "'+ str(sD.activePhrase) +'"}'

#Shows the different colors the pixels take in the virtualbar.
@app.route('/api/pix')
def endpoint_api_pix():
    loginResult = loginCheck(request.remote_addr, 'api')
    if loginResult:
        return loginResult
    else:
        if not ONRPi:
            global pixels
        return '{"pixels": "'+ str(pixels[:BARPIX]) +'"}'

@app.route('/api/quizname')
def endpoint_api_quizname():
    loginResult = loginCheck(request.remote_addr, 'api')
    if loginResult:
        return loginResult
    else:
        if sD.activeQuiz:
            return '{"quizname": "'+ str(sD.activeQuiz['name']) +'"}'
        else:
            return '{"error": "No quiz is currently loaded."}'

@app.route('/api/polls')
def endpoint_api_polls():
    loginResult = loginCheck(request.remote_addr, 'api')
    if loginResult:
        return loginResult
    else:
        db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
        dbcmd = db.cursor()
        polls = dbcmd.execute("SELECT * FROM polls").fetchall()
        db.close()
        return json.dumps(polls)

@app.route('/api/pollresponses')
def endpoint_api_pollresponses():
    loginResult = loginCheck(request.remote_addr, 'api')
    if loginResult:
        return loginResult
    else:
        db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
        dbcmd = db.cursor()
        responses = dbcmd.execute("SELECT * FROM responses").fetchall()
        db.close()
        return json.dumps(responses)

#This endpoints shows the actions the students did EX:TUTD up
@app.route('/api/students')
def endpoint_api_students():
    loginResult = loginCheck(request.remote_addr, 'api')
    if loginResult:
        return loginResult
    else:
        if not request.remote_addr in sD.studentDict:
            return '{"error": "You are not logged in."}'
        if sD.studentDict[request.remote_addr]['perms'] <= sD.settings['perms']['admin']:
            return json.dumps(sD.studentDict)
        elif sD.studentDict[request.remote_addr]['perms'] <= sD.settings['perms']['api']:
            return json.dumps(stripUserData())
        else:
            return '{"error": "Insufficient permissions."}'

# ██████
# ██   ██
# ██████
# ██   ██
# ██████


@app.route('/basic')
def endpoint_basic():
    return redirect('/quickpanel')


'''
    /bgm
    This endpoint leads to the Background music page
'''
@app.route('/bgm')
def endpoint_bgm():
    loginResult = loginCheck(request.remote_addr, 'bgm')
    if loginResult:
        return loginResult
    else:
        bgm.updateFiles()
        bgm_file = request.args.get('file')
        if bgm_file:
            if bgm_file == 'random':
                bgm_file = random.choice(list(bgm.bgm.keys()))
            if bgm_file in bgm.bgm:
                if time.time() - sD.bgm['lastTime'] >= 60 or sD.studentDict[request.remote_addr]['perms'] <= sD.settings['perms']['mod']:
                    sD.bgm['lastTime'] = time.time()
                    bgm_volume = request.args.get('volume')
                    try:
                        if request.args.get('volume'):
                            bgm_volume = float(bgm_volume)
                    except Exception as e:
                        logFile(" [warning] ", "Could not convert volume to float. Setting to default.")
                        bgm_volume = 0.5
                    sD.bgm['nowplaying']= bgm_file
                    if bgm_volume and type(bgm_volume) is float:
                        startBGM(bgm_file, bgm_volume)
                    else:
                        startBGM(bgm_file)
                    return render_template("message.html", message = 'Playing: ' + bgm_file)
                else:
                    if request.args.get('return') == 'json':
                        return '{error: "It has only been ' + str(int(time.time() - sD.bgm['lastTime'])) + ' seconds since the last song started. Please wait at least 60 seconds."}'
                    return render_template("message.html", message = "It has only been " + str(int(time.time() - sD.bgm['lastTime'])) + " seconds since the last song started. Please wait at least 60 seconds.")
            else:
                return render_template("message.html", message = "Cannot find that filename!")
        elif request.args.get('voladj'):
            if request.args.get('voladj') == 'up':
                volBGM('up')
                return render_template("message.html", message = 'Music volume increased by one increment.')
            elif request.args.get('voladj') == 'down':
                volBGM('down')
                return render_template("message.html", message = 'Music volume decreased by one increment.')
            else:
                try:
                    bgm_volume = float(request.args.get('voladj'))
                    volBGM(bgm_volume)
                    return render_template("message.html", message = 'Music volume set to ' + request.args.get('voladj') + '.')
                except Exception as e:
                    logFile("Error", +e)
                    return render_template("message.html", message = 'Invalid voladj. Use \'up\', \'down\', or a number from 0.0 to 1.0.')
        elif request.args.get('playpause'):
            playpauseBGM()
            if sD.bgm['paused']:
                return render_template("message.html", message = 'Music resumed.')
            else:
                return render_template("message.html", message = 'Music paused.')
        elif request.args.get('rewind'):
            rewindBGM()
            return render_template("message.html", message = 'Music rewound.')
        else:
            resString = '<a href="/bgmstop">Stop Music</a>'
            resString += '<h2>Now playing: ' + sD.bgm['nowplaying'] + '</h2>'
            resString += '<h2>List of available background music files:</h2><ul>'
            for key, value in bgm.bgm.items():
                resString += '<li><a href="/bgm?file=' + key + '">' + key + '</a></li>'
            resString += '</ul> You can play them by using \'<b>/bgm?file=&lt;sound file name&gt;&volume=&lt;0.0 - 1.0&gt;\'</b>'
            resString += '<br><br>You can stop them by using \'<b>/bgmstop</b>\''
            return render_template("general.html", content = resString, style = '<style>ul {columns: 2; -webkit-columns: 2; -moz-columns: 2;}</style>')

'''
    /bgmstop
    Stops the current background Music
'''
@app.route('/bgmstop')
def endpoint_bgmstop():
    sD.bgm['paused'] = False
    stopBGM()
    return render_template("message.html", message = 'Stopped music...')

@app.route('/bitshifter')
def endpoint_bitshifter():
    if request.args.get('advanced'):
        advanced = '?advanced=true'
    else:
        advanced = ''
    return redirect('/games/bitshifter' + advanced)

'''
    /break
    For when a student is temporarily unable to participate
'''

@app.route('/break')
def endpoint_break():
    loginResult = loginCheck(request.remote_addr)
    if loginResult:
        return loginResult
    else:
        name = request.args.get('name') or sD.studentDict[request.remote_addr]['name'].strip()
        if request.args.get('action') == 'request':
            if sD.studentDict[request.remote_addr]['perms'] == sD.settings['perms']['teacher']:
                return render_template("message.html", message = "Teachers can't request bathroom breaks.")
            if sD.studentDict[request.remote_addr]['help']['type']:
                return render_template("message.html", message = "You already have a help ticket or break request in.")
            else:
                sD.studentDict[request.remote_addr]['help']['type'] = 'break'
                sD.studentDict[request.remote_addr]['help']['time'] = time.time()
                playSFX("sfx_pickup02")
                socket_.emit('help', sD.studentDict[request.remote_addr]['help'], namespace=apinamespace)
                return render_template("message.html", message = "Your request was sent. The teacher still needs to approve it.")
        elif request.args.get('action') == 'end':
            if name != sD.studentDict[request.remote_addr]['name'] and sD.studentDict[request.remote_addr]['perms'] != sD.settings['perms']['teacher']:
                return render_template("message.html", message = "Only teachers can end other people's breaks.")
            #Find the student whose username matches the "name" argument
            for student in sD.studentDict:
                if sD.studentDict[student]['name'].strip() == name:
                    if sD.studentDict[student]['excluded']:
                        sD.studentDict[student]['excluded'] = False
                        sD.studentDict[student]['perms'] = sD.studentDict[student]['oldPerms']
                        #Disabled until chat works
                        #server.send_message(sD.studentDict[student], json.dumps(packMSG('alert', student, 'server', 'Your break was ended.')))
                        return render_template("break.html", excluded = sD.studentDict[request.remote_addr]['excluded'], ticket = json.dumps(sD.studentDict[request.remote_addr]['help']))
                    else:
                        return render_template("message.html", message = "This student is not currently taking a bathroom break.")
            return render_template("message.html", message = 'Student not found.')
        else:
            if sD.studentDict[request.remote_addr]['perms'] == sD.settings['perms']['teacher']:
                return render_template("message.html", message = "Teachers can't request bathroom breaks. To see students' tickets, go to /controlpanel.")
            return render_template("break.html", excluded = sD.studentDict[request.remote_addr]['excluded'], ticket = json.dumps(sD.studentDict[request.remote_addr]['help']))


#  ██████
# ██
# ██
# ██
#  ██████

@app.route('/changemode')
def endpoint_changemode():
    newMode = request.args.get('newMode') or ''
    direction = request.args.get('direction') or 'next'
    logFile(newMode)
    logFile(direction)
    return changeMode(newMode, direction)

@app.route('/changepassword', methods = ['POST', 'GET'])
def endpoint_changepassword():
    if request.method == 'POST':
        if 'username' in request.form:
            username = request.form['username']
        else:
            username = sD.studentDict[request.remote_addr]['name']
        db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
        dbcmd = db.cursor()
        userFound = dbcmd.execute("SELECT * FROM users WHERE username=:uname", {"uname": username}).fetchall()
        db.close()
        oldPassword = request.form['oldPassword']
        newPassword = request.form['newPassword']
        if userFound:
            if oldPassword:
                for user in userFound:
                    if username in user:
                        #Check if the password is correct
                        if oldPassword == cipher.decrypt(user[2]).decode():
                            passwordCrypt = cipher.encrypt(newPassword.encode())
                            db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
                            dbcmd = db.cursor()
                            dbcmd.execute("UPDATE users SET password=:pw WHERE username=:uname", {"uname": username, "pw": passwordCrypt})
                            db.commit()
                            db.close()
                            return render_template("message.html", message = "Password changed.", forward = '/')
                        else:
                            return render_template("message.html", message = "Your password is incorrect.")
            else:
                loggedIn = False
                for user in sD.studentDict:
                    if sD.studentDict[user]['name'].strip() == username:
                        loggedIn = True
                if loggedIn:
                    return render_template("message.html", message = "Someone is logged in with this username.")
                newPasswords[username] = newPassword
                playSFX("sfx_powerup01")
                return render_template("message.html", message = "Your password change needs to be approved by the teacher. You can use the Formbar as a guest while you wait.", forward = '/login')
        else:
            return render_template("message.html", message = "No users found with that username.")
    else:
        #If the user is logged in, check of they are a guest
        if request.remote_addr in sD.studentDict:
            username = sD.studentDict[request.remote_addr]['name']
            db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
            dbcmd = db.cursor()
            userFound = dbcmd.execute("SELECT * FROM users WHERE username=:uname", {"uname": username}).fetchall()
            db.close()
            if not userFound:
                return render_template("message.html", message = "You are logged in as a guest.")
        return render_template('changepassword.html', loggedIn = request.remote_addr in sD.studentDict)

'''
    /chat
    This endpoint allows students and teacher to chat realTime.
'''
@app.route('/chat')
def endpoint_chat():
    loginResult = loginCheck(request.remote_addr)
    if loginResult:
        return loginResult
    else:
        db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
        dbcmd = db.cursor()
        messages = dbcmd.execute("SELECT * FROM messages").fetchall()
        db.close()
        for i, message in enumerate(messages):
            message = list(message)
            message[4] = cipher.decrypt(message[4]).decode()
            messages[i] = message
        return render_template("chat.html", username = sD.studentDict[request.remote_addr]['name'], messages = json.dumps(messages))

@app.route('/cleartable')
def endpoint_cleartable():
    loginResult = loginCheck(request.remote_addr, 'teacher')
    if loginResult:
        return loginResult
    else:
        if table:
            db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
            dbcmd = db.cursor()
            dbcmd.execute("DELETE FROM " + table)
            db.commit()
            db.close()
            playSFX("sfx_explode01")
            return render_template("message.html", message = "Data in " + table + " deleted.")
        else:
            return render_template("message.html", message = "Missing table argument.")

'''
    /color
    Change the color of the entire bar
    Query Parameters:
        hex = six hexadecimal digit rgb color (prioritizes over RGB)
        r, g, b = provide three color values between 0 and 255
'''
@app.route('/color')
def endpoint_color():
    loginResult = loginCheck(request.remote_addr, 'bar')
    if loginResult:
        return loginResult
    else:
        try:
            r = int(request.args.get('r'))
            g = int(request.args.get('g'))
            b = int(request.args.get('b'))
        except Exception as e:
            logFile("Error", e)
            r = ''
            g = ''
            b = ''
        hex = request.args.get('hex')
        if hex and hex2dec(hex):
            fillBar(hex2dec(hex))
        elif not r == '' and not b == '' and not g == '':
            fillBar((r, g, b))
        else:
            return render_template("message.html", message = "Bad ArgumentsTry <b>/color?hex=FF00FF</b> or <b>/color?r=255&g=0&b=255</b>", forward = '/home')
        if ONRPi:
            pixels.show()
        return render_template("message.html", message = "Color sent!", forward = '/home')

#This endpoint is exclusive only to the teacher.
@app.route('/controlpanel', methods = ['POST', 'GET'])
def endpoint_controlpanel():
    loginResult = loginCheck(request.remote_addr, 'admin')
    if loginResult:
        return loginResult
    else:
        resString = ''
        #Loop through every arg that was sent as a query parameter
        for arg in request.args:
            if arg != 'advanced':
                #See if you save the
                argVal = str2bool(request.args.get(arg))
                #if the argVal resolved to a boolean value
                if isinstance(argVal, bool):
                    if arg in sD.settings:
                        sD.settings[arg] = argVal
                        resString += 'Set <i>' + arg + '</i> to: <i>' + str(argVal) + "</i>"
                        db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
                        dbcmd = db.cursor()
                        dbcmd.execute("UPDATE settings SET " + arg + "=:value", {"value": argVal})
                        db.commit()
                        db.close()
                    else:
                        resString += 'There is no setting that takes \'true\' or \'false\' named: <i>' + arg + "</i>"
                else:
                    try:
                        argInt = int(request.args.get(arg))
                        if arg in sD.settings['perms']:
                            if argInt > 4 or argInt < 0:
                                resString += "Permission value out of range! "
                            else:
                                sD.settings['perms'][arg] = argInt
                                db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
                                dbcmd = db.cursor()
                                dbcmd.execute("UPDATE settings SET " + arg + "Perm=:value", {"value": argInt})
                                db.commit()
                                db.close()
                    except Exception as e:
                        logFile("Error", e)
                        pass

        ###
        ### Everything past this point uses the old method of changing settings. Needs updated
        ###

        if request.args.get('students'):
            sD.settings['numStudents'] = int(request.args.get('students'))
            if sD.settings['numStudents'] == 0:
                sD.settings['autocount'] = True
                autoStudentCount()
            else:
                sD.settings['autocount'] = False
                resString += 'Set <i>numStudents</i> to: ' + str(sD.settings['numStudents'])
        if request.args.get('barmode'):
            if request.args.get('barmode') in sD.settings['modes']:
                sD.settings['barmode'] = request.args.get('barmode')
                resString += 'Set <i>mode</i> to: ' + sD.settings['barmode']
            else:
                resString += 'No setting called ' + sD.settings['barmode']
        if resString == '':
            return render_template("controlpanel.html", data = json.dumps(sD.settings))
        else:
            playSFX("sfx_pickup01")
            resString += ""
            return render_template("message.html", message = resString)


@app.route('/countdown')
def endpoint_countdown():
    return render_template("message.html", message = 'This feature is not available yet.')

@app.route('/createaccount')
def endpoint_createaccount():
    loginResult = loginCheck(request.remote_addr, 'teacher')
    if loginResult:
        return loginResult
    else:
        name = request.args.get('name')
        db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
        dbcmd = db.cursor()
        userFound = dbcmd.execute("SELECT * FROM users WHERE username=:uname", {"uname": name}).fetchall()
        db.close()
        if userFound:
            return render_template("message.html", message = 'There is already a user with that name.')
        else:
            password = request.args.get('password')
            passwordCrypt = cipher.encrypt(password.encode())
            db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
            dbcmd = db.cursor()
            dbcmd.execute("INSERT INTO users (username, password, permissions, bot) VALUES (?, ?, ?, ?)", (name, passwordCrypt, sD.settings['perms']['anyone'], "False"))
            db.commit()
            db.close()
            return render_template("message.html", message = 'Account created.')

@app.route('/createfightermatch', methods = ['POST'])
def endpoint_createfightermatch():
    code = request.args.get('code')
    name = request.args.get('name')
    public = request.args.get('public')
    if code in sD.fighter:
        return render_template("message.html", message = 'A match with this code already exists.')
    sD.fighter[code] = {} #Create new object for match
    sD.fighter[code]['creator'] = name #Set "creator" of object to arg "name"
    sD.fighter[code]['public'] = public
    return render_template("message.html", message = 'Match ' + code + ' created by ' + name + '.')

# ██████
# ██   ██
# ██   ██
# ██   ██
# ██████


'''
    /DEBUG
'''
@app.route('/debug')
def endpoint_debug():
    return render_template('debug.html')

# ███████
# ██
# █████
# ██
# ███████


'''
@app.route('/emptyblocks')
def endpoint_emptyblocks():
    blockList = []
    if ONRPi:
        pixels.fill((0,0,0))
    else:
        pixels = [(0,0,0)] * MAXPIX
    if ONRPi:
        pixels.show()
    return render_template("message.html", message = "Emptied blocks")
'''

#Start a poll
@app.route('/endpoll')
def endpoll():
    loginResult = loginCheck(request.remote_addr, 'mod')
    if loginResult:
        return loginResult
    else:
        if not sD.pollType:
            return render_template("message.html", message = 'There is no active poll right now.')
        db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
        dbcmd = db.cursor()
        dbcmd.execute("INSERT INTO polls ('type', 'time') VALUES (?, ?)", (sD.pollType, int(time.time() * 1000)))
        for user in sD.studentDict:
            if sD.studentDict[user]['perms'] == sD.settings['perms']['student']:
                response = sD.studentDict[user]['thumb'] or sD.studentDict[user]['letter'] or sD.studentDict[user]['essay']
                response = response.replace('"', '\\"') #Escape quotes
                dbcmd.execute("INSERT INTO responses ('poll', 'name', 'response') VALUES (?, ?, ?)", (sD.pollID, sD.studentDict[user]['name'], response))
        db.commit()
        db.close()
        changeMode('poll')
        repeatMode()
        return render_template("message.html", message = 'Poll ended. Results saved.')

'''
/essay
'''
@app.route('/essay', methods = ['POST', 'GET'])
def endpoint_essay():
    loginResult = loginCheck(request.remote_addr)
    if loginResult:
        return loginResult
    else:
        if request.method == 'POST':
            if request.form:
                essay = request.form['essay']
            else:
                essay = request.args.get('essay')
            if sD.settings['barmode'] == 'text':
                if not essay and sD.studentDict[request.remote_addr]['essay']:
                    #Response unsubmitted
                    playSFX("sfx_hit01")
                sD.studentDict[request.remote_addr]['essay'] = essay
                textBar()
                socket_.emit('essay', {'name': sD.studentDict[request.remote_addr]['name'], 'essay': essay}, namespace=apinamespace)
                return render_template("message.html", message = "Response submitted.")
            else:
                return render_template("message.html", message = "Not in Essay mode.")
        else:
            return render_template('thumbsrental.html')


@app.route('/expert')
def endpoint_expert():
    return redirect('/advanced')

# ███████
# ██
# █████
# ██
# ██


@app.route('/fighter')
def endpoint_fighter():
    if request.args.get('advanced'):
        advanced = '?advanced=true'
    else:
        advanced = ''
    return redirect('/games/fighter' + advanced)


'''
    /flashcards
'''
@app.route('/flashcards')
def endpoint_flashcards():
    if request.args.get('advanced'):
        advanced = '?advanced=true'
    else:
        advanced = ''
    return redirect('/games/flashcards' + advanced)

'''
    /flush
'''
@app.route('/flush')
def endpoint_flush():
    loginResult = loginCheck(request.remote_addr, 'admin')
    if loginResult:
        return loginResult
    else:
        flushUsers()
        endMode()
        sD.refresh()
        return render_template("message.html", message = "Session was restarted.")

#  ██████
# ██
# ██   ███
# ██    ██
#  ██████


@app.route('/games/2048')
def endpoint_games_2048():
    loginResult = loginCheck(request.remote_addr, 'games')
    if loginResult:
        return loginResult
    else:
        username = sD.studentDict[request.remote_addr]['name']
        db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
        dbcmd = db.cursor()
        highScore = dbcmd.execute("SELECT * FROM scores WHERE username=:uname AND game='2048' ORDER BY score DESC", {"uname": username}).fetchone()
        db.close()
        if highScore:
            highScore = highScore[3]
        else:
            highScore = 0
        return render_template('games/2048.html', highScore = highScore)

@app.route('/games/bitshifter')
def endpoint_games_bitshifter():
    loginResult = loginCheck(request.remote_addr, 'games')
    if loginResult:
        return loginResult
    else:
        username = sD.studentDict[request.remote_addr]['name']
        db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
        dbcmd = db.cursor()
        highScore = dbcmd.execute("SELECT * FROM scores WHERE username=:uname AND game='bitshifter' ORDER BY score DESC", {"uname": username}).fetchone()
        db.close()
        if highScore:
            highScore = highScore[3]
        else:
            highScore = 0
        return render_template('games/bitshifter.html', highScore = highScore)

@app.route('/games/fighter', methods = ['GET', 'POST'])
def endpoint_games_fighter():
    loginResult = loginCheck(request.remote_addr, 'games')
    if loginResult:
        return loginResult
    else:
        username = sD.studentDict[request.remote_addr]['name']
        if request.form:
            action = request.form['action']
            password = request.form['password']
        else:
            action = request.args.get('action')
            password = ''
        authenticated = False
        if action == 'resetStats':
            if password:
                db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
                dbcmd = db.cursor()
                user = dbcmd.execute("SELECT * FROM users WHERE username=:uname", {"uname": username}).fetchone()
                db.close()
                #Check if the password is correct
                if password == cipher.decrypt(user[2]).decode():
                    authenticated = True
                else:
                    return render_template("message.html", message = "Your password is incorrect.")
            else:
                return render_template('authenticate.html', forward = request.path, action = action)

        try:
            db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
            dbcmd = db.cursor()
            wins = dbcmd.execute("SELECT fighterWins FROM users WHERE username=:uname", {"uname": username}).fetchone()[0] or 0
            losses = dbcmd.execute("SELECT fighterLosses FROM users WHERE username=:uname", {"uname": username}).fetchone()[0] or 0
            winStreak = dbcmd.execute("SELECT fighterWinStreak FROM users WHERE username=:uname", {"uname": username}).fetchone()[0] or 0
            goldUnlocked = dbcmd.execute("SELECT goldUnlocked FROM users WHERE username=:uname", {"uname": username}).fetchone()[0] or 0
            db.close()
            return render_template('games/fighter.html', username = username, wins = wins, losses = losses, winStreak = winStreak, goldUnlocked = goldUnlocked, action = action, authenticated = authenticated)
        except Exception as e:
            logFile("Error", str(e))


'''
    /games/flashcards
'''
@app.route('/games/flashcards')
def endpoint_games_flashcards():
    loginResult = loginCheck(request.remote_addr)
    if loginResult:
        return loginResult
    else:
        return render_template('games/flashcards.html')

#This endpoint takes you to the hangman game
@app.route('/games/hangman')
def endpoint_games_hangman():
    loginResult = loginCheck(request.remote_addr, 'games')
    if loginResult:
        return loginResult
    else:
        if sD.lesson:
            if sD.lesson.vocab:
                wordObj = sD.lesson.vocab
        else:
            #Need more generic words here
            wordObj = {
                'place': 'your',
                'words': 'here'
            }
        username = sD.studentDict[request.remote_addr]['name']
        db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
        dbcmd = db.cursor()
        highScore = dbcmd.execute("SELECT * FROM scores WHERE username=:uname AND game='hangman' ORDER BY score DESC", {"uname": username}).fetchone()
        db.close()
        if highScore:
            highScore = highScore[3]
        else:
            highScore = 0
        return render_template("games/hangman.html", wordObj=wordObj, highScore = highScore)

'''
    /games/idle
'''
@app.route('/games/idle')
def endpoint_games_idle():
    loginResult = loginCheck(request.remote_addr)
    if loginResult:
        return loginResult
    else:
        return render_template('games/idle.html')

@app.route('/games/minesweeper')
def endpoint_games_minesweeper():
    loginResult = loginCheck(request.remote_addr, 'games')
    if loginResult:
        return loginResult
    else:
        cols = 20
        rows = 20
        dense = 10
        if request.args.get('cols'):
            cols = request.args.get('cols')
        if request.args.get('rows'):
            rows = request.args.get('rows')
        if request.args.get('dense'):
            dense = request.args.get('dense')
        username = sD.studentDict[request.remote_addr]['name']
        db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
        dbcmd = db.cursor()
        bestTime = dbcmd.execute("SELECT * FROM scores WHERE username=:uname AND game='minesweeper' ORDER BY score ASC", {"uname": username}).fetchone()
        db.close()
        if bestTime:
            bestTime = bestTime[3]
        else:
            bestTime = 0
        return render_template("games/mnsw.html", cols=cols, rows=rows, dense=dense, bestTime=bestTime)

@app.route('/games/speedtype')
def endpoint_games_speedtype():
    loginResult = loginCheck(request.remote_addr, 'games')
    if loginResult:
        return loginResult
    else:
        username = sD.studentDict[request.remote_addr]['name']
        db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
        dbcmd = db.cursor()
        highScore = dbcmd.execute("SELECT * FROM scores WHERE username=:uname AND game='speedtype' ORDER BY score DESC", {"uname": username}).fetchone()
        db.close()
        if highScore:
            highScore = highScore[3]
        else:
            highScore = 0
        return render_template("games/speedtype.html", highScore = highScore)

@app.route('/games/towerdefense')
def endpoint_games_towerdefense():
    loginResult = loginCheck(request.remote_addr, 'games')
    if loginResult:
        return loginResult
    else:
        username = sD.studentDict[request.remote_addr]['name']
        db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
        dbcmd = db.cursor()
        progress = dbcmd.execute("SELECT tdProgress FROM users WHERE username=:uname", {"uname": username}).fetchone()[0] or ''
        achievements = dbcmd.execute("SELECT tdAchievements FROM users WHERE username=:uname", {"uname": username}).fetchone()[0] or ''
        db.close()
        return render_template('games/towerdefense.html', progress = progress, achievements = achievements)

#Tic Tac Toe
@app.route('/games/ttt')
def endpoint_games_ttt():
    loginResult = loginCheck(request.remote_addr, 'games')
    if loginResult:
        return loginResult
    else:
        opponent = request.args.get('opponent')

        if opponent == sD.studentDict[request.remote_addr]['name']:
            return render_template("message.html", message = "You can't enter your own name.")

        db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
        dbcmd = db.cursor()
        wins = dbcmd.execute("SELECT * FROM scores WHERE username=:uname AND game='ttt' ORDER BY score DESC", {"uname": sD.studentDict[request.remote_addr]['name']}).fetchone()
        if wins:
            wins = wins[3]
        else:
            wins = 0
        db.close()

        #Loop through all existing games
        for game in sD.ttt:
            #If the user and the opponent is in an existing player list
            if sD.studentDict[request.remote_addr]['name'] in game.players and opponent in game.players:
                #Then you have found the right game and can edit it here
                return render_template("games/ttt.html", game = json.dumps(game.__dict__), username = sD.studentDict[request.remote_addr]['name'], wins = wins)
                #return the response here

        #Creating a new game
        for student in sD.studentDict:
            if sD.studentDict[student]['name'] == opponent:
                sD.ttt.append(sessions.TTTGame([sD.studentDict[request.remote_addr]['name'], opponent]))
                return render_template("games/ttt.html", game = json.dumps(sD.ttt[-1].__dict__), username = sD.studentDict[request.remote_addr]['name'], wins = wins)

        if opponent:
            return render_template("message.html", message = "There are no users with that name.")

        return render_template("tttstart.html")

@app.route('/games/wordle')
def endpoint_games_wordle():
    loginResult = loginCheck(request.remote_addr, 'games')
    if loginResult:
        return loginResult
    else:
        username = sD.studentDict[request.remote_addr]['name']
        db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
        dbcmd = db.cursor()
        highScore = dbcmd.execute("SELECT * FROM scores WHERE username=:uname AND game='wordle' ORDER BY score DESC", {"uname": username}).fetchone()
        db.close()
        if highScore:
            highScore = highScore[3]
        else:
            highScore = 0
        return render_template('games/wordle.html', wordList = str(words.keys()), highScore = highScore)

@app.route('/getword')
def endpoint_getword():
    if request.args.get('number'):
        try:
            number = int(request.args.get('number'))
            wordlist = []
            for i in range(number):
                wordlist.append(random.choice(list(words.keys())))
            return json.dumps(wordlist)
        except Exception as e:
            logFile("Error", "Could not convert number. " + str(e))
            return render_template("message.html", message = "Could not convert number. " + str(e))
    else:
        word = random.choice(list(words.keys()))
        return str(word)

# ██   ██
# ██   ██
# ███████
# ██   ██
# ██   ██


@app.route('/hangman')
def endpoint_hangman():
    if request.args.get('advanced'):
        advanced = '?advanced=true'
    else:
        advanced = ''
    return redirect('/games/hangman' + advanced)

@app.route('/help', methods = ['POST', 'GET'])
def endpoint_help():
    loginResult = loginCheck(request.remote_addr, 'teacher')
    if loginResult:
        return loginResult
    else:
        name = sD.studentDict[request.remote_addr]['name']
        name = name.strip()
        if sD.studentDict[request.remote_addr]['help']['type']:
            return render_template("message.html", message = "You already have a help ticket or break request in. If your problem is time-sensitive, or your last ticket was not cleared, please get the teacher's attention manually.")
        elif request.method == 'POST':
            sD.studentDict[request.remote_addr]['help']['type'] = 'help'
            sD.studentDict[request.remote_addr]['help']['time'] = time.time()
            sD.studentDict[request.remote_addr]['help']['message'] = request.args.get('message')
            playSFX("sfx_up04")
            socket_.emit('help', sD.studentDict[request.remote_addr]['help'], namespace=apinamespace)
            return render_template("message.html", message = "Your ticket was sent. Keep working on the problem the best you can while you wait.", forward = sD.mainPage)
        else:
            return render_template("help.html")


@app.route('/home')
def endpoint_home():
    loginResult = loginCheck(request.remote_addr)
    if loginResult:
        return loginResult
    else:
        return render_template("index.html")

# ██
# ██
# ██
# ██
# ███████

@app.route('/leaderboards')
def endpoint_leaderboards():
    loginResult = loginCheck(request.remote_addr)
    if loginResult:
        return loginResult
    else:
        game = request.args.get('game') or ''
        db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
        dbcmd = db.cursor()
        data = dbcmd.execute("SELECT * FROM scores ORDER BY score DESC").fetchall()
        db.close()
        return render_template("leaderboards.html", game = game, data = json.dumps(data))

'''
    /lesson
    (Teacher)
    GET: This will take you to the lesson management page.
        QUERY PARAMS:
    POST: Submit a lesson excel spreadsheet for upload.
            (This needs validation on upload!)
'''
@app.route('/lesson', methods = ['POST', 'GET'])
def endpoint_lesson():
    loginResult = loginCheck(request.remote_addr, 'bar')
    if loginResult:
        return loginResult
    else:
        if request.method == 'POST':
            if not request.files['file']:
                return render_template("message.html", message = 'Lesson file required.')
            else:
                f = request.files['file']
                f.save(os.path.join('lessondata', secure_filename(f.filename.strip(' '))))
                if request.args.get('advanced'):
                    advanced = '?advanced=true'
                else:
                    advanced = ''
                return redirect('/lesson' + advanced)
        elif request.args.get('load'):
            try:
                sD.refresh()
                sD.lessonList = lessons.updateFiles()
                sD.lesson = lessons.readBook(request.args.get('load'))
                if request.args.get('advanced'):
                    advanced = '?advanced=true'
                else:
                    advanced = ''
                return redirect('/lesson' + advanced)
            except Exception as e:
                logFile("Error", traceback.format_exc())
                logFile("Error", e)
                return render_template("message.html", message = '<b>Error:</b> ' + str(e))
        elif request.args.get('action'):
            if request.args.get('action') == 'next':
                sD.currentStep += 1
                if sD.currentStep >= len(sD.lesson.steps):
                    sD.currentStep = len(sD.lesson.steps)
                    return render_template("message.html", message = 'End of lesson!')
                else:
                    updateStep()
                    if request.args.get('advanced'):
                        advanced = '?advanced=true'
                    else:
                        advanced = ''
                    return redirect('/lesson' + advanced)
            elif request.args.get('action') == 'prev':
                sD.currentStep -= 1
                if sD.currentStep <= 0:
                    sD.currentStep = 0
                    return render_template("message.html", message = 'Already at start of lesson!')
                else:
                    updateStep()
                    if request.args.get('advanced'):
                        advanced = '?advanced=true'
                    else:
                        advanced = ''
                    return redirect('/lesson' + advanced)
            elif request.args.get('action') == 'unload':
                sD.refresh()
                return render_template("message.html", message = 'Unloaded lesson.')
            elif request.args.get('action') == 'upload':
                return render_template('general.html', content='<form method=post enctype=multipart/form-data><input type=file name=file accept=".xlsx"><input type=submit value=Upload></form>')
            else:
                if request.args.get('advanced'):
                    advanced = '?advanced=true'
                else:
                    advanced = ''
                return redirect('/lesson' + advanced)
        else:
            if not sD.lesson:
                sD.lessonList = lessons.updateFiles()
                resString = '<a href="/lesson?action=upload">Upload a Lesson</a><br>'
                resString += '<ul>'
                for lesson in sD.lessonList:
                    resString += '<li><a href="/lesson?load=' + lesson + '">' + lesson + '</a></li>'
                resString +='</ul>'
                return render_template('general.html', content=resString)
            else:
                resString = '<a href="/lesson?action=prev">Last Step</a>'
                resString += '<a href="/lesson?action=next">Next Step</a><br>'
                resString += '<a href="/lesson?action=unload">Unload Lesson</a>'
                resString += '<h2>Current Step: ' + str(sD.lesson.steps[sD.currentStep]['Prompt']) + '</h2>'
                resString += '<table>'
                #Agenda
                for i, item in enumerate(sD.lesson.agenda):
                    resString += '<tr>'
                    if not i:
                        for col in item:
                            resString += '<td class="header">' + col + '</td>'
                        resString += '</tr><tr>'
                    for col in item:
                        resString += '<td class="row">' + str(item[col]) + '</td>'
                    resString += '</div>'
                #Steps
                for i, item in enumerate(sD.lesson.steps):
                    resString += '<tr>'
                    if not i:
                        for col in item:
                            resString += '<td class="header">' + col + '</td>'
                        resString += '</tr><tr>'
                    for col in item:
                        resString += '<td class="row">' + str(item[col]) + '</td>'
                    resString += '</div>'
                #Objectives
                for i, item in enumerate(sD.lesson.objectives):
                    resString += '<tr>'
                    if not i:
                        for col in item:
                            resString += '<td class="header">' + col + '</td>'
                        resString += '</tr><tr>'
                    for col in item:
                        resString += '<td class="row">' + str(item[col]) + '</td>'
                    resString += '</div>'
                #Resources
                for i, item in enumerate(sD.lesson.links):
                    resString += '<tr>'
                    if not i:
                        for col in item:
                            resString += '<td class="header">' + col + '</td>'
                        resString += '</tr><tr>'
                    for col in item:
                        resString += '<td class="row">' + str(item[col]) + '</td>'
                    resString += '</div>'
                updateStep()
                return render_template('general.html', content=resString, style='<style>.header{font-weight: bold;}.row:nth-child(odd){background-color: #aaaaaa;}.row:nth-child(even){background-color: #cccccc;}.entry{}</style>')

'''
    /login
    Handles logging into the Formbar
'''
@app.route('/login', methods = ['POST', 'GET'])
def endpoint_login():
    remote = request.remote_addr
    if remote in banList:
        return render_template("message.html", message = "This IP is in the banlist.")
    else:
        if request.method == 'POST':
            username = request.form['username']
            username = username.strip()
            password = request.form['password']
            passwordCrypt = cipher.encrypt(password.encode()) #Required to be bytes?
            userType = request.form['userType']
            forward = request.form['forward']
            bot = request.form['bot']
            bot = bot.lower() == "true"


            if userType == "login":
                if username and password:
                    #Open and connect to database
                    db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
                    dbcmd = db.cursor()
                    userFound = dbcmd.execute("SELECT * FROM users WHERE username=:uname", {"uname": username}).fetchall()
                    db.close()
                    if userFound:
                        for user in userFound:
                            if username in user:
                                #Check if the password is correct
                                if password == cipher.decrypt(user[2]).decode():
                                    newStudent(remote, username, bot=bot)
                                    if bot:
                                        return json.dumps({'status': 'success'})
                                    if forward:
                                        return redirect(forward, code=302)
                                    else:
                                        return redirect('/', code=302)
                                else:
                                    if bot:
                                        return json.dumps({'status': 'failed', 'reason': 'credentials'})
                                    else:
                                        return render_template("message.html", message = "Your password is incorrect.")
                    else:
                        return render_template("message.html", message = "No users found with that username.")
                else:
                    return render_template("message.html", message = "You need to enter a username and password.")

            elif userType == "new":
                #Open and connect to database
                db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
                dbcmd = db.cursor()
                userFound = dbcmd.execute("SELECT * FROM users WHERE username=:uname", {"uname": username}).fetchall()
                db.close()
                #Search everyone currently logged in for same username
                for user in sD.studentDict:
                    if sD.studentDict[user]['name'].strip() == username:
                        userFound = True
                if userFound:
                    return render_template("message.html", message = "There is already a user with that name.")
                else:
                    db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
                    dbcmd = db.cursor()
                    #Add user to database
                    userFound = dbcmd.execute("INSERT INTO users (username, password, permissions, bot) VALUES (?, ?, ?, ?)", (username, passwordCrypt, sD.settings['perms']['anyone'], str(bot)))
                    db.commit()
                    db.close()
                    newStudent(remote, username, bot=bot)
                    if forward:
                        return redirect(forward, code=302)
                    else:
                        return redirect('/', code=302)

            elif userType == "guest":
                #Open and connect to database
                db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
                dbcmd = db.cursor()
                userFound = dbcmd.execute("SELECT * FROM users WHERE username=:uname", {"uname": username}).fetchall()
                db.close()
                for user in sD.studentDict:
                    if sD.studentDict[user]['name'].strip() == username:
                        userFound = True
                if userFound:
                    return render_template("message.html", message = "There is already a user with that name.")
                else:
                    newStudent(remote, username)
                    if forward:
                        return redirect(forward, code=302)
                    else:
                        return redirect('/', code=302)

        else:
            #If the user is logged in, log them out
            if remote in sD.studentDict:
                logFile("Info " + sD.studentDict[request.remote_addr]['name'],  " logged out.")
                socket_.emit('alert', json.dumps(packMSG('all', 'server', sD.studentDict[request.remote_addr]['name'] + " logged out...")), namespace=chatnamespace)
                del sD.studentDict[request.remote_addr]
                playSFX('sfx_laser01')
            if request.args.get('name'): ##needs update
                newStudent(remote, request.args.get('name'))
                return redirect('/', code=302)
            return render_template("login.html")

@app.route('/logout')
def endpoint_logout():
    return redirect('/login')

# ███    ███
# ████  ████
# ██ ████ ██
# ██  ██  ██
# ██      ██

@app.route('/minesweeper')
def endpoint_minesweeper():
    if request.args.get('advanced'):
        advanced = '?advanced=true'
    else:
        advanced = ''
    return redirect('/games/minesweeper' + advanced)


@app.route('/mnsw')
def endpoint_mnsw():
    if request.args.get('advanced'):
        advanced = '?advanced=true'
    else:
        advanced = ''
    return redirect('/games/minesweeper' + advanced)

'''
    /mobile
    Homepage for mobile devices
'''
@app.route('/mobile')
def endpoint_mobile():
    loginResult = loginCheck(request.remote_addr)
    if loginResult:
        return loginResult
    else:
        sounds = []
        music = []
        for key, value in sfx.sound.items():
            sounds.append(key)
        for key, value in bgm.bgm.items():
            music.append(key)
        return render_template("mobile.html", sfx = sounds, bgm = music)

# ██████
# ██   ██
# ██████
# ██
# ██


@app.route('/perc')
def endpoint_perc():
    loginResult = loginCheck(request.remote_addr, 'bar')
    if loginResult:
        return loginResult
    else:
        percAmount = request.args.get('amount')
        try:
            percAmount = int(percAmount)
            percFill(percAmount)
        except Exception as e:
            logFile("Error", e)
            return render_template("message.html", message = "<b>amount</b> must be an integer between 0 and 100 \'/perc?amount=<b>50</b>\'", forward = '/home')
        return render_template("message.html", message = "Set perecentage to: " + str(percAmount) + ".", forward = '/home')

'''
    /profile
'''
@app.route('/profile')
def endpoint_profile():
    loginResult = loginCheck(request.remote_addr, 'banned')
    if loginResult:
        return loginResult
    else:
        name = request.args.get('user') or sD.studentDict[request.remote_addr]['name']
        userFound = False
        for x in sD.studentDict:
            user = sD.studentDict[x]
            if user['name'].strip() == name:
                userFound = True
        if not userFound:
            db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
            dbcmd = db.cursor()
            userFound = dbcmd.execute("SELECT * FROM users WHERE username=:uname", {"uname": name}).fetchall()
            db.close()
        if userFound:
            db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
            dbcmd = db.cursor()
            digipogs = dbcmd.execute("SELECT digipogs FROM users WHERE username=:uname AND digipogs",  {"uname": user['name']}).fetchone()
            highScores = {
                "2048": dbcmd.execute("SELECT * FROM scores WHERE username=:uname AND game='2048' ORDER BY score DESC", {"uname": user['name']}).fetchone(),
                "bitshifter": dbcmd.execute("SELECT * FROM scores WHERE username=:uname AND game='bitshifter' ORDER BY score DESC", {"uname": user['name']}).fetchone(),
                "hangman": dbcmd.execute("SELECT * FROM scores WHERE username=:uname AND game='hangman' ORDER BY score DESC", {"uname": user['name']}).fetchone(),
                "minesweeper": dbcmd.execute("SELECT * FROM scores WHERE username=:uname AND game='minesweeper' ORDER BY score ASC", {"uname": user['name']}).fetchone(),
                "speedtype": dbcmd.execute("SELECT * FROM scores WHERE username=:uname AND game='speedtype' ORDER BY score DESC", {"uname": user['name']}).fetchone(),
                "towerdefense": dbcmd.execute("SELECT * FROM scores WHERE username=:uname AND game='towerdefense' ORDER BY score DESC", {"uname": user['name']}).fetchone(),
                "ttt": dbcmd.execute("SELECT * FROM scores WHERE username=:uname AND game='ttt' ORDER BY score DESC", {"uname": user['name']}).fetchone(),
                "fighter": dbcmd.execute("SELECT * FROM scores WHERE username=:uname AND game='fighter' ORDER BY score DESC", {"uname": user['name']}).fetchone(),
                "wordle": dbcmd.execute("SELECT * FROM scores WHERE username=:uname AND game='wordle' ORDER BY score DESC", {"uname": user['name']}).fetchone(),
            }
            db.close()
            return render_template("profile.html", username = user['name'], perms = sD.settings['permname'][user['perms']], bot = user['bot'], highScores = json.dumps(highScores), digipogs = digipogs[0])
        #If there are no matches
        return render_template("message.html", message = "There are no users with that name.")

'''
    /progress
'''
@app.route('/progress', methods = ['POST', 'GET'])
def endpoint_progress():
    loginResult = loginCheck(request.remote_addr)
    if loginResult:
        return loginResult
    else:
        if request.args.get('check'):
            try:
                check = int(request.args.get('check'))
                sD.studentDict[request.remote_addr]['progress'][check] = not sD.studentDict[request.remote_addr]['progress'][check]
                percAmount = sD.lesson.checkProg(sD.studentDict)
                if sD.settings['barmode'] == 'progress':
                    percFill(percAmount)
                return str(check) + " was toggled."
            except Exception as e:
                logFile("Error", e)
                return render_template("message.html", message = '<b>Error:</b> ' + str(e))
        else:
            if sD.activeProgress:
                return render_template('progress.html', progress=sD.activeProgress)
            else:
                return render_template("message.html", message = 'There is no progress tracker active right now.')

#  ██████
# ██    ██
# ██    ██
# ██ ▄▄ ██
#  ██████
#     ▀▀


'''
    /quickpanel
    Only the most-used features
'''
@app.route('/quickpanel')
def endpoint_quickpanel():
    loginResult = loginCheck(request.remote_addr)
    if loginResult:
        return loginResult
    else:
        sounds = []
        music = []
        for key, value in sfx.sound.items():
            sounds.append(key)
        for key, value in bgm.bgm.items():
            music.append(key)
        return render_template("quickpanel.html", sfx = sounds, bgm = music)


#takes you to a quiz(literally)
@app.route('/quiz', methods = ['POST', 'GET'])
def endpoint_quiz():
    loginResult = loginCheck(request.remote_addr, 'student')
    if loginResult:
        return loginResult
    else:
        if request.method == 'POST':
            messageOut = packMSG('alert', 'all', 'server', 'The teacher started a quiz.<br><button onclick="window.location=\"/quiz\"">Open quiz</button>')
            socket_.emit('message', json.dumps(messageOut))
            resString = '<ul>'
            for i, answer in enumerate(request.form):
                resString += '<li>' + str(i) + ': '
                if sD.activeQuiz['keys'][i] == int(request.form[answer]):
                    sD.studentDict[request.remote_addr]['quizRes'].append(True)
                    resString += '<b>Correct!</b></li>'
                else:
                    sD.studentDict[request.remote_addr]['quizRes'].append(False)
                    resString += 'Incorrect</li>'
                    sD.studentDict[request.remote_addr]['complete'] = True
                    return render_template('general.html', content=resString)
        elif sD.activeQuiz:
            return render_template('quiz.html', quiz=sD.activeQuiz)
        else:
            return render_template("message.html", message = "No quiz is currently loaded.")

# ██████
# ██   ██
# ██████
# ██   ██
# ██   ██

@app.route('/removefightermatch', methods = ['POST'])
def endpoint_removefightermatch():
    code = request.args.get('code')
    if code in sD.fighter:
        del sD.fighter[code]
        return render_template("message.html", message = 'Match ' + code + ' removed.')
    return render_template("message.html", message = 'Could not remove match.')

@app.route('/removetttmatch', methods = ['POST'])
def endpoint_removetttmatch():
    opponent = request.args.get('opponent')
    for game in sD.ttt:
        if sD.studentDict[request.remote_addr]['name'] in game.players and opponent in game.players:
            sD.ttt.remove(game)
            return render_template("message.html", message = 'Match removed.')
    return render_template("message.html", message = 'Match not found.')

# ███████
# ██
# ███████
#      ██
# ███████

@app.route('/savescore', methods = ['POST'])
def endpoint_savescore():
    loginResult = loginCheck(request.remote_addr)
    if loginResult:
        return loginResult
    else:
        try:
            game = request.args.get("game")
            score = request.args.get("score")
            if game and score:
                username = sD.studentDict[request.remote_addr]['name']
                db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
                dbcmd = db.cursor()
                dbcmd.execute("INSERT INTO scores (game, username, score) VALUES (?, ?, ?)", (game, username, score))
                db.commit()
                db.close()
                return render_template("message.html", message = "Score saved to database.")
            else:
                return render_template("message.html", message = "Missing arguments.")
        except Exception as e:
            print("[error] " + "Error: " + str(e))


@app.route('/say')
def endpoint_say():
    loginResult = loginCheck(request.remote_addr, 'bar')
    if loginResult:
        return loginResult
    else:
        sD.activePhrase = request.args.get('phrase')
        fgColor = request.args.get('fg')
        bgColor = request.args.get('bg')
        if sD.activePhrase:
            if hex2dec(fgColor) and hex2dec(bgColor):
                clearString()
                showString(sD.activePhrase, 0, hex2dec(fgColor), hex2dec(bgColor))
            else:
                clearString()
                showString(sD.activePhrase)
                if ONRPi:
                    pixels.show()
            return render_template("message.html", message = "Set phrase to: " + str(sD.activePhrase) + ".")
        else:
            return render_template("message.html", message = "<b>phrase</b> must contain a string. \'/say?phrase=<b>\'hello\'</b>\'", forward = '/home')

@app.route('/segment')
def endpoint_segment():
    if not ONRPi:
        global pixels
    loginResult = loginCheck(request.remote_addr, 'bar')
    if loginResult:
        return loginResult
    else:
        type = request.args.get('type')
        hex = request.args.get('hex')
        hex2 = request.args.get('hex2')
        start = request.args.get('start')
        end = request.args.get('end')
        if not hex:
            return render_template("message.html", message = "Bad ArgumentsTry <b>/segment?start=0&end=10&hex=FF00FF</b> (you need at least one color)")
        if not hex2dec(hex):
            return render_template("message.html", message = "Bad ArgumentsTry <b>/segment?start=0&end=10&hex=FF00FF</b> (you did not use a proper hexadecimal color)")
        if not start or not end:
            return render_template("message.html", message = "Bad ArgumentsTry <b>/segment?start=0&end=10&hex=FF00FF</b> (you need a start and end point)")
        else:
            try:
                start = int(start)
                end = int(end)
            except Exception as e:
                logFile("Error", e)
                return render_template("message.html", message = "Bad ArgumentsTry <b>/segment?start=0&end=10&hex=FF00FF</b> (start and end must be and integer)")
        if start > BARPIX or end > BARPIX:
            return render_template("message.html", message = "Bad ArgumentsTry <b>/segment?start=0&end=10&hex=FF00FF</b> (Your start or end was higher than the number of pixels: " + str(BARPIX) + ")")
        pixRange = range(start, end)
        if type == 'fadein':
            for i, pix in enumerate(pixRange):
                pixels[pix] = fadein(pixRange, i, hex2dec(hex))
        elif type == 'fadeout':
            for i, pix in enumerate(pixRange):
                pixels[pix] = fadeout(pixRange, i, hex2dec(hex))
        elif type == 'blend':
            if not hex:
                return render_template("message.html", message = "Bad ArgumentsTry <b>/segment?start=0&end=10&hex=FF00FF&hex2=#00FF00</b> (you need at least two colors)")
            if not hex2dec(hex):
                return render_template("message.html", message = "Bad ArgumentsTry <b>/segment?start=0&end=10&hex=FF00FF&hex2=#00FF00</b> (you did not use a proper hexadecimal color)")
            else:
                for i, pix in enumerate(pixRange):
                    pixels[pix] = blend(pixRange, i, hex2dec(hex), hex2dec(hex2))
        elif type == 'color':
                for i, pix in enumerate(pixRange):
                    pixels[pix] = hex2dec(hex)
        else:
            if hex2dec(hex):
                fillBar(hex2dec(hex))
            else:
                return render_template("message.html", message = "Bad ArgumentsTry <b>/color?hex=FF00FF</b> or <b>/color?r=255&g=0&b=255</b>")
        if ONRPi:
            pixels.show()
        return render_template("message.html", message = "Color sent!")

'''
@app.route('/sendblock')
def endpoint_sendblock():
    if not sD.settings['barmode'] == 'blockchest':
        return render_template("message.html", message = "Not in blockchest sD.settings['barmode']")
    blockId = request.args.get("id")
    blockData = request.args.get("data")
    if blockId and blockData:
        if blockId in colorDict:
            blockList.append([blockId, blockData])
            addBlock()
            #fillBlocks()
            return render_template("message.html", message = "Got Block: " + blockId + ", " + blockData)
        else:
            return render_template("message.html", message = "Bad block Id")
    else:
        return render_template("message.html", message = "Bad Arguments. Requires 'id' and 'data'")
'''

#Choose the user's default homepage
@app.route('/setdefault', methods = ['POST', 'GET'])
def endpoint_setdefault():
    loginResult = loginCheck(request.remote_addr)
    if loginResult:
        return loginResult
    else:
        if request.method == 'POST':
            if request.form['page'] == 'standard' or request.form['page'] == 'advanced' or request.form['page'] == 'quickpanel':
                sD.studentDict[request.remote_addr]['preferredHomepage'] = request.form['page']
                db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
                dbcmd = db.cursor()
                dbcmd.execute("UPDATE users SET preferredHomepage=:page WHERE username=:uname", {"uname": sD.studentDict[request.remote_addr]['name'], "page": request.form['page']})
                db.commit()
                db.close()
            else:
                return render_template("message.html", message = 'Invalid page.')
            return redirect('/')
        else:
            return render_template('setdefault.html', pm = sD.studentDict[request.remote_addr]['preferredHomepage'])

@app.route('/settings')
def endpoint_settings():
    if request.args.get('advanced'):
        advanced = '?advanced=true'
    else:
        advanced = ''
    return redirect('/controlpanel' + advanced)

#This endpoint leads to the Sound Effect page
@app.route('/sfx')
def endpoint_sfx():
    loginResult = loginCheck(request.remote_addr, 'sfx')
    if loginResult:
        return loginResult
    else:
        sfx.updateFiles()
        sfx_file = request.args.get('file')
        if sfx_file in sfx.sound:
            playSFX(sfx_file)
            return render_template("message.html", message = 'Playing: ' + sfx_file)
        else:
            resString = '<h2>List of available sound files:</h2><ul>'
            for key, value in sfx.sound.items():
                resString += '<li><a href="/sfx?file=' + key + '">' + key + '</a></li>'
            resString += '</ul> You can play them by using \'/sfx?file=<b>&lt;sound file name&gt;</b>\''
            return render_template("general.html", content = resString, style = '<style>ul {columns: 2; -webkit-columns: 2; -moz-columns: 2;}</style>')

@app.route('/socket')
def endpoint_socket():
    return render_template('socket.html', async_mode=socket_.async_mode)

@app.route('/speedtype')
def endpoint_speedtype():
    if request.args.get('advanced'):
        advanced = '?advanced=true'
    else:
        advanced = ''
    return redirect('/games/speedtype' + advanced)


@app.route('/standard')
def endpoint_standard():
    return redirect('/home')

#Start a poll
@app.route('/startpoll')
def endpoint_startpoll():
    loginResult = loginCheck(request.remote_addr, 'mod')
    if loginResult:
        return loginResult
    else:
        if not request.args.get('type'):
            return render_template("message.html", message = "You need a poll type.")
        type = request.args.get('type')
        if not (type == 'tutd' or type == 'abcd' or type == 'text'):
            return render_template("message.html", message = "Invalid poll type.")
        changeMode(type)
        repeatMode()
        sD.pollType = type
        return render_template("message.html", message = 'Started a new ' + type + ' poll.')

# ████████
#    ██
#    ██
#    ██
#    ██


@app.route('/td')
def endpoint_td():
    if request.args.get('advanced'):
        advanced = '?advanced=true'
    else:
        advanced = ''
    return redirect('/games/towerdefense' + advanced)

@app.route('/towerdefense')
def endpoint_towerdefense():
    if request.args.get('advanced'):
        advanced = '?advanced=true'
    else:
        advanced = ''
    return redirect('/games/towerdefense' + advanced)

@app.route('/ttt')
def endpoint_ttt():
    if request.args.get('advanced'):
        advanced = '?advanced=true'
    else:
        advanced = ''
    return redirect('/games/ttt' + advanced)

'''
    /tutd
    Thumbs-Up-Thumbs-Down page (Thumbspanel)
'''
@app.route('/tutd')
def endpoint_tutd():
    loginResult = loginCheck(request.remote_addr)
    if loginResult:
        return loginResult
    else:
        ip = request.remote_addr
        thumb = request.args.get('thumb')
        if thumb:
            if sD.settings['barmode'] == 'tutd':
                # This commented lines if made un-commented will allow for the host of the server to see who sent what reaction, along with their ip address. 
                #logFile("Info",  "Recieved " + thumb + " from " + name + " at ip: " + ip)
                if thumb in ['up', 'down', 'wiggle']:
                    if sD.studentDict[request.remote_addr]['thumb'] != thumb:
                        sD.studentDict[request.remote_addr]['thumb'] = thumb
                        tutdBar()
                        socket_.emit('thumb', {'name': sD.studentDict[request.remote_addr]['name'], 'thumb': thumb}, namespace=apinamespace)
                        return render_template("message.html", message = "Thank you for your tasty bytes... (" + thumb + ")")
                    else:
                        return render_template("message.html", message = "You've already submitted this answer... (" + thumb + ")")
                elif thumb == 'oops':
                    if sD.studentDict[request.remote_addr]['thumb']:
                        sD.studentDict[request.remote_addr]['thumb'] = ''
                        playSFX("sfx_hit01")
                        tutdBar()
                        socket_.emit('thumb', {'name': sD.studentDict[request.remote_addr]['name'], 'thumb': ''}, namespace=apinamespace)
                        return render_template("message.html", message = "I won\'t mention it if you don\'t")
                    else:
                        return render_template("message.html", message = "You don't have an answer to erase.")
                else:
                    return render_template("message.html", message = "Bad ArgumentsTry <b>/tutd?thumb=wiggle</b>You can also try <b>down</b> and <b>up</b> instead of <b>wiggle</b>")
            else:
                return render_template("message.html", message = "Not in TUTD mode.")
        else:
            return render_template("thumbsrental.html")

# ██    ██
# ██    ██
# ██    ██
# ██    ██
#  ██████

@app.route('/updateuser', methods = ['POST'])
def endpoint_updateuser():
    loginResult = loginCheck(request.remote_addr)
    if loginResult:
        return loginResult
    else:
        try:
            field = request.args.get("field")
            value = request.args.get("value")
            username = request.args.get("name") or sD.studentDict[request.remote_addr]['name']
            if field and value:
                db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
                dbcmd = db.cursor()
                dbcmd.execute("UPDATE users SET " + field + "=:value WHERE username=:uname", {"uname": username, "value": value})
                db.commit()
                db.close()
                return render_template("message.html", message = "Account updated.")
            else:
                return render_template("message.html", message = "Missing arguments.")
        except Exception as e:
            print("[error] " + "Error: " + str(e))

#This endpoint allows us to see which user(Student) is logged in.
@app.route('/users')
def endpoint_users():
    loginResult = loginCheck(request.remote_addr, 'users')
    if loginResult:
        return loginResult
    else:
        action = request.args.get('action')
        user = '';
        if request.args.get('name'):
            for key, value in sD.studentDict.items():
                if request.args.get('name') == sD.studentDict[key]['name']:
                    user = key
                    break
            if action == 'delete':
                db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
                dbcmd = db.cursor()
                dbcmd.execute("DELETE FROM users WHERE username=:uname", {"uname": request.args.get('name')})
                db.commit()
                db.close()
                if user in sD.studentDict:
                    del sD.studentDict[user]
                return render_template("message.html", message = "User deleted.")
            if action == 'changePw':
                password = request.args.get('password')
                if password:
                    passwordCrypt = cipher.encrypt(password.encode())
                    db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
                    dbcmd = db.cursor()
                    dbcmd.execute("UPDATE users SET password=:pw WHERE username=:uname", {"uname": request.args.get('name'), "pw": passwordCrypt})
                    db.commit()
                    db.close()
                    return render_template("message.html", message = "Password reset.")
                else:
                    return render_template("message.html", message = "New password reqired.")
            if not user:
                return render_template("message.html", message = "That user was not found by their name.")
        if request.args.get('ip'):
            if request.args.get('ip') in sD.studentDict:
                user = request.args.get('ip')
            else:
                return render_template("message.html", message = "That user was not found by their IP address.")
        if action == 'removeNP':
            if request.args.get('name') in newPasswords:
                del newPasswords[request.args.get('name')]
            else:
                return render_template("message.html", message = "That user was has not requested a new password.")
            if request.args.get('acceptNP'):
                if request.args.get('advanced'):
                    advanced = '&advanced=true'
                else:
                    advanced = ''
                return redirect('/users?action=changePw&name=' + request.args.get('name') + '&password=' + request.args.get('password') + '&advanced=' + advanced)
            else:
                return render_template("message.html", message = "Request rejected.")
        if user:
            if action == 'removeTicket':
                sD.studentDict[user]['help'] = {
                    'type': '',
                    'time': None,
                    'message': ''
                }
                if request.args.get('acceptBreak'):
                    sD.studentDict[student]['excluded'] = True
                    sD.studentDict[student]['oldPerms'] = sD.studentDict[student]['perms'] #Get the student's current permissions so they can be restored later
                    sD.studentDict[student]['perms'] = sD.settings['perms']['anyone']
                #Disabled until chat works
                    #server.send_message(sD.studentDict[student], json.dumps(packMSG('alert', name, 'server', 'The teacher accepted your break request.')))
                #elif sD.studentDict[student]['help']['type'] == 'break':
                    #server.send_message(sD.studentDict[student], json.dumps(packMSG('alert', name, 'server', 'The teacher rejected your break request.')))
            if action == 'kick':
                if user in sD.studentDict:
                    logFile("Info", sD.studentDict[request.remote_addr]['name'] + " was removed by the teacher.")
                    socket_.emit('alert', json.dumps(packMSG('all', 'server', sD.studentDict[request.remote_addr]['name'] + " was removed by the teacher...")), namespace=chatnamespace)
                    del sD.studentDict[user]
                    playSFX('sfx_laser01')
                    return render_template("message.html", message = "User removed")
                else:
                    return render_template("message.html", message = "User not in list.")
            if action == 'ban':
                if user in sD.studentDict:
                    banList.append(user)
                    del sD.studentDict[user]
                    return render_template("message.html", message = "User removed and added to ban list.")
                else:
                    return render_template("message.html", message = "User not in list.")
            if action == 'perm':
                if request.args.get('perm'):
                    try:
                        perm = int(request.args.get('perm'))
                        if user in sD.studentDict:
                            if perm > 4 or perm < 0 :
                                return render_template("message.html", message = "Permissions out of range.")
                            else:
                                sD.studentDict[user]['perms'] = perm
                                #Open and connect to database
                                db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
                                dbcmd = db.cursor()
                                dbcmd.execute("UPDATE users SET permissions=:perms WHERE username=:uname", {"uname": sD.studentDict[user]['name'], "perms": sD.studentDict[user]['perms']})
                                db.commit()
                                db.close()
                                logFile("Info", "Permissions Changed")
                                return render_template("message.html", message = "Changed user permission.")
                        else:
                            return render_template("message.html", message = "User not in list.")
                    except Exception as e:
                        logFile("Error", e)
                        f = open('errorlog.txt', 'a')
                        f.write(str(e))
                        f.close()
                        return render_template("message.html", message = "Perm was not an integer.")
            if request.args.get('refresh'):
                refresh = request.args.get('refresh')
                if refresh == 'all':
                    if refreshUsers(user):
                        return render_template("message.html", message = "Removed all student essays.")
                    else:
                        return render_template("message.html", message = "Error removing essays from all students.")
                else:
                    if refreshUsers(user, refresh):
                        return render_template("message.html", message = "Removed " + refresh + " essays from " + user + ".")
                    else:
                        return render_template("message.html", message = "Error removing " + refresh + " essays from " + user + ".")
            else:
                return render_template("message.html", message = "No action given.")
        else:
            db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
            dbcmd = db.cursor()
            users = dbcmd.execute("SELECT * FROM users").fetchall()
            db.close()
            return render_template("users.html", users = users)

@app.route('/usermanual')
def endpoint_usermanual():
     return render_template("usermanual.html")


# ██    ██
# ██    ██
# ██    ██
#  ██  ██
#   ████


#This endpoint allows you to see the formbars IP with style and shows different colors.
@app.route('/virtualbar')
def endpoint_virtualbar():
    return render_template("virtualbar.html")

# ██     ██
# ██     ██
# ██  █  ██
# ██ ███ ██
#  ███ ███


#This will take the student to the current "What are we doing?" link
@app.route('/wawd')
def endpoint_wawd():
    content = ''
    if sD.activePrompt:
        content = '<h2>'
        if sD.lesson.steps[sD.currentStep]['Type']:
            content += '<b>'+sD.lesson.steps[sD.currentStep]['Type'] + ': </b>'
        content += '<i>' + sD.activePrompt+'</i></h2>'
    if sD.wawdLink:
        if sD.wawdLink[0] == "/":
            content += '<a href="' + str(sD.wawdLink) + '">Go to page</a>'
        else:
            content += '<h2>External Resource</h2><a href="' + str(sD.wawdLink) + '">' + str(sD.wawdLink) + '</a>'
    if not content:
        content = 'There is no active lesson right now.'
    return render_template('general.html', content = content)

@app.route('/wordle')
def endpoint_wordle():
    if request.args.get('advanced'):
        advanced = '?advanced=true'
    else:
        advanced = ''
    return redirect('/games/wordle' + advanced)


# ███████  ██████   ██████ ██   ██ ███████ ████████ ████████  ██████
# ██      ██    ██ ██      ██  ██  ██         ██       ██    ██    ██
# ███████ ██    ██ ██      █████   █████      ██       ██    ██    ██
#      ██ ██    ██ ██      ██  ██  ██         ██       ██    ██    ██
# ███████  ██████   ██████ ██   ██ ███████    ██ ██ ████████  ██████

'''
    A message to or from the server should be a stringified JSON object:
    {
        type: <alert|userlist|help|message|fighter>,
        to: <*username*|server|all>,
        from: <*username*|server>,
        content: <message>
    }

'''

def packMSG(rx, tx, content, now = int(time.time() * 1000)):
    msgOUT = {
        "to": rx,
        "from": tx,
        "content": content,
        "time": now
    }
    return msgOUT

@socket_.on('connect', namespace=chatnamespace)
def connect():
    try:
        if request.remote_addr in sD.studentDict:
            sD.studentDict[request.remote_addr]['sid'] = request.sid
            logFile("Info", sD.studentDict[request.remote_addr]['name'] + " connected and was given id \"" + request.sid + "\"")
            emit('userlist', json.dumps(packMSG('all', 'server', chatUsers())), broadcast=True)
    except Exception as e:
        logFile("Error", "Error finding user in list: " + str(e))


@socket_.on('disconnect', namespace=chatnamespace)
def disconnect():
    try:
        if request.remote_addr in sD.studentDict:
            if 'sid' in sD.studentDict[request.remote_addr]:
                del sD.studentDict[request.remote_addr]['sid']
                logFile("Info", sD.studentDict[request.remote_addr]['name'] + " disconnected")
                emit('userlist', json.dumps(packMSG('all', 'server', chatUsers())), broadcast=True)
    except Exception as e:
        logFile("Error", "Error finding user in list: " + str(e))
        f = open('errorlog.txt', 'a')
        f.write(str(e))
        f.close()


@socket_.on('message', namespace=chatnamespace)
def message(message):
    try:
        #Check for permissions
        if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['say']:
            messageOut = packMSG('alert', sD.studentDict[client['address'][0]]['name'], 'server', "You do not have permission to send text messages.")
            server.send_message(client, json.dumps(messageOut))
        else:
            now = int(time.time() * 1000)
            message = json.loads(message)
            #Checking max message length here
            if len(message['content']) > 252:
                message['content'] = message['content'][:252]+'...'
            #Save the message to the database
            db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
            dbcmd = db.cursor()
            content = message['content'].replace('"', '\\"')
            contentCrypt = cipher.encrypt(content.encode())
            dbcmd.execute("INSERT INTO messages ('from', 'to', 'time', 'content') VALUES (?, ?, ?, ?)", (message['from'], message['to'], now, contentCrypt))
            db.commit()
            db.close()
            #Check recipients here
            if message['to'] == 'all':
                messageOut = packMSG('all', message['from'], message['content'], now)
                #messageOut = packMSG('all', sD.studentDict[client['address'][0]]['name'], message['content'])
                emit('message', json.dumps(messageOut), broadcast=True)
            else:
                for student in sD.studentDict:
                    if sD.studentDict[student]['name'] == message['to'] or sD.studentDict[student]['name'] == message['from']:
                        messageOut = packMSG(message['to'], message['from'], message['content'], now)
                        logFile("Chat", messageOut)
                        emit('message', json.dumps(messageOut), to=sD.studentDict[student]['sid'])
                        break
            logFile("Info", message['from'] + " said to " + message['to'] + ": " + message['content'])
    except Exception as e:
        logFile("Error", str(e))


@socket_.on('edit', namespace=chatnamespace)
def edit(timeSent, newContent):
    try:
        db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
        dbcmd = db.cursor()
        content = newContent
        if len(content) > 252:
            content = content[:252]+'...'
        content = content.replace('"', '\\"')
        contentCrypt = cipher.encrypt(content.encode())
        dbcmd.execute("UPDATE messages SET content=:content WHERE time=" + str(timeSent), {"content": contentCrypt})
        dbcmd.execute("UPDATE messages SET edited=1 WHERE time=" + str(timeSent))
        db.commit()
        db.close()
        emit('edit', [timeSent, newContent], broadcast=True)
    except Exception as e:
        logFile("Error", str(e))


@socket_.on('delete', namespace=chatnamespace)
def delete(timeSent):
    try:
        db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + '/data/database.db')
        dbcmd = db.cursor()
        content = 'Message deleted'
        contentCrypt = cipher.encrypt(content.encode())
        dbcmd.execute("UPDATE messages SET content=:content WHERE time=" + str(timeSent), {"content": contentCrypt})
        dbcmd.execute("UPDATE messages SET deleted=1 WHERE time=" + str(timeSent))
        db.commit()
        db.close()
        emit('delete', timeSent, broadcast=True)
    except Exception as e:
        logFile("Error", str(e))


@socket_.on('userlist', namespace=chatnamespace)
def message(message):
    try:
        emit('userlist', json.dumps(packMSG('userlist', sD.studentDict[request.remote_addr]['name'], 'server', chatUsers())), broadcast=True)
    except Exception as e:
        logFile("Error", str(e))


@socket_.on('reload', namespace=chatnamespace)
def message(message):
    try:
        emit('reload', message, broadcast=True)
    except Exception as e:
        print("[error] " + 'Error: ' + str(e))

@socket_.on('alert', namespace=chatnamespace)
def message(message):
    try:
        emit('alert', client, json.dumps(packMSG('alert', sD.studentDict[request.remote_addr]['name'], 'server', 'Only the server can send alerts!')))
    except Exception as e:
        logFile("Error", str(e))
        
        
        


@socket_.on('help', namespace=chatnamespace)
def message(message):
    try:
        #Update or remove
        pass
        #message = json.loads(message)
        #name = sD.studentDict[request.remote_addr]['name']
        #name = name.replace(" ", "")
        #helpList[name] = message['content']
        #playSFX("sfx_up04")
        #emit('help', json.dumps(packMSG('alert', sD.studentDict[request.remote_addr]['name'], 'server', 'Your help ticket was sent. Keep working on the problem while you wait!')))
    except Exception as e:
        logFile("Error", str(e))

@socket_.on('fighter', namespace=chatnamespace)
def fighter(message):
    try:
        emit('fighter', message, broadcast=True)
    except Exception as e:
        logFile("Error", str(e))
        
        
        


@socket_.on('ttt', namespace=chatnamespace)
def ttt(message):
    try:
        emit('ttt', message, broadcast=True)
        message = json.loads(message)
        for game in sD.ttt:
            #If the user and the opponent is in an existing player list
            if message['from'] in game.players and message['to'] in game.players:
                square = message['content']['square']
                rBox = math.floor(square / 3);
                cBox = square % 3;
                if game.turn == 1:
                    game.turn = 2
                else:
                    game.turn = 1
                if message['from'] == game.players[0]:
                    shape = 'X'
                else:
                    shape = 'O'
                game.gameboard[rBox][cBox] = shape
    except Exception as e:
        logFile("Error", str(e))



# ███████ ██ ███    ██  █████  ██          ██████   ██████   ██████  ████████
# ██      ██ ████   ██ ██   ██ ██          ██   ██ ██    ██ ██    ██    ██
# █████   ██ ██ ██  ██ ███████ ██          ██████  ██    ██ ██    ██    ██
# ██      ██ ██  ██ ██ ██   ██ ██          ██   ██ ██    ██ ██    ██    ██
# ██      ██ ██   ████ ██   ██ ███████     ██████   ██████   ██████     ██


#Startup stuff
sD.activePhrase = sD.ip
showString(sD.activePhrase)
if ONRPi:
    pixels.show()
if '--silent' not in str(sys.argv):
    playSFX("sfx_bootup02")

def start_flask():
    global DEBUG
    app.run(host='0.0.0.0', port=420, use_reloader=False, debug=DEBUG)

def start_IR():
    while True:
        ir.inData = ir.convertHex(ir.getBinary()) #Runs subs to get incomming hex value
        for button in range(len(ir.Buttons)):#Runs through every value in list
            if hex(ir.Buttons[button]) == ir.inData: #Checks this against incomming
                # print(ir.ButtonsNames[button]) #Prints corresponding english name for button
                if ir.ButtonsNames[button] == 'power':
                    flushUsers()
                elif ir.ButtonsNames[button] == 'func':
                    changeMode()
                elif ir.ButtonsNames[button] == 'repeat':
                    repeatMode()
                elif ir.ButtonsNames[button] == 'rewind':
                    rewindBGM()
                elif ir.ButtonsNames[button] == 'play_pause':
                    playpauseBGM()
                elif ir.ButtonsNames[button] == 'eq':
                    playSFX("sfx_up03")
                elif ir.ButtonsNames[button] == 'vol_up':
                    volBGM('up')
                elif ir.ButtonsNames[button] == 'vol_down':
                    volBGM('down')
                elif ir.ButtonsNames[button] == 'up':
                    sD.currentStep += 1
                    if sD.currentStep >= len(sD.lesson.steps):
                        sD.currentStep = len(sD.lesson.steps) - 1
                    playSFX("sfx_pickup01")
                elif ir.ButtonsNames[button] == 'down':
                    sD.currentStep -= 1
                    if sD.currentStep <= 0:
                        sD.currentStep = 0
                    playSFX("sfx_pickup01")

if __name__ == '__main__':
    #irApp = threading.Thread(target=start_IR, daemon=True)
    #irApp.start()#Starts up the chat feature
    # flaskApp = threading.Thread(target=start_flask)
    # flaskApp.start()
    # flaskApp.join()
    start_flask()
    socket_.run(app, debug=DEBUG)
