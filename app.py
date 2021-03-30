from flask import Flask, redirect, url_for, request, render_template
from websocket_server import WebsocketServer
import board, neopixel
import json, csv
import pygame
import time, math
import threading
import multiprocessing
import netifaces as ni
ni.ifaddresses('eth0')
ip = ni.ifaddresses('eth0')[ni.AF_INET][0]['addr']


WSPORT=9001

print('Running formbar server on:' + ip)

import letters
import sfx
import bgm
from colors import colors, hex2dec

import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

BARPIX = 240
MAXPIX = 762

sfx.updateFiles()
bgm.updateFiles()
pygame.init()

pixels = neopixel.NeoPixel(board.D21, MAXPIX, brightness=1.0, auto_write=False)

app = Flask(__name__)

# 0 - teacher
# 1 - mod
# 2 - student
# 3 - anyone
settingsPerms = {
    'admin' : 0,
    'users' : 1,
    'api' : 3,
    'sfx' : 1,
    'bgm' : 1,
    'say' : 1,
    'bar' : 1
}

settingsBoolDict = {
    'locked' : False,
    'paused' : False,
    'blind' : False,
    'showinc' : True,
    'captions' : True
}
settingsIntDict = {
    'numStudents': 8
}

settingsStrDict = {
    'mode': 'thumbs'
}

settingsStrList = {
    'modes': ['thumbs', 'survey', 'quiz', 'essay', 'help', 'kahoot', 'playtime', 'blockchest']
}

whiteList = [
    '127.0.0.1',
    '172.21.3.5'
    ]

banList = []

studentList = {
}

settingsIntDict['numStudents'] = 8
up = down = wiggle = 0
ipList = {}
helpList = {}
blockList = []
colorDict = {
        '14': (255, 255, 0),
        '15': (196, 150, 128),
        '16': (255, 96, 0),
        '56': (0, 192, 192),
        }

quizQuestion = ''
quizAnswers = []
quizCorrect = ''

backButton = "<br><button onclick='window.history.back()'>Go Back</button><script language='JavaScript' type='text/javascript'>setTimeout(\"window.history.back()\",5000);</script>"

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
    if len(threading.enumerate()) < 4:
        threading.Thread(target=aniTest, daemon=True).start()
        return 'testing...'
    else:
        return 'Too many threads'

def newStudent(remote, username, forward='', pin=''):
    global studentList
    if not remote in studentList:
        studentList[remote] = {
            'name': username,
            'thumb': '',
            'survey': '',
            'perms': 2,
            'banstatus': False
        }
        if len(studentList) - 1:
            print("New user logged in. Made them a student: " + username)
            studentList[remote]['perms'] = 2
        else:
            print("First user logged in. Made them a Teacher: " + username)
            studentList[remote]['perms'] = 0
        if forward:
            return redirect(forward, code=302)

def playSFX(sound):
    pygame.mixer.Sound(sfx.sound[sound]).play()
def playBGM(bgm_filename, volume=1.0):
    pygame.mixer.music.load(bgm.bgm[bgm_filename])
    pygame.mixer.music.set_volume(volume)
    pygame.mixer.music.play(loops=-1)
def stopBGM():
    pygame.mixer.music.stop()

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

def fillBar(color=colors['default'], stop=BARPIX, start=0):
    #If you provide no args, the whole bar is made the default color
    #If you provide one arg, the whole bar will be that color
    #If you provide two args, the bar will be that color until the stop point
    #If you provide three args, pixels between the stop and start points will be that color
    for pix in range(start, stop):
        pixels[pix] = color

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
            print("Error! Letter ", letter, " not found.")
    else:
        print("Error! Not enough space for this letter!")

