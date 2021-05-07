class Session():
    def __init__(self):
        self.currentStep = 0
        self.wawdLink = '/'
        self.agendaStep = 0
        self.activePrompt = ''
        self.activeQuiz = {}
        self.activeProgress = {}
        self.lesson = {}
        self.lessonList = {}
        self.bgm = {
            'nowplaying': '',
            'lastTime': 0,
            'lastPlayer': '',
            'list': {}
        }

class Student():
    def __init__(self, username):
        self.name = username
        self.thumb = ''
        self.survey = ''
        self.progress = []
        self.perms = 2
        self.quizResults = {}
