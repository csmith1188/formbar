import pandas

book = pandas.ExcelFile('../lessondata/Book1.xlsx')
lesson = book.parse('Quiz_1').to_dict()


def readSheet():
    lessonData = {
        bellringer: {},
        exitticket: {},
        progressList: [],
        quizList: []
    }
    for sheet in book.sheet_names:
        if sheet[0:5] == 'Quiz_':
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
            lessonData.quizList.append(quiz)
            print(quiz)
    return lessonData.quizList

def consoleQuiz():
    for quiz in lessonData.quizList:
        for i, question in enumerate(quiz['questions']):
            print(question)
            for j, answer in enumerate(quiz['answers'][i]):
                print(j + 1, ": ", answer)
            userAnswer = input('What is? ')
            if int(userAnswer) == quiz['keys'][i]:
                print('Correct!')
            else:
                print('haha dumb!')
