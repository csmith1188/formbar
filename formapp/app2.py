#Importing external modules
from flask import Flask, redirect, url_for, request, render_template
from werkzeug.utils import secure_filename
from websocket_server import WebsocketServer
import board, neopixel
import pandas, json, csv
import pygame
import time, math
import threading
import netifaces as ni
import logging
import traceback
import random, sys, os

'''
# Complex logging here
logging.basicConfig(filename='info.log',
                            filemode='a',
                            format='%(asctime)s.%(msecs)d %(levelname)s %(message)s',
                            datefmt='%H:%M:%S',
                            level=logging.DEBUG)

# set up logging to console
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
# set a format which is simpler for console use
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
console.setFormatter(formatter)
# add the handler to the root logger
logging.getLogger('').addHandler(console)
logger = logging.getLogger(__name__)
'''
# Change the built-in logging for flask
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

#Get internal IP address
#for wireless connections:
#ip = ni.ifaddresses('wlan0')[ni.AF_INET][0]['addr']
#for wired connections
ip = ni.ifaddresses('eth0')[ni.AF_INET][0]['addr']

#Set the websocket port for chat and live actions
WSPORT=9001

#Display IP address to console for user connection
logging.info('Running formbar server on:' + ip)

#Enable/Disable basic debugging w/o logging
DEBUG = True

#Importing customs modules
import letters
import sfx
import bgm
from colors import colors, hex2dec
import lessons
import sessions
import ir

#Set the maximum number of pixels on the bar
BARPIX = 300
#Set the maximum number of pixels, including pixelpanels
MAXPIX = 812

#Scan the sfx and bgm folders
sfx.updateFiles()
bgm.updateFiles()
#Start up pygame for sfx and bgm
pygame.init()

#Start the neopixel tracker
pixels = neopixel.NeoPixel(board.D21, MAXPIX, brightness=1.0, auto_write=False)

#Start a new flask server for http service
app = Flask(__name__)

sD = sessions.Session(ip)

# Dictionary words for hangman game
words = json.loads(open('data/words.json').read())

#Permission levels are as follows:
# 0 - teacher
# 1 - mod
# 2 - student
# 3 - anyone
# 4 - banned

banList = []
helpList = {}
blockList = []
colorDict = {
        '14': (255, 255, 0),
        '15': (196, 150, 128),
        '16': (255, 96, 0),
        '56': (0, 192, 192),
        }

'''
#For testing potential animation features
def aniTest():
    fillBar((0,0,0))
    for i in range(0, BARPIX - 40):
        pixRange = range(i+20, i + 40)
        pixRange2 = range(i, i + 20)
        for j, pix in enumerate(pixRange):
            pixels[pix] = blend(pixRange, j, colors['blue'], colors['red'])
        for j, pix in enumerate(pixRange2):
            pixels[pix] = blend(pixRange2, j, colors['green'], colors['blue'])
        pixels.show()

@app.route('/anitest')
def endpoint_anitest():
    if len(threading.enumerate()) < 5:
        threading.Thread(target=aniTest, daemon=True).start()
        return 'testing...'
    else:
        return 'Too many threads'
'''

def dbug(message='Checkpoint Reached'):
    global DEBUG
    if DEBUG:
        print("[DEBUG] " + str(message))

def newStudent(remote, username, pin=''):
    if not remote in sD.studentDict:
        sD.studentDict[remote] = {
            'name': username,
            'thumb': '',
            'survey': '',
            'perms': 2,
            'progress': [],
            'complete': False,
            'tttGames': [],
            'quizRes': [],
            'essayRes': ''
        }
        if len(sD.studentDict) - 1:
            logging.info("New user logged in. Made them a student: " + username)
            sD.studentDict[remote]['perms'] = 2
        else:
            logging.info("First user logged in. Made them a Teacher: " + username)
            sD.studentDict[remote]['perms'] = 0
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
                logging.error(e)
                return False
        else:
            sD.studentDict[student]['thumb'] = '',
            sD.studentDict[student]['survey'] = '',
            sD.studentDict[student]['progress'] = [],
            sD.studentDict[student]['complete'] = False,
            sD.studentDict[student]['quizRes'] = [],
            sD.studentDict[student]['essayRes'] = ''
            return True

def changeMode(newMode='', direction='next'):
    playSFX("sfx_pickup01")
    index = sD.settings['modes'].index(sD.settings['barmode'])
    if newMode in sD.settings['modes']:
        sD.settings['barmode'] = newMode
    else:
        if direction == 'next':
            index += 1
        elif direction == 'prev':
            index -= 1
        else:
            logging.warning('Invalid direction. Needs next or prev.')
        if index >= len(sD.settings['modes']):
            index = 0
        elif index < 0:
            index =len(sD.settings['modes']) - 1
        sD.settings['barmode'] = sD.settings['modes'][index]
    if sD.settings['barmode'] == 'tutd':
        tutdBar()
    elif sD.settings['barmode'] == 'survey':
        surveyBar()
    elif sD.settings['barmode'] == 'essay' or sD.settings['barmode'] == 'quiz':
        completeBar()
    elif sD.settings['barmode'] == 'progress':
        if sD.lesson:
            percFill(sD.lesson.checkProg(stripUser('admin')))
    elif sD.settings['barmode'] == 'playtime':
        clearString()
        showString(sD.activePhrase)

#This function Allows you to choose and play whatever sound effect you want
def playSFX(sound):
    try:
        pygame.mixer.Sound(sfx.sound[sound]).play()
        return "Succesfully played: "
    except:
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

