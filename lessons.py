import pandas#Imports pandas.
import os#Imports operating system.

class Lesson():
    def __init__(self):
        pass
    agenda = []
    objective = []
    links = []
    quizList = {}
    progList = {}

    # lessonModel = {
    #     'agenda': [{'time': 0, 'title': '', 'desc': '', 'step': 0}],
    #     'objectives': [{'objective': '', 'desc': ''}],
    #     'links': [{'url': '', 'desc': ''}],
    #     'quizzes': {'Quiz_1': {'name': '', 'questions':[], 'keys': [], 'answers': []}},
    #     'progLists': {'Progress_1': {'name': '', 'task':[], 'desc': []}}
    # }

lessons = {}

def updateFiles():
    global lessons
    #Empty lessons file list
    lessons = {}
    #Scan folder for all filenames
    availableFiles = os.listdir("./lessondata")
    #Loop through each file
    for file in sorted(availableFiles):
        #Check last five letters are the correct file extension
        if file[-5:] == '.xlsx':
            #Add them to the lessonsFiles list if so
            lessons[file[:-5]] = "/home/pi/formbar/lessondata/" + file

def readBook(incBook):
    newBook = 'lessondata/' + incBook + '.xlsx'
    book = pandas.ExcelFile(newBook)
    lessonData = Lesson()
    for sheet in book.sheet_names:
        if sheet == 'Agenda':
            data = book.parse(sheet).to_dict()
            agenda = []
            for i, col in enumerate(data):
                if len(agenda) <= i:
                    agenda.append({})
                agenda[i][col] = data[col]
            print(data)
        elif sheet == 'Steps':
            data = book.parse(sheet).to_dict()
            print(data)
        elif sheet == 'Objectives':
            data = book.parse(sheet).to_dict()
            print(data)
        elif sheet == 'Resources':
            data = book.parse(sheet).to_dict()
            print(data)
        elif sheet[0:5] == 'Quiz_':
            data = book.parse(sheet).to_dict()
            quiz = {'name': sheet[5:], 'questions':[], 'keys': [], 'answers': []}
            for row in range(0, len(data['Question'])):
                answers = []
                for i, col in enumerate(data):
                    if i == 0:
                        quiz['questions'].append(data[col][row])
                    if i == 1:
                        quiz['keys'].append(data[col][row])
                    elif i > 1:
                        answers.append(data[col][row])
                quiz['answers'].append(answers)
            lessonData.quizList[sheet] = quiz
            print(lessonData.quizList[sheet])

        elif sheet[0:9] == 'Progress_':
            data = book.parse(sheet).to_dict()
            progress = {'name': sheet[9:], 'task':[], 'desc': []}
            for task in data['Task']:
                progress['task'].append(data['Task'][task])
            for desc in data['Description']:
                progress['desc'].append(data['Description'][desc])
            lessonData.progList[sheet] = progress
            print(lessonData.progList[sheet])

    return lessonData
