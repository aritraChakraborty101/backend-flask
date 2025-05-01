import os
import stripe
from flask import Flask
from dotenv import load_dotenv
from propelauth_flask import init_auth
from flask_cors import CORS
from flask_socketio import SocketIO
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Initialize Supabase client
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# Enable CORS
CORS(app, resources={r"/*": {"origins": "*"}})

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize PropelAuth
auth = init_auth(os.getenv("PROPELAUTH_AUTH_URL"), os.getenv("PROPELAUTH_API_KEY"))

# Stripe API Key
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Route Blueprints
from routes.user_routes import create_user_routes
from routes.org_routes import create_org_routes
from routes.note_routes import create_note_routes
from routes.course_routes import create_course_routes
from routes.message_routes import create_message_routes
from routes.search_routes import create_search_routes
from routes.payment_routes import payment_bp

# Register Blueprints
app.register_blueprint(create_user_routes(auth, supabase), url_prefix="/users")
app.register_blueprint(create_org_routes(auth), url_prefix="/orgs")
app.register_blueprint(create_note_routes(auth, supabase), url_prefix="/notes")
app.register_blueprint(create_course_routes(auth, supabase), url_prefix="/courses")
app.register_blueprint(create_message_routes(auth, supabase), url_prefix="/messages")
app.register_blueprint(create_search_routes(auth, supabase), url_prefix="/search")
app.register_blueprint(payment_bp, url_prefix="/payment")

if not stripe.api_key:
    raise RuntimeError("Stripe secret key not set. Check your .env file!")

if __name__ == "__main__":
    app.run(port=3001)