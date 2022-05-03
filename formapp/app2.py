from flask import Flask, render_template, session, copy_current_request_context
from flask_socketio import SocketIO, emit, disconnect
from threading import Lock

async_mode = None
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socket_ = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock()

apinamespace = '/apisocket'
chatnamespace = '/chat'

block = {
    'users': [{
        'name': 'ur mum',
        'perm': True
    },
    {
        'name': 'dem mums',
        'perm': True
    }]
}

@app.route('/')
def index():
    return render_template('socket.html', async_mode=socket_.async_mode)

def handle_manage_users():
    pass

@app.route('/manage/users')
def manage_users():
    #Check Permissions here
    return render_template('management/users.html', namespace=apinamespace, async_mode=socket_.async_mode)

@socket_.on('loadUsers', namespace=apinamespace)
def api_loadUsers():
    #Check permissions here
    #Check to see if block is active to select users
    emit( 'api_userList', {'data': block['users'], 'message': ''} )

@socket_.on('changeperm', namespace=apinamespace)
def api_changeperm():
    #Check permissions here
    #Check to see if block is active to select users
    block['users'][0]['perm'] = not block['users'][0]['perm']
    print(block['users'][0]['perm'])
    emit( 'api_userList', {'data': block['users'], 'message': ''} )


@socket_.on('my_event', namespace=chatnamespace)
def chat_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']})

@socket_.on('my_broadcast_event', namespace=chatnamespace)
def chat_broadcast_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']},
         broadcast=True)

@socket_.on('disconnect_request', namespace=chatnamespace)
def disconnect_request():
    @copy_current_request_context
    def can_disconnect():
        disconnect()

    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'Disconnected!', 'count': session['receive_count']},
         callback=can_disconnect)

if __name__ == '__main__':
    socket_.run(app, debug=True)
