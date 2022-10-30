class Session():
    def __init__(self, ip='0.0.0.0'):
        self.refresh()
        self.ip = ip
        self.studentDict = {}
        self.mainPage = '/home'
        self.pollType = ''
        self.pollPrompt = ''
        self.pollID = 1
        self.bgm = {
            'nowplaying': '',
            'lastTime': 0,
            'lastPlayer': '',
            'list': {},
            'volume': 0.5,
            'paused': False
        }
        self.ttt = []
        self.fighter = {}
        self.settings = {
            # If you change the default values here, you'll need to update the database too
            'perms': {
                'admin': 0,
                'users': 1,
                'api': 3,
                'sfx': 1,
                'bgm': 1,
                'say': 2,
                'bar': 1,
                'games': 2,
                'teacher': 0,
                'mod': 1,
                'student': 2,
                'anyone': 3,
                'banned': 4
            },
            'permname': ['Teacher', 'Mod', 'Student', 'Guest', 'Banned'],
            'locked': False,
            'paused': False,
            'blind': False,
            'showinc': True,
            'captions': True,
            'autocount': True,
            'numStudents': 8,
            'upcolor': 'green',
            'wigglecolor': 'blue',
            'downcolor': 'red',
            'barmode': 'playtime',
            'modes': ['poll', 'tutd', 'abcd', 'text', 'quiz', 'essay', 'progress', 'playtime', 'sendblock'],
            'whitelist': [
                '127.0.0.1',
                '172.21.3.5'
            ]
        }

    def refresh(self):
        self.currentStep = 0
        self.wawdLink = ''
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
        self.help = False
        self.breakReq = False
        self.thumb = ''
        self.letter = ''
        self.textRes = ''
        self.progress = []
        self.perms = 2
        self.quizResults = {}
        self.preferredHomepage = None


class TTTGame():
    def __init__(self, players):
        self.players = players
        self.turn = 1
        self.gameboard = [
            [None, None, None],
            [None, None, None],
            [None, None, None]
        ]