def surveyBar():
    results = [] # Create empty results list
    clearBar()
    #Go through IP list and see what each IP sent as a response
    for x in ipList:
        #add this result to the results list
        results.append(ipList[x])
    #The number of results is how many have completed the survey
    complete = len(results)
    #calculate the chunk length for each student
    chunkLength = math.floor(BARPIX / settingsIntDict['numStudents'])
    #Sort the results by "alphabetical order"
    results.sort()
    #Loop through each result, and show the correct color
    for index, result in enumerate(results):
        #Calculate how long this chunk will be and where it starts
        pixRange = range((chunkLength * index), (chunkLength * index) + chunkLength)
        #Fill in that chunk with the correct color
        if result == 'a':
            for i, pix in enumerate(pixRange):
                #If it's the first pixel of the chunk, make it a special color
                if i == 0:
                    pixels[pix] = colors['student']
                else:
                    if settingsBoolDict['blind'] and complete != settingsIntDict['numStudents']:
                        pixels[pix] = fadein(pixRange, i, colors['blind'])
                    else:
                        pixels[pix] = fadein(pixRange, i, colors['red'])
        elif result == 'b':
            for i, pix in enumerate(pixRange):
                if i == 0:
                    pixels[pix] = colors['student']
                else:
                    if settingsBoolDict['blind'] and complete != settingsIntDict['numStudents']:
                        pixels[pix] = fadein(pixRange, i, colors['blind'])
                    else:
                        pixels[pix] = fadein(pixRange, i, colors['blue'])
        elif result == 'c':
            for i, pix in enumerate(pixRange):
                if i == 0:
                    pixels[pix] = colors['student']
                else:
                    if settingsBoolDict['blind'] and complete != settingsIntDict['numStudents']:
                        pixels[pix] = fadein(pixRange, i, colors['blind'])
                    else:
                        pixels[pix] = fadein(pixRange, i, colors['yellow'])
        elif result == 'd':
            for i, pix in enumerate(pixRange):
                if i == 0:
                    pixels[pix] = colors['student']
                else:
                    if settingsBoolDict['blind'] and complete != settingsIntDict['numStudents']:
                        pixels[pix] = fadein(pixRange, i, colors['blind'])
                    else:
                        pixels[pix] = fadein(pixRange, i, colors['green'])
    if settingsBoolDict['captions']:
        clearString()
        showString("SRVY " + str(complete) + "/" + str(settingsIntDict['numStudents']))
    pixels.show()

def tutdBar():
    global studentList
    upFill = upCount = downFill = wiggleFill = 0
    complete = 0
    for x in studentList:
        if studentList[x]['thumb']:
            if studentList[x]['thumb'] == 'up':
                upFill += 1
                upCount += 1
            elif studentList[x]['thumb'] == 'down':
                downFill += 1
            elif studentList[x]['thumb'] == 'wiggle':
                wiggleFill += 1
            complete += 1
    for pix in range(0, BARPIX):
        pixels[pix] = colors['default']
    if settingsBoolDict['showinc']:
        chunkLength = math.floor(BARPIX / settingsIntDict['numStudents'])
    else:
        chunkLength = math.floor(BARPIX / complete)
    for index, ip in enumerate(studentList):
        pixRange = range((chunkLength * index), (chunkLength * index) + chunkLength)
        if upFill > 0:
            for i, pix in enumerate(pixRange):
                if i == 0:
                    pixels[pix] = colors['student']
                else:
                    if settingsBoolDict['blind'] and complete != settingsIntDict['numStudents']:
                        pixels[pix] = fadein(pixRange, i, colors['blind'])
                    else:
                        pixels[pix] = fadein(pixRange, i, colors['green'])
            upFill -= 1
        elif wiggleFill > 0:
            for i, pix in enumerate(pixRange):
                if i == 0:
                    pixels[pix] = colors['student']
                else:
                    if settingsBoolDict['blind'] and complete != settingsIntDict['numStudents']:
                        pixels[pix] = fadein(pixRange, i, colors['blind'])
                    else:
                        pixels[pix] = fadein(pixRange, i, colors['yellow'])
            wiggleFill -= 1
        elif downFill > 0:
            for i, pix in enumerate(pixRange):
                if i == 0:
                    pixels[pix] = colors['student']
                else:
                    if settingsBoolDict['blind'] and complete != settingsIntDict['numStudents']:
                        pixels[pix] = fadein(pixRange, i, colors['blind'])
                    else:
                        pixels[pix] = fadein(pixRange, i, colors['red'])
            downFill -= 1
    if settingsBoolDict['captions']:
        clearString()
        showString("TUTD " + str(complete) + "/" + str(settingsIntDict['numStudents']))
        pixels.show()
    if upCount >= settingsIntDict['numStudents']:
        settingsBoolDict['paused'] = True
        pixels.fill((0,0,0))
        playSFX("success01")
        for i, pix in enumerate(range(0, BARPIX)):
                pixels[pix] = blend(range(0, BARPIX), i, colors['blue'], colors['red'])
        if settingsBoolDict['captions']:
            clearString()
            showString("MAX GAMER!", 0, colors['purple'])
    pixels.show()

