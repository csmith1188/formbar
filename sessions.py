class Session():
    def __init__(self, ip='0.0.0.0'):
        self.refresh()
        self.ip = ip
        self.studentDict = {}
        self.bgm = {
            'nowplaying': '',
            'lastTime': 0,
            'lastPlayer': '',
            'list': {},
            'volume': 0.5,
            'paused': False
        }
        self.ttt = []
        self.settings = {
            'perms': {
                'admin' : 0,
                'users' : 1,
                'api' : 3,
                'sfx' : 1,
                'bgm' : 1,
                'say' : 1,
                'bar' : 1,
                'games': 2,
                'teacher': 0,
                'mod': 1,
                'student': 2,
                'anyone': 3,
                'banned': 4
            },
            'locked' : False,
            'paused' : False,
            'blind' : False,
            'showinc' : True,
            'captions' : True,
            'autocount' : True,
            'numStudents': 8,
            'upcolor': 'green',
            'wigglecolor': 'blue',
            'downcolor': 'red',
            'barmode': 'tutd',
            'modes': ['tutd', 'survey', 'quiz', 'essay', 'progress', 'playtime'],
            'whitelist': [
                '127.0.0.1',
                '172.21.3.5'
                ]
        }

    def refresh(self):
        self.currentStep = 0
        self.wawdLink = '/'
        self.agendaStep = 0
        self.activePhrase = ''
        self.activePrompt = ''
        self.activeCompleted = ''
        self.activeBar = []
        self.activeProgress = {}
        self.activeQuiz = {}
        self.lesson = {}
        self.lessonList = {}

class Student():
    def __init__(self, username):
        self.name = username
        self.thumb = ''
        self.survey = ''
        self.progress = []
        self.perms = 2
        self.quizResults = {}


class TTTGame():
    def __init__(self, players):
        self.players = players