def volBGM(direction):
    sD.bgm['volume'] = pygame.mixer.music.get_volume()
    if direction == 'up':
        sD.bgm['volume'] += 0.1
    elif direction == 'down':
        sD.bgm['volume'] -= 0.1
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
    if blockList[-1][0] in colorDict:
        pixels[len(blockList)-1] = colorDict[blockList[-1][0]]
    else:
        pixels[len(blockList)-1] = colors['default']
    pixels.show()

def fillBlocks():
    for i, block in enumerate(blockList):
        if block[0] in colorDict:
            pixels[i] = colorDict[block[0]]
        else:
            pixels[i] = colors['default']
    pixels.show()

def percFill(amount, fillColor=colors['green'], emptyColor=colors['red']):
    if amount > 100 and amount < 0 and type(amount) is not int:
        raise TypeError("Out of range. Must be between 0 - 1 or 0 - 100.")
    else:
        pixRange = math.ceil(BARPIX * (amount * 0.01))
        for pix in range(0, BARPIX):
            if pix <= pixRange:
                pixels[pix] = fillColor
            else:
                pixels[pix] = emptyColor
        pixels.show()
    if sD.settings['captions']:
        clearString()
        showString("PROG " + str(sD.lesson.checkProg(stripUser('admin'))))
    pixels.show()

def fillBar(color=colors['default'], stop=BARPIX, start=0):
    #If you provide no args, the whole bar is made the default color
    #If you provide one arg, the whole bar will be that color
    #If you provide two args, the bar will be that color until the stop point
    #If you provide three args, pixels between the stop and start points will be that color
    for pix in range(start, stop):
        pixels[pix] = color

def repeatMode():
    if sD.settings['barmode'] == 'tutd':
        # Clear thumbs
        for student in sD.studentDict:
            sD.studentDict[student]['thumb'] = ''
        tutdBar()
    elif sD.settings['barmode'] == 'survey':
        # Clear thumbs
        for student in sD.studentDict:
            sD.studentDict[student]['survey'] = ''
        surveyBar()
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

#This function clears(default) the color from the formbar
def clearBar():
    #fill with default color to clear bar
    for pix in range(0, BARPIX):
        pixels[pix] = colors['default']

def clearString():
    for i in range(BARPIX, MAXPIX):
        pixels[i] = colors['bg']

def showString(toShow, startLocation=0, fg=colors['fg'], bg=colors['bg']):
    for i, letter in enumerate(toShow.lower()):
        printLetter(letter, (i * (8 * 6)) + ((startLocation * 48) + BARPIX), fg, bg)
    pixels.show()

def printLetter(letter, startLocation, fg=colors['fg'], bg=colors['bg']):
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
            logging.warning("Warning! Letter ", letter, " not found.")
    else:
        logging.warning("Warning! Not enough space for this letter!")

#Shows results of test when done with surveyBar
def surveyBar():
    results = [] # Create empty results list
    clearBar()
    #Go through IP list and see what each IP sent as a response
    for student in sD.studentDict:
        #if the survey answer is a valid a, b, c, or d:
        if sD.studentDict[student]['survey'] in ['a', 'b', 'c', 'd']:
            #add this result to the results list
            results.append(sD.studentDict[student]['survey'])
    #The number of results is how many have complete the survey
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
        showString("SRVY " + str(complete) + "/" + str(sD.settings['numStudents']))
    pixels.show()

#it takes the students picked answer and puts the required color for that specific choice
def tutdBar():
    if sD.settings['autocount']:
        autoStudentCount()
    upFill = upCount = downFill = wiggleFill = 0
    complete = 0
    for x in sD.studentDict:
        if sD.studentDict[x]['thumb']:
            if sD.studentDict[x]['thumb'] == 'up':
                upFill += 1
                upCount += 1
            elif sD.studentDict[x]['thumb'] == 'down':
                downFill += 1
            elif sD.studentDict[x]['thumb'] == 'wiggle':
                wiggleFill += 1
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
        pixels.show()
    if upCount >= sD.settings['numStudents']:
        pixels.fill((0,0,0))
        playSFX("sfx_success01")
        for i, pix in enumerate(range(0, BARPIX)):
                pixels[pix] = blend(range(0, BARPIX), i, colors['blue'], colors['red'])
        if sD.settings['captions']:
            clearString()
            showString("MAX GAMER!", 0, colors['purple'])
    #The Funny Number
    if sD.settings['numStudents'] == 9 and complete == 6:
        playSFX("clicknice")
    else:
        playSFX("sfx_blip01")
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
        if 'wsID' in sD.studentDict[student].keys():
            newList[student] = {}
            newList[student]['name'] = sD.studentDict[student]['name']
            newList[student]['perms'] = sD.studentDict[student]['perms']
            newList[student]['wsID'] = sD.studentDict[student]['wsID']
    return newList

def updateStep():
    step = sD.lesson.steps[sD.currentStep]
    if step['Type'] == 'Resource':
        sD.wawdLink = sD.lesson.links[int(step['Prompt'])]['URL']
    elif step['Type'] == 'TUTD':
        sD.settings['barmode'] = 'tutd'
        sD.activePrompt = step['Prompt']
        sD.wawdLink = '/tutd'
    elif step['Type'] == 'Essay':
        sD.settings['barmode'] = 'essay'
        sD.activePrompt = step['Prompt']
        sD.wawdLink = '/essay'
    elif step['Type'] == 'Survey':
        sD.settings['barmode'] = 'survey'
        sD.activeQuiz = sD.lesson.quizList[step['Prompt']]
        surveyIndex = int(sD.activeQuiz['name'].split(' ', 1))
        sD.activePrompt = sD.activeQuiz['questions'][surveyIndex]
        sD.wawdLink = '/survey'
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