@app.route('/')
def endpoint_home():
    return render_template('index.html')

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
            newStudent(remote, username, forward)
            return redirect('/', code=302)
        elif request.args.get('name'):
            newStudent(remote, request.args.get('name'))
            return redirect('/', code=302)
        else:
            return render_template("login.html")

@app.route('/color')
def endpoint_color():
    if not request.remote_addr in studentList:
        # This will have to send along the current address as "forward" eventually
        return redirect('/login')
    '''
    if settingsBoolDict['locked'] == True:
        if not request.remote_addr in whiteList:
            return "You are not whitelisted. " + backButton
    '''
    if studentList[request.remote_addr]['perms'] > settingsPerms['bar']:
        return "You do not have high enough permissions to do this right now. " + backButton
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
            return "Bad Arguments<br><br>Try <b>/color?hex=#FF00FF</b> or <b>/color?r=255&g=0&b=255</b>"
        pixels.show()
        return "Color sent!<br>" + backButton

@app.route('/segment')
def endpoint_segment():
    if not request.remote_addr in studentList:
        # This will have to send along the current address as "forward" eventually
        return redirect('/login')
    if studentList[request.remote_addr]['perms'] > settingsPerms['bar']:
        return "You do not have high enough permissions to do this right now. " + backButton
    else:
        type = request.args.get('type')
        hex = request.args.get('hex')
        hex2 = request.args.get('hex2')
        start = request.args.get('start')
        end = request.args.get('end')
        if not hex:
            return "Bad Arguments<br><br>Try <b>/segment?start=0&end=10&hex=#FF00FF</b> (you need at least one color)"
        if not hex2dec(hex):
            return "Bad Arguments<br><br>Try <b>/segment?start=0&end=10&hex=#FF00FF</b> (you did not use a proper hexadecimal color)"
        if not start or not end:
            return "Bad Arguments<br><br>Try <b>/segment?start=0&end=10&hex=#FF00FF</b> (you need a start and end point)"
        else:
            try:
                start = int(start)
                end = int(end)
            except:
                return "Bad Arguments<br><br>Try <b>/segment?start=0&end=10&hex=#FF00FF</b> (start and end must be and integer)"
        if start > BARPIX or end > BARPIX:
            return "Bad Arguments<br><br>Try <b>/segment?start=0&end=10&hex=#FF00FF</b> (Your start or end was higher than the number of pixels: " + str(BARPIX) + ")"
        pixRange = range(start, end)
        if type == 'fadein':
            for i, pix in enumerate(pixRange):
                pixels[pix] = fadein(pixRange, i, hex2dec(hex))
        elif type == 'fadeout':
            for i, pix in enumerate(pixRange):
                pixels[pix] = fadeout(pixRange, i, hex2dec(hex))
        elif type == 'blend':
            if not hex:
                return "Bad Arguments<br><br>Try <b>/segment?start=0&end=10&hex=#FF00FF&hex2=#00FF00</b> (you need at least two colors)"
            if not hex2dec(hex):
                return "Bad Arguments<br><br>Try <b>/segment?start=0&end=10&hex=#FF00FF&hex2=#00FF00</b> (you did not use a proper hexadecimal color)"
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
                return "Bad Arguments<br><br>Try <b>/color?hex=#FF00FF</b> or <b>/color?r=255&g=0&b=255</b>"
        pixels.show()
        return "Color sent!<br>" + backButton

