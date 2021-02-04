from flask import Flask, redirect, url_for, request, render_template
import board, neopixel
import json, csv
import pygame
import time, math
import netifaces as ni
ni.ifaddresses('eth0')
ip = ni.ifaddresses('eth0')[ni.AF_INET][0]['addr']
#import pyttsx3
#engine = pyttsx3.init()

import letters
from sfx import sfx
from colors import colors

print(colors['red'])

import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

BARPIX = 240
MAXPIX = 762
perc = 0
locked = False
paused = False
blind = False
showInc = True
mode = 'thumbs'
modes = ['thumbs', 'survey', 'quiz', 'essay', 'help', 'kahoot', 'playtime', 'blockchest']
whiteList = [
    '127.0.0.1',
    '172.21.3.5'
    ]

backButton = "<button onclick='window.history.back()'>Go Back</button><script language='JavaScript' type='text/javascript'>setTimeout(\"window.history.back()\",5000);</script>"

pygame.init()

pixels = neopixel.NeoPixel(board.D21, MAXPIX, brightness=1.0, auto_write=False)

app = Flask(__name__)

numStudents = 8
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
    global colorDict
    if blockList[-1][0] in colorDict:
        pixels[len(blockList)-1] = colorDict[blockList[-1][0]]
    else:
        pixels[len(blockList)-1] = colors['default']
    pixels.show()

def fillBlocks():
    global colorDict
    for i, block in enumerate(blockList):
        if block[0] in colorDict:
            pixels[i] = colorDict[block[0]]
        else:
            pixels[i] = colors['default']
    pixels.show()

def percFill(amount, fillColor=colors['green'], emptyColor=colors['red']):
    if amount > 1 or amount < 0:
        if amount > 100 and amount < 0 and type(amount) is not int:
            raise TypeError("Out of range. Must be between 0 - 1 or 0 - 100.")
        else:
            amount = amount * 0.01
    pixRange = math.ceil(BARPIX * amount)
    for pix in range(0, BARPIX):
        if pix > pixRange:
            pixels[pix] = fillColor
        pixels[pix] = emptyColor
    pixels.show()

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
        else:
            print("Error! Letter ", letter, " not found.")
    else:
        print("Error! Not enough space for this letter!")

def surveyBar():
    #Create empty results list
    results = []
    #fill with default color to clear bar
    for pix in range(0, BARPIX):
        pixels[pix] = colors['default']
    #Go through IP list and see what each IP sent as a response
    for x in ipList:
        #add this result to the results list
        results.append(ipList[x])
    complete = len(results)
    #calculate the chunk length for each student
    chunkLength = math.floor(BARPIX / numStudents)
    for index, result in enumerate(results):
        pixRange = range((chunkLength * index), (chunkLength * index) + chunkLength)
        if result == 'a':
            for i, pix in enumerate(pixRange):
                if i == 0:
                    pixels[pix] = colors['student']
                else:
                    if blind and complete != numStudents:
                        pixels[pix] = fadein(pixRange, i, colors['blind'])
                    else:
                        pixels[pix] = fadein(pixRange, i, colors['red'])
        elif result == 'b':
            for i, pix in enumerate(pixRange):
                if i == 0:
                    pixels[pix] = colors['student']
                else:
                    if blind and complete != numStudents:
                        pixels[pix] = fadein(pixRange, i, colors['blind'])
                    else:
                        pixels[pix] = fadein(pixRange, i, colors['blue'])
        elif result == 'c':
            for i, pix in enumerate(pixRange):
                if i == 0:
                    pixels[pix] = colors['student']
                else:
                    if blind and complete != numStudents:
                        pixels[pix] = fadein(pixRange, i, colors['blind'])
                    else:
                        pixels[pix] = fadein(pixRange, i, colors['yellow'])
        elif result == 'd':
            for i, pix in enumerate(pixRange):
                if i == 0:
                    pixels[pix] = colors['student']
                else:
                    if blind and complete != numStudents:
                        pixels[pix] = fadein(pixRange, i, colors['blind'])
                    else:
                        pixels[pix] = fadein(pixRange, i, colors['green'])
    clearString()
    showString("SRVY " + str(complete) + "/" + str(numStudents))
    pixels.show()