#Default formbar(Main page)
@app.route('/')
def endpoint_home():
    return render_template('index.html')

#Default formbar in advanced expert mode
@app.route('/expert')
def endpoint_expert():
    if sD.studentDict:
        username = sD.studentDict[request.remote_addr]['name']
    else:
        username = ''
    sfx.updateFiles()
    sounds = []
    music = []
    for key, value in sfx.sound.items():
        sounds.append(key)
    for key, value in bgm.bgm.items():
        music.append(key)
    return render_template('expert.html', username = username, serverIp = ip, sfx = sounds, bgm = music)

@app.route('/debug')
def endpoint_debug():
    return render_template('debug.html')

@app.route('/fighter')
def endpoint_fighter():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['games']:
        return render_template("message.html", message = "You do not have high enough permissions to do this right now. " )
    else:
        #return render_template('fighter.html', username = sD.studentDict[request.remote_addr]['name'], serverIp = ip)
        return render_template("message.html", forward=request.path, message = "Fighter will be ready to play soon.")

#Before choosing endpoints you are required to log in
@app.route('/login', methods = ['POST', 'GET'])
def endpoint_login():
    remote = request.remote_addr
    if remote in banList:
        return "This IP is in the banlist."
    else:
        if request.method == 'POST':
            username = request.form['username']
            forward = request.form['forward']
            #pin = request.form['pin']
            print(remote)
            if username.strip() and remote == '127.0.0.1':
                newStudent(remote, username)
                sD.studentDict[remote]['perms'] = sD.settings['perms']['admin']
                return "success"
            elif username.strip():
                newStudent(remote, username)
                if forward:
                    return redirect(forward, code=302)
                else:
                    return redirect('/', code=302)
            else:
                return render_template("message.html", forward=forward, message="You cannot have a blank name.")
        elif request.args.get('name'):
            newStudent(remote, request.args.get('name'))
            return redirect('/', code=302)
        else:
            return render_template("login.html")

'''
Change the color of the entire bar
Query Parameters:
    hex = six hexadecimal digit rgb color (prioritizes over RGB)
    r, g, b = provide three color values between 0 and 255
'''
@app.route('/color')
def endpoint_color():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    elif sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['bar']:
        return render_template("message.html", message = "You do not have high enough permissions to do this right now. " )
    else:
        try:
            r = int(request.args.get('r'))
            g = int(request.args.get('g'))
            b = int(request.args.get('b'))
        except:
            r = ''
            g = ''
            b = ''
        hex = request.args.get('hex')
        if hex2dec(hex):
            fillBar(hex2dec(hex))
        elif r and b and g:
            fillBar((r, g, b))
        else:
            return "Bad ArgumentsTry <b>/color?hex=#FF00FF</b> or <b>/color?r=255&g=0&b=255</b>"
        pixels.show()
        return render_template("message.html", message = "Color sent!" )

@app.route('/segment')
def endpoint_segment():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    elif sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['bar']:
        return render_template("message.html", message = "You do not have high enough permissions to do this right now. " )
    else:
        type = request.args.get('type')
        hex = request.args.get('hex')
        hex2 = request.args.get('hex2')
        start = request.args.get('start')
        end = request.args.get('end')
        if not hex:
            return "Bad ArgumentsTry <b>/segment?start=0&end=10&hex=#FF00FF</b> (you need at least one color)"
        if not hex2dec(hex):
            return "Bad ArgumentsTry <b>/segment?start=0&end=10&hex=#FF00FF</b> (you did not use a proper hexadecimal color)"
        if not start or not end:
            return "Bad ArgumentsTry <b>/segment?start=0&end=10&hex=#FF00FF</b> (you need a start and end point)"
        else:
            try:
                start = int(start)
                end = int(end)
            except:
                return "Bad ArgumentsTry <b>/segment?start=0&end=10&hex=#FF00FF</b> (start and end must be and integer)"
        if start > BARPIX or end > BARPIX:
            return "Bad ArgumentsTry <b>/segment?start=0&end=10&hex=#FF00FF</b> (Your start or end was higher than the number of pixels: " + str(BARPIX) + ")"
        pixRange = range(start, end)
        if type == 'fadein':
            for i, pix in enumerate(pixRange):
                pixels[pix] = fadein(pixRange, i, hex2dec(hex))
        elif type == 'fadeout':
            for i, pix in enumerate(pixRange):
                pixels[pix] = fadeout(pixRange, i, hex2dec(hex))
        elif type == 'blend':
            if not hex:
                return "Bad ArgumentsTry <b>/segment?start=0&end=10&hex=#FF00FF&hex2=#00FF00</b> (you need at least two colors)"
            if not hex2dec(hex):
                return "Bad ArgumentsTry <b>/segment?start=0&end=10&hex=#FF00FF&hex2=#00FF00</b> (you did not use a proper hexadecimal color)"
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
                return "Bad ArgumentsTry <b>/color?hex=#FF00FF</b> or <b>/color?r=255&g=0&b=255</b>"
        pixels.show()
        return render_template("message.html", message = "Color sent!" )