@app.route('/settings', methods = ['POST', 'GET'])
def settings():
    global ipList

    if not request.remote_addr in studentList:
        # This will have to send along the current address as "forward" eventually
        return redirect('/login')
    '''
    if settingsBoolDict['locked'] == True:
        if not request.remote_addr in whiteList:
            return "You are not whitelisted. " + backButton
    '''
    if studentList[request.remote_addr]['perms'] > settingsPerms['bar']:
        return "You do not have high enough permissions to do this right now. " + backButton
    else:
        ipList = {}
        for student in studentList:
            studentList[student]['thumb'] = ''
        tutdBar()
        if request.method == 'POST':
            quizQuestion = request.form['qQuestion']
            quizCorrect = int(request.form['quizlet'])
            quizAnswers = [request.form['qaAnswer'], request.form['qbAnswer'], request.form['qcAnswer'], request.form['qdAnswer']]
            if settingsStrDict['mode'] == 'thumbs':
                tutdBar()
            elif settingsStrDict['mode'] == 'survey':
                surveyBar()
            playSFX("success01")
            settingsBoolDict['paused'] = False
            return redirect(url_for('settings'))
        else:
            resString = ''
            #Loop through every arg that was sent as a query parameter
            for arg in request.args:
                #See if you save the
                argVal = str2bool(request.args.get(arg))
                #if the argVal resolved to a boolean value
                if isinstance(argVal, bool):
                    if arg in settingsBoolDict:
                        settingsBoolDict[arg] = argVal
                        resString += 'Set <i>' + arg + '</i> to: <i>' + str(argVal) + "</i>"
                    else:
                        resString += 'There is no setting that takes \'true\' or \'false\' named: <i>' + arg + "</i>"
                else:
                    try:
                        argInt = int(request.args.get(arg))
                        if arg in settingsPerms:
                            if argInt > 3 or argInt < 0:
                                resString += "Permission value out of range! "
                            else:
                                settingsPerms[arg] = argInt
                    except:
                        pass

            ###
            ### Everything past this point uses the old method of changing settings. Needs updated
            ###

            if request.args.get('students'):
                settingsIntDict['numStudents'] = int(request.args.get('students'))
                resString += 'Set <i>numStudents</i> to: ' + str(settingsIntDict['numStudents'])
            if request.args.get('mode'):
                if request.args.get('mode') in settingsStrList['modes']:
                    ipList = {}
                    settingsStrDict['mode'] = request.args.get('mode')
                    resString += 'Set <i>mode</i> to: ' + settingsStrDict['mode']
                else:
                    resString += 'No setting called ' + settingsStrDict['mode']
            if resString == '':
                return render_template("settings.html")
            else:
                playSFX("pickup01")
                resString += "<br>" + backButton
                return resString

@app.route('/flush')
def endpoint_flush():
    if not request.remote_addr in studentList:
        # This will have to send along the current address as "forward" eventually
        return redirect('/login')
    if studentList[request.remote_addr]['perms'] > settingsPerms['admin']:
        return "You do not have high enough permissions to do this right now. " + backButton
    else:
        for user in studentList:
            if not user['perms'] == settingsPerms['admin']:
                del user['perms']

@app.route('/quiz')
def endpoint_quiz():
    if not request.remote_addr in studentList:
        # This will have to send along the current address as "forward" eventually
        return redirect('/login')
    '''
    if settingsBoolDict['locked'] == True:
        if not request.remote_addr in whiteList:
            return "You are not whitelisted. " + backButton
    '''
    if studentList[request.remote_addr]['perms'] > settingsPerms['bar']:
        return "You do not have high enough permissions to do this right now. " + backButton
    else:
        answer = request.args.get('answer')
        if answer:
            answer = int(answer)
            if request.remote_addr not in ipList:
                if answer == quizCorrect:
                    ipList[request.remote_addr] = 'up'
                else:
                    ipList[request.remote_addr] = 'down'
                tutdBar()
                return "Thank you for your tasty bytes...<br>" + backButton
            else:
                return "You have already answered this quiz.<br>" + backButton
        else:
            resString = '<meta http-equiv="refresh" content="5">'
            if request.remote_addr in ipList:
                resString += '<b><i>You have already answered this question. Wait for a new one</b></i>'
            resString += '<table border=1><tr><td>' + quizQuestion + '</td></tr>'
            for i, question in enumerate(quizAnswers):
                resString += '<tr><td><a href="/quiz?answer=' + str(i) + '">' + question + '</a></td></tr>'
            resString += '</table>'
            return resString