def fillBar():
    global blind
    global paused
    upFill = upCount = downFill = wiggleFill = 0
    complete = 0
    for x in ipList:
        if ipList[x] == 'up':
            upFill += 1
            upCount += 1
        elif ipList[x] == 'down':
            downFill += 1
        elif ipList[x] == 'wiggle':
            wiggleFill += 1
        complete += 1
    for pix in range(0, BARPIX):
        pixels[pix] = colors['default']
    clearString()
    showString("TUTD " + str(complete) + "/" + str(numStudents))
    pixels.show()
    if showInc:
        chunkLength = math.floor(BARPIX / numStudents)
    else:
        chunkLength = math.floor(BARPIX / complete)
    for index, ip in enumerate(ipList):
        pixRange = range((chunkLength * index), (chunkLength * index) + chunkLength)
        if upFill > 0:
            for i, pix in enumerate(pixRange):
                if i == 0:
                    pixels[pix] = colors['student']
                else:
                    if blind and complete != numStudents:
                        pixels[pix] = fadein(pixRange, i, colors['blind'])
                    else:
                        pixels[pix] = fadein(pixRange, i, colors['green'])
            upFill -= 1
        elif wiggleFill > 0:
            for i, pix in enumerate(pixRange):
                if i == 0:
                    pixels[pix] = colors['student']
                else:
                    if blind and complete != numStudents:
                        pixels[pix] = fadein(pixRange, i, colors['blind'])
                    else:
                        pixels[pix] = fadein(pixRange, i, colors['yellow'])
            wiggleFill -= 1
        elif downFill > 0:
            for i, pix in enumerate(pixRange):
                if i == 0:
                    pixels[pix] = colors['student']
                else:
                    if blind and complete != numStudents:
                        pixels[pix] = fadein(pixRange, i, colors['blind'])
                    else:
                        pixels[pix] = fadein(pixRange, i, colors['red'])
            downFill -= 1
    if upCount >= numStudents:
        paused = True
        pixels.fill((0,0,0))
        pygame.mixer.Sound(sfx["success01"]).play()
        for i, pix in enumerate(range(0, BARPIX)):
                pixels[pix] = blend(range(0, BARPIX), i, colors['blue'], colors['red'])
        showString("MAX GAMER!", 0, colors['purple'])
    pixels.show()

@app.route('/')
def endpoint_home():
    return render_template('index.html')

@app.route('/color')
def endpoint_color():
    if not mode == 'playtime':
        return "Not in play mode <br>" + backButton
    global locked
    if locked == True:
        if not request.remote_addr in whiteList:
            return "Color changing is locked"
    r = int(request.args.get('r'))
    g = int(request.args.get('g'))
    b = int(request.args.get('b'))
    pixels.fill((r,g,b))
    pixels.show()
    return str(r) + ", " + str(g) + ", " + str(b)

@app.route('/settings', methods = ['POST', 'GET'])
def settings():
    global paused
    global locked
    global quizQuestion
    global quizAnswers
    global quizCorrect
    global blind
    global mode
    global showInc

    if locked:
        if request.remote_addr not in whiteList:
            return "STAHP DOING THE SNEAKY HACKERINGS!"
    global numStudents
    global ipList
    ipList = {}
    if request.method == 'POST':
        quizQuestion = request.form['qQuestion']
        quizCorrect = int(request.form['quizlet'])
        quizAnswers = [request.form['qaAnswer'], request.form['qbAnswer'], request.form['qcAnswer'], request.form['qdAnswer']]
        if mode == 'thumbs':
            fillBar()
        elif mode == 'survey':
            surveyBar()
        pygame.mixer.Sound(sfx["success01"]).play()
        paused = False
        print("Quiz answer: " + quizAnswers[quizCorrect])
        return redirect(url_for('settings'))
    else:
        resString = ''
        ### Need to find a better way of handling this
        setLock = request.args.get('locked')
        if setLock == 'true':
            locked = True
            resString += 'Set <i>locked</i> to: ' + str(locked)
        elif setLock == 'false':
            locked = False
            resString += 'Set <i>locked</i> to: ' + str(locked)
        setBlind = request.args.get('blind')
        if setBlind == 'true':
            blind = True
            resString += 'Set <i>blind</i> to: ' + str(blind)
        elif setBlind == 'false':
            blind = False
            resString += 'Set <i>blind</i> to: ' + str(blind)
        setshowInc = request.args.get('showinc')
        if setshowInc == 'true':
            showInc = True
            resString += 'Set <i>showInc</i> to: ' + str(showInc)
        elif setshowInc == 'false':
            showInc = False
            resString += 'Set <i>showInc</i> to: ' + str(showInc)
        setNumStudents = request.args.get('students')
        if setNumStudents:
            numStudents = int(setNumStudents)
            resString += 'Set <i>numStudents</i> to: ' + str(numStudents)
        setMode = request.args.get('mode')
        if setMode:
            if setMode in modes:
                ipList = {}
                mode = setMode
                resString += 'Set <i>mode</i> to: ' + setMode
            else:
                resString += 'No mode called ' + setMode
        if resString == '':
            return render_template("settings.html")
        else:
            pygame.mixer.Sound(sfx["pickup01"]).play()
            resString += "<br>" + backButton
            return resString

