import os
from flask import Flask
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from propelauth_flask import init_auth
from flask_migrate import Migrate
from flask_cors import CORS
from flask_socketio import SocketIO

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Enable CORS
CORS(app, resources={r"/*": {"origins": "*"}})

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize database
db = SQLAlchemy(app)

# Initialize Flask-Migrate
migrate = Migrate(app, db)

# Initialize PropelAuth
auth = init_auth(os.getenv("PROPELAUTH_AUTH_URL"), os.getenv("PROPELAUTH_API_KEY"))


# Access the path of uploading files
creds_path = os.getenv("GOOGLE_DRIVE_CREDENTIALS_PATH")

# Route Blueprints
from routes.user_routes import create_user_routes
from routes.org_routes import create_org_routes
from routes.note_routes import create_note_routes
from routes.course_routes import create_course_routes
from routes.message_routes import create_message_routes
from routes.connection_routes import create_connection_routes
# Register Blueprints
app.register_blueprint(create_user_routes(auth), url_prefix="/users")
app.register_blueprint(create_org_routes(auth), url_prefix="/orgs")
app.register_blueprint(create_note_routes(auth), url_prefix="/notes")  # Pass auth here
app.register_blueprint(create_course_routes(auth), url_prefix="/courses")
app.register_blueprint(create_message_routes(auth), url_prefix="/messages")  # Pass auth here
app.register_blueprint(create_connection_routes(auth), url_prefix="/connections")
# Run the app
if __name__ == "__main__":
    app.run(port=3001)