#This will take the student to the current "What are we doing?" link
@app.route('/wawd')
def endpoint_wawd():
    if sD.wawdLink[0] == "/":
        return redirect(sD.wawdLink)
    else:
        return render_template('general.html', content='<h2>External Resource</h2><a href="' +str(sD.wawdLink) + '">' + str(sD.wawdLink) + '</a>')

#This will take the student to the current "What are we doing?" link
@app.route('/lesson', methods = ['POST', 'GET'])
def endpoint_lesson():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    elif sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['bar']:
        return render_template("message.html", forward=request.path, message = "You do not have high enough permissions to do this right now. " )
    else:
        if request.method == 'POST':
            if not request.files['file']:
                return render_template('message.html', message='Lesson file required.')
            else:
                f = request.files['file']
                f.save(os.path.join('lessondata', secure_filename(f.filename.strip(' '))))
                return redirect('/lesson')
        elif request.args.get('load'):
            try:
                sD.refresh()
                sD.lessonList = lessons.updateFiles()
                sD.lesson = lessons.readBook(request.args.get('load'))
                return redirect('/lesson')
            except Exception as e:
                print(traceback.format_exc())
                logging.error(e)
                return render_template('message.html', message='<b>Error:</b> ' + str(e))
        elif request.args.get('action'):
            if request.args.get('action') == 'next':
                sD.currentStep += 1
                if sD.currentStep >= len(sD.lesson.steps):
                    sD.currentStep = len(sD.lesson.steps)
                    return render_template('message.html', message='End of lesson!')
                else:
                    updateStep()
                    return redirect('/lesson')
            elif request.args.get('action') == 'prev':
                sD.currentStep -= 1
                if sD.currentStep <= 0:
                    sD.currentStep = 0
                    return render_template('message.html', message='Already at start of lesson!')
                else:
                    updateStep()
                    return redirect('/lesson')
            elif request.args.get('action') == 'unload':
                sD.refresh()
                return render_template('message.html', message='Unloaded lesson.')
            elif request.args.get('action') == 'upload':
                return render_template('general.html', content='<form method=post enctype=multipart/form-data><input type=file name=file accept=".xlsx"><input type=submit value=Upload></form>')
            else:
                return redirect('/lesson')
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

#This endpoint is exclusive only to the teacher.
@app.route('/progress', methods = ['POST', 'GET'])
def endpoint_progress():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    #el if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['bar']:
    #     return render_template("message.html", forward=request.path, message = "You do not have high enough permissions to do this right now. " )
    # else:
    if request.args.get('check'):
        try:
            check = int(request.args.get('check'))
            sD.studentDict[request.remote_addr]['progress'][check] = not sD.studentDict[request.remote_addr]['progress'][check]
            percAmount = sD.lesson.checkProg(sD.studentDict)
            if sD.settings['barmode'] == 'progress':
                percFill(percAmount)
            return render_template('message.html', message=str(check) + " was toggled.")
        except Exception as e:
            logger.error(e)
            return render_template('message.html', message='<b>Error:</b> ' + str(e))
    else:
        if sD.activeProgress:
            return render_template('progress.html', progress=sD.activeProgress)
        else:
            return render_template('message.html', message='There is no progress tracker active right now.')

#This endpoint is exclusive only to the teacher.
@app.route('/settings', methods = ['POST', 'GET'])
def endpoint_settings():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['admin']:
        return render_template("message.html", forward=request.path, message = "You do not have high enough permissions to do this right now. " )
    else:
        if request.method == 'POST':
            repeatMode()
            return redirect('/settings')
        else:
            resString = ''
            #Loop through every arg that was sent as a query parameter
            for arg in request.args:
                #See if you save the
                argVal = str2bool(request.args.get(arg))
                #if the argVal resolved to a boolean value
                if isinstance(argVal, bool):
                    if arg in sD.settings:
                        sD.settings[arg] = argVal
                        resString += 'Set <i>' + arg + '</i> to: <i>' + str(argVal) + "</i>"
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
                    except:
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
                return render_template("settings.html")
            else:
                playSFX("sfx_pickup01")
                resString += ""
                return resString

@app.route('/flush')
def endpoint_flush():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['admin']:
        return render_template("message.html", message = "You do not have high enough permissions to do this right now. " )
    else:
        flushUsers()
        sD.refresh()
        return render_template("message.html", message = "Session was restarted." )

#takes you to a quiz(literally)
@app.route('/quiz', methods = ['POST', 'GET'])
def endpoint_quiz():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['student']:
        return render_template("message.html", forward=request.path, message = "You do not have high enough permissions to do this right now. " )
    else:
        if request.method == 'POST':
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
            return render_template('message.html', message='No quiz is currently loaded.')

#This endpoint allows the teacher to test students.
@app.route('/survey')
def endpoint_survey():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['student']:
        return render_template("message.html", forward=request.path, message = "You do not have high enough permissions to do this right now. " )
    else:
        ip = request.remote_addr
        vote = request.args.get('vote')
        if vote:
            if vote in ["a", "b", "c", "d"]:
                if sD.studentDict[request.remote_addr]['survey'] != vote:
                    sD.studentDict[request.remote_addr]['survey'] = vote
                    playSFX("sfx_blip01")
                    surveyBar()
                    return render_template("message.html", forward=request.path, message = "Thank you for your tasty bytes... (" + vote + ")" )
                else:
                    return render_template("message.html", forward=request.path, message = "You've already sunmitted an answer... (" + sD.studentDict[request.remote_addr]['survey'] + ")" )
            elif vote == 'oops':
                if sD.studentDict[request.remote_addr]['survey']:
                    sD.studentDict[request.remote_addr]['survey'] = ''
                    playSFX("sfx_hit01")
                    surveyBar()
                    return render_template("message.html", forward=request.path, message = "I won\'t mention it if you don\'t" )
                else:
                    return render_template("message.html", forward=request.path, message = "You don't have an answer to erase." )
            else:
                return render_template("message.html", forward=request.path, message = "Bad arguments..." )
        else:
            return render_template("thumbsrental.html")

