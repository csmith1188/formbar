import os#Imports operating system.

bgm = {}

def updateFiles():
    global bgm
    #Empty bgm file list
    bgm = {}
    #Scan folder for all filenames
    availableFiles = os.listdir("./bgm")
    #Loop through each file
    for file in sorted(availableFiles):
        #Check last four letters are the correct file extension
        if file[-4:] == '.wav' or file[-4:] == '.mp3':
            #Add them to the bgmFiles list if so
            bgm[file[:-4]] = "/home/pi/formbar/bgm/" + file
