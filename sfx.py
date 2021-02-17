import os

sound = {}

def updateFiles():
    global sound
    #Empty sound file list
    sound = {}
    #Scan folder for all filenames
    availableFiles = os.listdir("./sfx")
    #Loop through each file
    for file in sorted(availableFiles):
        #Check last four letters are the correct file extension
        if file[-4:] == '.wav' or file[-4:] == '.mp3':
            #Add them to the soundFiles list if so
            sound[file[:-4]] = "/home/pi/formbar/sfx/" + file
    #Loop through all of the found files


#OLD SOUND FILES LIST
'''
sound = {
    "up01": "/home/pi/formbar/sfx/up01.wav",
    "up02": "/home/pi/formbar/sfx/up02.wav",
    "up03": "/home/pi/formbar/sfx/up03.wav",
    "up04": "/home/pi/formbar/sfx/up04.wav",
    "blip01": "/home/pi/formbar/sfx/blip01.wav",
    "dodge01": "/home/pi/formbar/sfx/dodge01.wav",
    "explode01": "/home/pi/formbar/sfx/explode01.wav",
    "hit01": "/home/pi/formbar/sfx/hit01.wav",
    "laser01": "/home/pi/formbar/sfx/laser01.wav",
    "pickup01": "/home/pi/formbar/sfx/pickup01.wav",
    "pickup02": "/home/pi/formbar/sfx/pickup02.wav",
    "shoot01": "/home/pi/formbar/sfx/shoot01.wav",
    "splash01": "/home/pi/formbar/sfx/splash01.wav",
    "success01": "/home/pi/formbar/sfx/success01.wav",
    "bootup02": "/home/pi/formbar/sfx/bootup02.wav",
    "powerup02": "/home/pi/formbar/sfx/powerup02.wav"
}
'''