#It takes you to the thumbs panel for voting
@app.route('/tutd')
def endpoint_tutd():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    else:
        ip = request.remote_addr
        thumb = request.args.get('thumb')
        if thumb:
            # logging.info("Recieved " + thumb + " from " + name + " at ip: " + ip)
            if thumb == 'up' or thumb == 'down' or thumb == 'wiggle' :
                if sD.studentDict[request.remote_addr]['thumb'] != thumb:
                    sD.studentDict[request.remote_addr]['thumb'] = thumb
                    tutdBar()
                    return render_template("message.html", forward=request.path, message = "Thank you for your tasty bytes... (" + thumb + ")" )
                else:
                    return render_template("message.html", forward=request.path, message = "You've already sunmitted this answer... (" + thumb + ")" )
            elif thumb == 'oops':
                if sD.studentDict[request.remote_addr]['thumb']:
                    sD.studentDict[request.remote_addr]['thumb'] = ''
                    playSFX("sfx_hit01")
                    tutdBar()
                    return render_template("message.html", forward=request.path, message = "I won\'t mention it if you don\'t" )
                else:
                    return render_template("message.html", forward=request.path, message = "You don't have an answer to erase." )
            else:
                return render_template("message.html", forward=request.path, message = "Bad ArgumentsTry <b>/tutd?thumb=wiggle</b>You can also try <b>down</b> and <b>up</b> instead of <b>wiggle</b>")
        else:
            if sD.activePrompt:
                prompt = '<h2>'
                if sD.lesson.steps[sD.currentStep]['Type']:
                    prompt += '<b>'+sD.lesson.steps[sD.currentStep]['Type'] + ': </b>'
                prompt += '<i>' + sD.activePrompt+'</i></h2>'
            else:
                prompt = ''
            return render_template("thumbsrental.html", prompt=prompt)

#This endpoint lets you switch the sD.settings for the formbar(exclusive for teacher)
@app.route('/help', methods = ['POST', 'GET'])
def endpoint_help():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    if request.method == 'POST':
        name = sD.studentDict[request.remote_addr]['name']
        name = name.replace(" ", "")
        if name in helpList:
            return render_template("message.html", forward=request.path, message = "You already have a help ticket in. If your problem is time-sensitive, or your last ticket was not cleared, please get the teacher's attention manually." )
        else:
            helpList[name] = "Help ticket"
            playSFX("sfx_up04")
            return render_template("message.html", forward=request.path, message = "Your ticket was sent. <b>Keep working on the problem the best you can while you wait.</b>" )
    else:
        return render_template("help.html")

#This endpoint allows the teacher to check tickets that students send for help.
@app.route('/needshelp')
def endpoint_needshelp():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['admin']:
        return render_template("message.html", forward=request.path, message = "You do not have high enough permissions to do this right now. " )
    else:
        remove = request.args.get('remove')
        '''
        if bool(helpList):
            pixels.fill(colors['red'])
        else:
            pixels.fill((0, 0, 0))
        pixels.show()
        '''
        if remove:
            if remove in helpList:
                del helpList[remove]
                return render_template("message.html", forward=request.path, message = "Removed ticket for: " + remove +"" )
            else:
                return render_template("message.html", forward=request.path, message = "Couldn't find ticket for: " + remove +"" )
        else:
            resString = '<meta http-equiv="refresh" content="5">'
            if not helpList:
                resString += "No tickets yet. <button onclick='location.reload();'>Try Again</button>"
                return render_template("needshelp.html", table = resString)
            else:
                resString += "<table border=1>"
                for ticket in helpList:
                    resString += "<tr><td><a href=\'/needshelp?remove=" + ticket +"\'>" + ticket + "</a></td><td>" + helpList[ticket] + "</td></tr>"
                resString += "</table>"
                return render_template("needshelp.html", table = resString)

#This endpoint allows students and teacher to chat realTime.
@app.route('/chat')
def endpoint_chat():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['say']:
        return render_template("message.html", forward=request.path, message = "You do not have high enough permissions to do this right now. " )
    else:
        return render_template("chat.html", username = sD.studentDict[request.remote_addr]['name'], serverIp = ip)

