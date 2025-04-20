import os
from flask import Flask
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from propelauth_flask import init_auth, current_user
from flask_migrate import Migrate
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room


# Load environment
load_dotenv()


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


# CORS
CORS(app,
    resources={r"/*": {"origins": "http://localhost:3000",
                       "supports_credentials": True}},
    supports_credentials=True)


# DB + migrations
db = SQLAlchemy(app)
migrate = Migrate(app, db)


# PropelAuth
auth = init_auth(os.getenv("PROPELAUTH_AUTH_URL"), os.getenv("PROPELAUTH_API_KEY"))


# Socket.IO
socketio = SocketIO(app,
                   cors_allowed_origins=["http://localhost:3000"],
                   async_mode='eventlet')


# Register blueprints
from routes.user_routes    import create_user_routes
from routes.org_routes     import create_org_routes
from routes.note_routes    import create_note_routes
from routes.course_routes  import create_course_routes
from routes.message_routes import create_message_routes


app.register_blueprint(create_user_routes(auth),    url_prefix="/users")
app.register_blueprint(create_org_routes(auth),     url_prefix="/orgs")
app.register_blueprint(create_note_routes(auth),    url_prefix="/notes")
app.register_blueprint(create_course_routes(auth),  url_prefix="/courses")
app.register_blueprint(create_message_routes(auth), url_prefix="/messages")


# --- Socket.IO handlers ---
@socketio.on('connect')
def on_connect():
   if current_user.is_authenticated:
       join_room(current_user.user_id)
       print(f"User {current_user.user_id} connected")


@socketio.on('join_conversation')
def on_join(data):
   room = str(data.get('convo_id'))
   if room:
       join_room(room)
       print(f"User {current_user.user_id} joined room {room}")


@socketio.on('disconnect')
def on_disconnect():
   uid = current_user.user_id if current_user.is_authenticated else 'Anonymous'
   print(f"User {uid} disconnected")


if __name__ == '__main__':
   socketio.run(app, host='0.0.0.0', port=3001, debug=True)