@app.route('/quiz')
def endpoint_quiz():
    if not mode == 'quiz':
        return "Not in Quiz mode <br>" + backButton
    global quizCorrect
    answer = request.args.get('answer')
    if answer:
        answer = int(answer)
        if request.remote_addr not in ipList:
            if answer == quizCorrect:
                ipList[request.remote_addr] = 'up'
            else:
                ipList[request.remote_addr] = 'down'
            fillBar()
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
    if not mode == 'survey':
        return "Not in Survey mode <br>" + backButton
    global numStudents
    ip = request.remote_addr
    vote = request.args.get('vote')
    name = request.args.get('name')
    if not name:
        name = 'unknown'
    elif vote:
        print("Recieved " + vote + " from " + name + " at " + ip)
        pygame.mixer.Sound(sfx["blip01"]).play()
    #if mode != 'survey':
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
    global numStudents
    ip = request.remote_addr
    thumb = request.args.get('thumb')
    name = request.args.get('name')
    if not name:
        name = "unknown"
    if thumb:
        if not mode == 'thumbs':
            return "Not in Thumbs mode <br>" + backButton
        else:
            print("Recieved " + thumb + " from " + name + " at ip: " + ip)
            pygame.mixer.Sound(sfx["blip01"]).play()
            if thumb == 'up' or thumb == 'down' or thumb == 'wiggle' :
                ipList[request.remote_addr] = request.args.get('thumb')
                fillBar()
                return "Thank you for your tasty bytes... (" + thumb + ")<br>" + backButton
            elif thumb == 'oops':
                ipList.pop(ip)
                pygame.mixer.Sound(sfx["hit01"]).play()
                fillBar()
                return "I won\'t mention it if you don\'t<br>" + backButton
            else:
                return "Bad Arguments<br><br>Try <b>/tutd?thumb=wiggle</b><br><br>You can also try <b>down</b> and <b>up</b> instead of <b>wiggle</b>"
    else:
        return render_template("thumbsrental.html")

@app.route('/help', methods = ['POST', 'GET'])
def endpoint_help():
    #if not mode == 'help':
    #    return "Not in Help mode <br>" + backButton
    if request.method == 'POST':
        name = request.form['name']
        problem = request.form['problem']
        if name:
            name = name.replace("%20", "")
            name = name.replace(" ", "")
            helpList[name] = problem
            pygame.mixer.Sound(sfx["up04"]).play()
            return "Your ticket was sent. Keep working on the problem the best you can while you wait.<br>" + backButton
        else:
            return "I at least need your name so I know who to help"
    else:
        return render_template("help.html")

@app.route('/needshelp')
def endpoint_needshelp():
    #if not mode == 'help':
    #    return "Not in Help mode <br>" + backButton
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
    return render_template("chat.html")

@app.route('/emptyblocks')
def endpoint_emptyblocks():
    if not mode == 'blockchest':
        return "Not in blockchest mode <br>" + backButton
    global blockList
    blockList = []
    pixels.fill((0,0,0))
    pixels.show()
    return "Emptied blocks"

@app.route('/sendblock')
def endpoint_sendblock():
    if not mode == 'blockchest':
        return "Not in blockchest mode <br>" + backButton
    global blockList
    global colorDict
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

@app.route('/getpix')
def endpoint_getpix():
    return '{"pixels": "'+ str(pixels) +'"}'

@app.route('/virtualbar')
def endpoint_virtualbar():
    return render_template("virtualbar.html")

@app.route('/sfx')
def endpoint_sfx():
    if not mode == 'playtime':
        return "Not in play mode <br>" + backButton
    global locked
    if locked == True:
        if not request.remote_addr in whiteList:
            return "Sound effects are locked"
    sfx_file = request.args.get('file')
    if sfx_file in sfx:
        pygame.mixer.Sound(sfx[sfx_file]).play()
        return 'Playing: ' + sfx_file + backButton
    else:
        resString = '<h2>List of available sound files:</h2><ul>'
        for key, value in sfx.items() :
            resString += '<li><a href="/sfx?file=' + key + '">' + key + '</a></li>'
        resString += '</ul> You can play them by using \'/sfx?file=<b>&lt;sound file name&gt;</b>\'' + backButton
        return resString

@app.route('/perc')
def endpoint_perc():
    if not mode == 'playtime':
        return "Not in play mode <br>" + backButton
    global locked
    if locked == True:
        if not request.remote_addr in whiteList:
            return "Percent mode is locked"
    percAmount = request.args.get('amount')
    try:
        percAmount = float(percAmount)
        percFill(percAmount)
        global perc
        perc = percAmount
    except:
        return "<b>amount</b> must be a decimal place between 0 and 1. \'/perc?amount=<b>0.5</b>\'<br>" + backButton
    return "Set perecentage to: " + str(percAmount) + "<br>" + backButton

@app.route('/say')
def endpoint_say():
    if not mode == 'playtime':
        return "Not in play mode <br>" + backButton
    global locked
    if locked == True:
        if not request.remote_addr in whiteList:
            return "Say mode is locked"
    phrase = request.args.get('phrase')
    fgColor = request.args.get('fg')
    bgColor = request.args.get('bg')
    clearString()
    if phrase:
        if not bgColor or bgColor not in colors:
            bgColor = colors['bg']
        else:
            bgColor = ((colors[bgColor][0] / 8), (colors[bgColor][1] / 8), (colors[bgColor][2] / 8))
        if fgColor and fgColor in colors:
            showString(phrase, 0, colors[fgColor], bgColor)
        else:
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
pygame.mixer.Sound(sfx["bootup02"]).play()

if __name__ == '__main__':
    app.run(host='0.0.0.0', use_reloader=False, debug = False)