#This endpoint allows us to see which user(Student) is logged in.
@app.route('/users')
def endpoint_user():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['users']:
        return render_template("message.html", forward=request.path, message = "You do not have high enough permissions to do this right now. " )
    else:
        user = '';
        if request.args.get('name'):
            for key, value in sD.studentDict.items():
                if request.args.get('name') == sD.studentDict[key]['name']:
                    user = key
                    break
            if not user:
                return render_template("message.html", forward=request.path, message = "That user was not found by their name. " )
        if request.args.get('ip'):
            if request.args.get('ip') in sD.studentDict:
                user = request.args.get('ip')
            else:
                return render_template("message.html", forward=request.path, message = "That user was not found by their IP address. " )
        if user:
            if request.args.get('action'):
                action = request.args.get('action')
                if action == 'kick':
                    if user in sD.studentDict:
                        del sD.studentDict[user]
                        return "User removed"
                    else:
                        return render_template("message.html", forward=request.path, message = "User not in list. " )
                if action == 'ban':
                    if user in sD.studentDict:
                        banList.append(user)
                        del sD.studentDict[user]
                        return "User removed and added to ban list."
                    else:
                        return render_template("message.html", forward=request.path, message = "User not in list. " )
                if action == 'perm':
                    if request.args.get('perm'):
                        try:
                            perm = int(request.args.get('perm'))
                            if user in sD.studentDict:
                                if perm > 4 or perm < 0 :
                                    return render_template("message.html", forward=request.path, message = "Permissions out of range." )
                                else:
                                    sD.studentDict[user]['perms'] = perm
                                    return render_template("message.html", forward=request.path, message = "Changed user permission." )
                            else:
                                return render_template("message.html", forward=request.path, message = "User not in list." )
                        except:
                            return render_template("message.html", forward=request.path, message = "Perm was not an integer." )
            if request.args.get('refresh'):
                refresh = request.args.get('refresh')
                if refresh == 'all':
                    if refreshUsers(user):
                        return render_template("message.html", forward=request.path, message = "Removed all student responses.")
                    else:
                        return render_template("message.html", forward=request.path, message = "Error removing responses from all students.")
                else:
                    if refreshUsers(user, refresh):
                        return render_template("message.html", forward=request.path, message = "Removed " + refresh + " responses from " + user + ".")
                    else:
                        return render_template("message.html", forward=request.path, message = "Error removgin " + refresh + " responses from " + user + ".")
            else:
                return render_template("message.html", forward=request.path, message = "No action given. " )
        else:
            return render_template("users.html")

'''
@app.route('/emptyblocks')
def endpoint_emptyblocks():
    blockList = []
    pixels.fill((0,0,0))
    pixels.show()
    return "Emptied blocks"


@app.route('/sendblock')
def endpoint_sendblock():
    if not sD.settings['barmode'] == 'blockchest':
        return render_template("message.html", forward=request.path, message = "Not in blockchest sD.settings['barmode'] " )
    blockId = request.args.get("id")
    blockData = request.args.get("data")
    if blockId and blockData:
        if blockId in colorDict:
            blockList.append([blockId, blockData])
            addBlock()
            #fillBlocks()
            return "Got Block: " + blockId + ", " + blockData
        else:
            return "Bad block Id"
    else:
        return "Bad Arguments. Requires 'id' and 'data'"
'''

#Shows the different colors the pixels take in the virtualbar.
@app.route('/getpix')
def endpoint_getpix():
    return '{"pixels": "'+ str(pixels[:BARPIX]) +'"}'

@app.route('/getphrase')
def endpoint_getphrase():
    return '{"phrase": "'+ str(sD.activePhrase) +'"}'


@app.route('/2048')
def endpoint_2048():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['games']:
        return render_template("message.html", message = "You do not have high enough permissions to do this right now. " )
    else:
        return render_template('2048.html')

#This endpoint takes you to the hangman game
@app.route('/hangman')
def endpoint_hangman():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['games']:
        return render_template("message.html", message = "You do not have high enough permissions to do this right now. " )
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
        return render_template("hangman.html", wordObj=wordObj)

#Tic Tac Toe
@app.route('/ttt')
def endpoint_ttt():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['student']:
        return render_template("message.html", forward=request.path, message = "You do not have high enough permissions to do this right now. " )
    else:
        opponent = request.args.get('opponent')

        #Loop through all existing games
        for game in sD.ttt:
            #If the user and the opponent is in an existing player list
            if sD.studentDict[request.remote_addr]['name'] in game.players and opponent in game.players:
                #Then you have found the right game and can edit it here
                return render_template("ttt.html", game = str(game))
                #return the response here


        #Creating a new game
        for student in sD.studentDict:
            if sD.studentDict[student]['name'] == opponent:
                sD.ttt.append(sessions.TTTGame([sD.studentDict[request.remote_addr]['name'], opponent]))
                return render_template("ttt.html", game = json.dumps(sD.ttt[-1].__dict__))


        #Ifthere is no game with these players
        return render_template("message.html", message="No game found")

@app.route('/getmode')
def endpoint_getmode():
    return '{"mode": "'+ str(sD.settings['barmode']) +'"}'

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
            logging.error("Could not convert number. " + str(e))
            return render_template("message.html", message="Could not convert number. " + str(e))
    else:
        word = random.choice(list(words.keys()))
        return str(word)

#Sends back your student information
@app.route('/getme')
def endpoint_getme():
    if not request.remote_addr in sD.studentDict:
        return '{"error": "You are not logged in."}'
    else:
        return json.dumps(sD.studentDict[request.remote_addr])

#This endpoints shows the actions the students did EX:TUTD up
@app.route('/getstudents')
def endpoint_getstudents():
    if not request.remote_addr in sD.studentDict:
        return '{"error": "You are not logged in."}'
    if sD.studentDict[request.remote_addr]['perms'] <= sD.settings['perms']['admin']:
        return json.dumps(sD.studentDict)
    elif sD.studentDict[request.remote_addr]['perms'] <= sD.settings['perms']['api']:
        return json.dumps(stripUserData())
    else:
        return '{"error": "Insufficient permissions."}'

