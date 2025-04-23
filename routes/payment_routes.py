from flask import Blueprint, request, jsonify
import stripe, os
from functools import wraps
from models import db, User

payment_bp = Blueprint('payment', __name__)

def require_auth(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Unauthorized"}), 401
        token = auth_header.split(" ")[1]
        expected_token = os.getenv("API_TOKEN", "mysecrettoken")
        if token != expected_token:
            return jsonify({"error": "Invalid token"}), 401
        return func(*args, **kwargs)
    return wrapper

@payment_bp.route('/create-checkout-session', methods=['POST'])
@require_auth
def create_checkout_session():
    try:
        data = request.get_json() or {}
        # For demonstration, we’re using a fixed price product.
        items = data.get("items", [])
        
        # You might map "items" to real Stripe pricing data in a production app
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {'name': 'Premium Access'},
                    'unit_amount': 500,  # Fixed $5.00 price in cents.
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url='http://localhost:3000/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='http://localhost:3000/cancel',
            client_reference_id=data.get("userId")  # Optional: ties session with user.
        )
        # Return the session id in a JSON object.
        return jsonify({'id': session.id})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@payment_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    
    try:
        # This line verifies and constructs the event using the payload, 
        # the signature from Stripe (in the header), and your endpoint secret.
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        # If the payload is invalid, return a 400 error.
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        # If the signature verification fails, then the event did not come from Stripe.
        return jsonify({'error': 'Invalid signature'}), 400

    # Process the event only if it is a completed checkout session.
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        # Retrieves the user ID that was passed as client_reference_id 
        # during session creation on the frontend.
        user_id = session.get("client_reference_id")
        if user_id:
            # Look up the user in your database
            user = User.query.get(user_id)
            if user:
                # Update the user's premium status to True after successful payment.
                user.is_premium = True
                db.session.commit()
    # Return a success message to acknowledge receipt of the webhook.
    return jsonify({'status': 'success'}), 200

