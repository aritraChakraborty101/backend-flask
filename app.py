import os
from flask import Flask
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from propelauth_flask import init_auth
from flask_migrate import Migrate
from flask_cors import CORS

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'  # Use SQLite for simplicity
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Enable CORS
CORS(app, resources={r"/*": {"origins": "*"}})

# Initialize database
db = SQLAlchemy(app)

# Initialize Flask-Migrate
migrate = Migrate(app, db)

# Initialize PropelAuth
auth = init_auth(os.getenv("PROPELAUTH_AUTH_URL"), os.getenv("PROPELAUTH_API_KEY"))

from routes.user_routes import create_user_routes
from routes.org_routes import create_org_routes

# Register Blueprints
app.register_blueprint(create_user_routes(auth), url_prefix="/users")
app.register_blueprint(create_org_routes(auth), url_prefix="/orgs")

# Run the app
if __name__ == "__main__":
    app.run(port=3001)