@app.route('/getpermissions')
def endpoint_getpermissions():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['api']:
        return render_template("message.html", forward=request.path, message = "You do not have high enough permissions to do this right now. " )
    else:
        return json.dumps(sD.settings['perms'])

@app.route('/getbgm')
def endpoint_getbgm():
    return '{"bgm": "'+ str(sD.bgm['nowplaying']) +'"}'

@app.route('/getquizname')
def endpoint_getquizname():
    if sD.activeQuiz:
        return '{"quizname": "'+ str(sD.activeQuiz['name']) +'"}'
    else:
        return '{"quizname": "''"}'

@app.route('/getfightermatches')
def endpoint_getfightermatches():
    return json.dumps(sD.fighter)

@app.route('/createfightermatch')
def endpoint_createfightermatch():
    code = request.args.get('code')
    name = request.args.get('name')
    sD.fighter['match' + code] = {} #Create new object for match
    sD.fighter['match' + code]['creator'] = name #Set "creator" of object to arg "name"
    return 'Match ' + code + ' created by ' + name

@app.route('/addfighteropponent')
def endpoint_addfighteropponent():
    code = request.args.get('code')
    name = request.args.get('name')
    sD.fighter['match' + code]['opponent'] = name #Set "opponent" of object to arg "name"

#This endpoint allows you to see the formbars IP with style and shows different colors.
@app.route('/virtualbar')
def endpoint_virtualbar():
    return render_template("virtualbar.html", serverIp = sD.ip)

#This endpoint leads to the Sound Effect page
@app.route('/sfx')
def endpoint_sfx():

    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['sfx']:
        return render_template("message.html", forward=request.path, message = "You do not have high enough permissions to do this right now. " )
    else:
        sfx.updateFiles()
        sfx_file = request.args.get('file')
        if sfx_file in sfx.sound:
            playSFX(sfx_file)
            return render_template("message.html", forward=request.path, message = 'Playing: ' + sfx_file )
        else:
            resString = '<h2>List of available sound files:</h2><ul>'
            for key, value in sfx.sound.items():
                resString += '<li><a href="/sfx?file=' + key + '">' + key + '</a></li>'
            resString += '</ul> You can play them by using \'/sfx?file=<b>&lt;sound file name&gt;</b>\''
            return render_template("general.html", content = resString, style = '<style>ul {columns: 2; -webkit-columns: 2; -moz-columns: 2;}</style>')

#This endpoint leads to the Background music page
@app.route('/bgm')
def endpoint_bgm():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    if sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['bgm']:
        return render_template("message.html", forward=request.path, message = "You do not have high enough permissions to do this right now. " )
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
                    except:
                        logging.warning("Could not convert volume to float. Setting to default.")
                        bgm_volume = 0.5
                    sD.bgm['nowplaying']= bgm_file
                    if bgm_volume and type(bgm_volume) is float:
                        startBGM(bgm_file, bgm_volume)
                    else:
                        startBGM(bgm_file)
                    return render_template("message.html", forward=request.path, message = 'Playing: ' + bgm_file )
                else:
                    return render_template("message.html", forward=request.path, message = "It has only been " + str(int(time.time() - sD.bgm['lastTime'])) + " seconds since the last song started. Please wait at least 60 seconds.")
            else:
                return render_template("message.html", forward=request.path, message = "Cannot find that filename!")
        elif request.args.get('voladj'):
            if request.args.get('voladj') == 'up':
                volBGM('up')
                return render_template("message.html", message = 'Music volume increased by one increment.' )
            elif request.args.get('voladj') == 'down':
                volBGM('down')
                return render_template("message.html", message = 'Music volume decreased by one increment.' )
            else:
                return render_template("message.html", message = 'Invalid voladj. Use \'up\' or \'down\'.' )
        else:
            resString = '<a href="/bgmstop">Stop Music</a>'
            resString += '<h2>Now playing: ' + sD.bgm['nowplaying'] + '</h2>'
            resString += '<h2>List of available background music files:</h2><ul>'
            for key, value in bgm.bgm.items():
                resString += '<li><a href="/bgm?file=' + key + '">' + key + '</a></li>'
            resString += '</ul> You can play them by using \'<b>/bgm?file=&lt;sound file name&gt;&volume=&lt;0.0 - 1.0&gt;\'</b>'
            resString += '<br><br>You can stop them by using \'<b>/bgmstop</b>\''
            return render_template("general.html", content = resString, style = '<style>ul {columns: 2; -webkit-columns: 2; -moz-columns: 2;}</style>')

#Stops the current background Music
@app.route('/bgmstop')
def endpoint_bgmstop():
    sD.bgm['paused'] = False
    stopBGM()
    return render_template("message.html", message = 'Stopped music...' )

@app.route('/perc')
def endpoint_perc():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    elif sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['bar']:
        return render_template("message.html", forward=request.path, message = "You do not have high enough permissions to do this right now. " )
    else:
        percAmount = request.args.get('amount')
        try:
            percAmount = int(percAmount)
            percFill(percAmount)
        except:
            return render_template("message.html", forward=request.path, message = "<b>amount</b> must be an integer between 0 and 100 \'/perc?amount=<b>50</b>\'" )
        return render_template("message.html", forward=request.path, message = "Set perecentage to: " + str(percAmount) + "" )