@app.route('/survey')
def endpoint_survey():
    if not request.remote_addr in studentList:
        # This will have to send along the current address as "forward" eventually
        return redirect('/login')
    '''
    if settingsBoolDict['locked'] == True:
        if not request.remote_addr in whiteList:
            return "You are not whitelisted. " + backButton
    '''
    if studentList[request.remote_addr]['perms'] > settingsPerms['bar']:
        return "You do not have high enough permissions to do this right now. " + backButton
    else:
        if not settingsStrDict['mode'] == 'survey':
            return "Not in Survey mode <br>" + backButton
        ip = request.remote_addr
        vote = request.args.get('vote')
        name = request.args.get('name')
        if not name:
            name = 'unknown'
        elif vote:
            print("Recieved " + vote + " from " + name + " at " + ip)
            playSFX("blip01")
        #if settingsStrDict['mode'] != 'survey':
            #return "There is no survey right now<br>" + backButton
        if vote:
            if vote in ["a", "b", "c", "d"]:
                ipList[request.remote_addr] = vote
                surveyBar()
                return "Thank you for your tasty bytes... (" + vote + ")<br>" + backButton
            elif vote == 'oops':
                ipList.pop(ip)
                surveyBar()
                return "I won\'t mention it if you don\'t<br>" + backButton
            else:
                return "Bad Arguments<br><br>Try <b>/survey?vote=a</b>"
        else:
            return render_template("thumbsrental.html")

@app.route('/tutd')
def endpoint_tutd():
    if not request.remote_addr in studentList:
        # This will have to send along the current address as "forward" eventually
        return redirect('/login')
    else:
        ip = request.remote_addr
        thumb = request.args.get('thumb')
        if thumb:
            # print("Recieved " + thumb + " from " + name + " at ip: " + ip)
            playSFX("blip01")
            if thumb == 'up' or thumb == 'down' or thumb == 'wiggle' :
                studentList[request.remote_addr]['thumb'] = request.args.get('thumb')
                tutdBar()
                return "Thank you for your tasty bytes... (" + thumb + ")<br>" + backButton
            elif thumb == 'oops':
                studentList[request.remote_addr]['thumb'] = ''
                playSFX("hit01")
                tutdBar()
                return "I won\'t mention it if you don\'t<br>" + backButton
            else:
                return "Bad Arguments<br><br>Try <b>/tutd?thumb=wiggle</b><br><br>You can also try <b>down</b> and <b>up</b> instead of <b>wiggle</b>"
        else:
            return render_template("thumbsrental.html")

@app.route('/help', methods = ['POST', 'GET'])
def endpoint_help():
    if not request.remote_addr in studentList:
        # This will have to send along the current address as "forward" eventually
        return redirect('/login')
    if request.method == 'POST':
        name = studentList[request.remote_addr]['name']
        name = name.replace(" ", "")
        helpList[name] = "Help ticket"
        playSFX("up04")
        return "Your ticket was sent. Keep working on the problem the best you can while you wait.<br>" + backButton
    else:
        return render_template("help.html")

@app.route('/needshelp')
def endpoint_needshelp():
    if not request.remote_addr in studentList:
        # This will have to send along the current address as "forward" eventually
        return redirect('/login')
    if studentList[request.remote_addr]['perms'] > settingsPerms['admin']:
        return "You do not have high enough permissions to do this right now. " + backButton
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
                return "Removed ticket for: " + remove +"<br>" + backButton
            else:
                return "Couldn't find ticket for: " + remove +"<br>" + backButton
        else:
            resString = '<meta http-equiv="refresh" content="5">'
            if not helpList:
                resString += "No tickets yet. <br><button onclick='location.reload();'>Try Again</button>"
                return resString
            else:
                resString += "<table border=1>"
                for ticket in helpList:
                    resString += "<tr><td><a href=\'/needshelp?remove=" + ticket +"\'>" + ticket + "</a></td><td>" + helpList[ticket] + "</td></tr>"
                resString += "</table>"
                return resString

