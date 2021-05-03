class Session():
    def __init__(self):
        self.currentStep = 0
        self.wawdLink = '/'
        self.agendaStep = 0
        self.currentEssay = 0
        self.currentProgress = 0
        self.currentQuiz = 0
        self.stepResults = []
        self.lesson = {}
        self.lessonList = {}
        self.bgm = {
            'nowplaying': '',
            'lastTime': 0,
            'lastPlayer': '',
            'list': {}
        }