@app.route('/say')
def endpoint_say():
    if not request.remote_addr in sD.studentDict:
        return redirect('/login?forward=' + request.path)
    elif sD.studentDict[request.remote_addr]['perms'] > sD.settings['perms']['bar']:
        return render_template("message.html", forward=request.path, message = "You do not have high enough permissions to do this right now. " )
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
            pixels.show()
        else:
            return render_template("message.html", message = "<b>phrase</b> must contain a string. \'/say?phrase=<b>\'hello\'</b>\'" )
        return render_template("message.html", message = "Set phrase to: " + str(sD.activePhrase) + "" )

#Startup stuff
sD.activePhrase = sD.ip
showString(sD.activePhrase)
pixels.show()
if '--silent' not in str(sys.argv):
    playSFX("sfx_bootup02")

'''
    Websocket Setup
    https://github.com/Pithikos/python-websocket-server

    A message to or from the server should be a stringified JSON object:
    {
        type: <alert|userlist|help|message>,
        to: <*username*|server|all>,
        from: <*username*|server>,
        content: <message>
    }

'''

def packMSG(type, rx, tx, content):
    msgOUT = {
        "type": type,
        "to": rx,
        "from": tx,
        "content": content
        }
    return msgOUT

# Called for every client connecting (after handshake)
def new_client(client, server):
    # try:
        sD.studentDict[client['address'][0]]['wsID'] = client['id']
        logging.info(sD.studentDict[client['address'][0]]['name'] + " connected and was given id %d" % client['id'])
        server.send_message_to_all(json.dumps(packMSG('alert', 'all', 'server', sD.studentDict[client['address'][0]]['name'] + " has joined the server...")))
        server.send_message_to_all(json.dumps(packMSG('userlist', 'all', 'server', chatUsers())))
    # except Exception as e:
    #     logging.error("Error finding user in list: " + str(e))

# Called for every client disconnecting
def client_left(client, server):
    logging.info(sD.studentDict[client['address'][0]]['name'] + " disconnected")
    del sD.studentDict[client['address'][0]]['wsID']
    #Send a message to every client that isn't THIS disconnecting client, telling them the user disconnected
    for i, user in enumerate(server.clients):
        if not server.clients[i] == client:
            server.send_message(server.clients[i], json.dumps(packMSG('alert', 'all', 'server', sD.studentDict[client['address'][0]]['name'] + " has left the server...")))
            server.send_message(server.clients[i], json.dumps(packMSG('userlist', 'all', 'server', chatUsers())))

# Called when a client sends a message
def message_received(client, server, message):
    try:
        message = json.loads(message)
        if message['game'] == 'fighter':
            server.send_message(message.to, json.dumps(message))
        if message['type'] == 'ttt':
            #For now, this will only forward the gamestate. We'll do validation later.
            #server.send_message(message.to, json.dumps(message))
            pass
        if message['type'] == 'userlist':
            server.send_message(client, json.dumps(packMSG('userlist', sD.studentDict[client['address'][0]]['name'], 'server', chatUsers())))
        if message['type'] == 'alert':
            server.send_message(client, json.dumps(packMSG('alert', sD.studentDict[client['address'][0]]['name'], 'server', 'Only the server can send alerts!')))
        if message['type'] == 'help':
            name = sD.studentDict[client['address'][0]]['name']
            name = name.replace(" ", "")
            helpList[name] = message['content']
            playSFX("sfx_up04")
            server.send_message(client, json.dumps(packMSG('alert', sD.studentDict[client['address'][0]]['name'], 'server', 'Your help ticket was sent. Keep working on the problem while you wait!')))
        else:
            #Check for permissions
            if sD.studentDict[client['address'][0]]['perms'] > sD.settings['perms']['say']:
                messageOut = packMSG('alert', sD.studentDict[client['address'][0]]['name'], 'server', "You do not have permission to send text messages.")
                server.send_message(client, json.dumps(messageOut))
            else:
                #Checking max message length here
                if len(message['content']) > 252:
                    message['content'] = message['content'][:252]+'...'
                #Check recipients here
                if message['to'] == 'all':
                    messageOut =  packMSG('message', 'all', sD.studentDict[client['address'][0]]['name'], message['content'])
                    server.send_message_to_all(json.dumps(messageOut))
                else:
                    for student in sD.studentDict:
                        if sD.studentDict[student]['name'] == message['to'] or sD.studentDict[student]['name'] == message['from']:
                            for toClient in server.clients:
                                if toClient['id'] == sD.studentDict[student]['wsID']:
                                    messageOut =  packMSG('message', message['to'], sD.studentDict[client['address'][0]]['name'], message['content'])
                                    server.send_message(toClient, json.dumps(messageOut))
                                    break
                logging.info(message['from'] + " said to " + message['to'] + ": " + message['content'])
    except Exception as e:
        logging.error('Error: ' + str(e))

def start_flask():
    app.run(host='0.0.0.0', use_reloader=False, debug=False)

#This function activate chat and let students chat with one another.
def start_chat():
    server = WebsocketServer(WSPORT, host='0.0.0.0')
    server.set_fn_new_client(new_client)
    server.set_fn_client_left(client_left)
    server.set_fn_message_received(message_received)
    server.run_forever()

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
    chatApp = threading.Thread(target=start_chat, daemon=True)
    chatApp.start()#Starts up the chat feature
    #irApp = threading.Thread(target=start_IR, daemon=True)
    #irApp.start()#Starts up the chat feature
    # flaskApp = threading.Thread(target=start_flask)
    # flaskApp.start()
    # flaskApp.join()
    start_flask()