@app.route('/chat')
def endpoint_chat():
    if not request.remote_addr in studentList:
        # This will have to send along the current address as "forward" eventually
        return redirect('/login')
    if studentList[request.remote_addr]['perms'] > settingsPerms['say']:
        return "You do not have high enough permissions to do this right now. " + backButton
    else:
        return render_template("chat.html", username = studentList[request.remote_addr]['name'], serverIp = ip)

@app.route('/users')
def endpoint_user():
    if not request.remote_addr in studentList:
        # This will have to send along the current address as "forward" eventually
        return redirect('/login')
    '''
    if settingsBoolDict['locked'] == True:
        if not request.remote_addr in whiteList:
            return "You are not whitelisted. " + backButton
    '''
    if studentList[request.remote_addr]['perms'] > settingsPerms['users']:
        return "You do not have high enough permissions to do this right now. " + backButton
    else:
        user = '';
        if request.args.get('name'):
            for key, value in studentList.items():
                if request.args.get('name') == studentList[key]['name']:
                    user = key
                    break
            if not user:
                return "That user was not found by their name. " + backButton
        if request.args.get('ip'):
            if request.args.get('ip') in studentList:
                user = request.args.get('ip')
            else:
                return "That user was not found by their IP address. " + backButton
        if user:
            if request.args.get('action'):
                action = request.args.get('action')
                if action == 'kick':
                    if user in studentList:
                        del studentList[user]
                        return "User removed"
                    else:
                        return "User not in list. " + backButton
                if action == 'ban':
                    if user in studentList:
                        banList.append(user)
                        del studentList[user]
                        return "User removed and added to ban list."
                    else:
                        return "User not in list. " + backButton
                if action == 'perm':
                    if request.args.get('perm'):
                        try:
                            perm = int(request.args.get('perm'))
                            if user in studentList:
                                if perm > 3 or perm < 0 :
                                    return "Permissions out of range. " + backButton
                                else:
                                    studentList[user]['perms'] = perm
                                    return "Changed user permission. " + backButton
                            else:
                                return "User not in list. " + backButton
                        except:
                            return "Perm was not an integer. " + backButton
            else:
                return "No action given. " + backButton
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
    if not settingsStrDict['mode'] == 'blockchest':
        return "Not in blockchest settingsStrDict['mode'] <br>" + backButton
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

@app.route('/getpix')
def endpoint_getpix():
    return '{"pixels": "'+ str(pixels[:BARPIX]) +'"}'

@app.route('/getstudents')
def endpoint_getstudents():
    if not request.remote_addr in studentList:
        # This will have to send along the current address as "forward" eventually
        return redirect('/login')
    if studentList[request.remote_addr]['perms'] > settingsPerms['api']:
        return "You do not have high enough permissions to do this right now. " + backButton
    else:
        return json.dumps(studentList)

@app.route('/getpermissions')
def endpoint_getpermissions():
    if not request.remote_addr in studentList:
        # This will have to send along the current address as "forward" eventually
        return redirect('/login')
    if studentList[request.remote_addr]['perms'] > settingsPerms['api']:
        return "You do not have high enough permissions to do this right now. " + backButton
    else:
        return json.dumps(settingsPerms)

@app.route('/virtualbar')
def endpoint_virtualbar():
    return render_template("virtualbar.html", serverIp = ip)

@app.route('/sfx')
def endpoint_sfx():
    if not request.remote_addr in studentList:
        # This will have to send along the current address as "forward" eventually
        return redirect('/login')
    if studentList[request.remote_addr]['perms'] > settingsPerms['sfx']:
        return "You do not have high enough permissions to do this right now. " + backButton
    else:
        sfx.updateFiles()
        sfx_file = request.args.get('file')
        if sfx_file in sfx.sound:
            playSFX(sfx_file)
            return 'Playing: ' + sfx_file + backButton
        else:
            resString = '<h2>List of available sound files:</h2><ul>'
            for key, value in sfx.sound.items():
                resString += '<li><a href="/sfx?file=' + key + '">' + key + '</a></li>'
            resString += '</ul> You can play them by using \'/sfx?file=<b>&lt;sound file name&gt;</b>\''
            return resString

