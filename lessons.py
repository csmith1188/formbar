import pandas
import os

def readFolder():
    lessonList = []
    #Scan folder for all filenames
    availableFiles = os.listdir("./lessondata")
    #Loop through each file
    for file in sorted(availableFiles):
        #Check last four letters are the correct file extension
        if file[-5:].lower() == '.xlsx':
            lessonList.append(readBook(pandas.ExcelFile('lessondata/' + file)))
    return lessonList

def readBook(book):
    # newLesson = newBook.parse('Quiz_1').to_dict()
    lessonData = {
        'bellringer': {},
        'exitticket': {},
        'progressList': [],
        'quizList': []
    }
    for sheet in book.sheet_names:
        if sheet[0:5] == 'Quiz_':
            lesson = book.parse(sheet).to_dict()
            quiz = {'questions':[], 'keys': [], 'answers': []}
            for row in range(0, len(lesson['Question'])):
                answers = []
                for i, col in enumerate(lesson):
                    if i == 0:
                        quiz['questions'].append(lesson[col][row])
                    if i == 1:
                        quiz['keys'].append(lesson[col][row])
                    elif i > 1:
                        answers.append(lesson[col][row])
                quiz['answers'].append(answers)
            lessonData['quizList'].append(quiz)
    return lessonData

# def consoleQuiz():
#     for quiz in lessonData['quizList']:
#         for i, question in enumerate(quiz['questions']):
#             print(question)
#             for j, answer in enumerate(quiz['answers'][i]):
#                 print(j + 1, ": ", answer)
#             userAnswer = input('What is? ')
#             if int(userAnswer) == quiz['keys'][i]:
#                 print('Correct!')
#             else:
#                 print('haha dumb!')

print(readFolder())