@app.route('/bgm')
def endpoint_bgm():
    if not request.remote_addr in studentList:
        # This will have to send along the current address as "forward" eventually
        return redirect('/login')
    '''
    if settingsBoolDict['locked'] == True:
        if not request.remote_addr in whiteList:
            return "You are not whitelisted. " + backButton
    '''
    if studentList[request.remote_addr]['perms'] > settingsPerms['bgm']:
        return "You do not have high enough permissions to do this right now. " + backButton
    else:
        bgm.updateFiles()
        bgm_file = request.args.get('file')
        if bgm_file in bgm.bgm:
            bgm_volume = request.args.get('volume')
            if bgm_volume and type(bgm_volume) is float:
                playBGM(bgm_file, bgm_volume)
            else:
                playBGM(bgm_file)
            return 'Playing: ' + bgm_file + backButton
        else:
            resString = '<h2>List of available background music files:</h2><ul>'
            for key, value in bgm.bgm.items():
                resString += '<li><a href="/bgm?file=' + key + '">' + key + '</a></li>'
            resString += '</ul> You can play them by using \'<b>/bgm?file=&lt;sound file name&gt;&volume=&lt;0.0 - 1.0&gt;\'</b>'
            resString += '<br>You can stop them by using \'<b>/bgmstop</b>\''
            return resString

@app.route('/bgmstop')
def endpoint_bgmstop():
    stopBGM()
    return 'Stopped music...' + backButton

@app.route('/perc')
def endpoint_perc():
    if not request.remote_addr in studentList:
        # This will have to send along the current address as "forward" eventually
        return redirect('/login')
    '''
    if settingsBoolDict['locked'] == True:
        if not request.remote_addr in whiteList:
            return "You are not whitelisted. " + backButton
    '''
    if studentList[request.remote_addr]['perms'] > settingsPerms['bar']:
        return "You do not have high enough permissions to do this right now. " + backButton
    else:
        percAmount = request.args.get('amount')
        try:
            percAmount = int(percAmount)
            percFill(percAmount)
        except:
            return "<b>amount</b> must be an integer between 0 and 100 \'/perc?amount=<b>50</b>\'<br>" + backButton
        return "Set perecentage to: " + str(percAmount) + "<br>" + backButton

@app.route('/say')
def endpoint_say():
    if not request.remote_addr in studentList:
        # This will have to send along the current address as "forward" eventually
        return redirect('/login')
    '''
    if settingsBoolDict['locked'] == True:
        if not request.remote_addr in whiteList:
            return "You are not whitelisted. " + backButton
    '''
    if studentList[request.remote_addr]['perms'] > settingsPerms['bar']:
        return "You do not have high enough permissions to do this right now. " + backButton
    else:
        phrase = request.args.get('phrase')
        fgColor = request.args.get('fg')
        bgColor = request.args.get('bg')
        if phrase:
            if hex2dec(fgColor) and hex2dec(bgColor):
                clearString()
                showString(phrase, 0, hex2dec(fgColor), hex2dec(bgColor))
            else:
                clearString()
                showString(phrase)
            pixels.show()
            #engine.say(p)
            #engine.runAndWait()
        else:
            return "<b>phrase</b> must contain a string. \'/say?phrase=<b>\'hello\'</b>\'<br>" + backButton
        return "Set phrase to: " + str(phrase) + "<br>" + backButton

#Startup stuff
showString(ip)
pixels.show()
playSFX("bootup02")

def start_flask():
    app.run(host='0.0.0.0', use_reloader=False, debug = False)

def start_chat():
    server = WebsocketServer(WSPORT, host='0.0.0.0')
    server.set_fn_new_client(new_client)
    server.set_fn_client_left(client_left)
    server.set_fn_message_received(message_received)
    server.run_forever()

if __name__ == '__main__':
    flaskApp = multiprocessing.Process(target=start_flask)
    chatApp = multiprocessing.Process(target=start_chat)
    flaskApp.start()
    chatApp.start()
    flaskApp.join()
    chatApp.join()
