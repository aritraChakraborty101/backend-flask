# from flask import Blueprint, request, jsonify
# from models import db, ConnectionRequest, User
# from propelauth_flask import current_user

# def create_connection_routes(auth):
#     bp = Blueprint('connections', __name__)

#     # Send a connection request
#     @bp.route('/request', methods=['POST'])
#     @auth.require_user
#     def send_connection_request():
#         data = request.get_json()
#         receiver_id = data.get("receiver_id")
#         if not receiver_id:
#             return jsonify({"error": "Receiver ID is required"}), 400

#         # Get the current logged-in user's Propel ID
#         requester_id = current_user.get("user_id")  # Adjust depending on your propelauth current_user format

#         # Check if a request has already been sent
#         existing_request = ConnectionRequest.query.filter_by(requester_id=requester_id, receiver_id=receiver_id).first()
#         if existing_request:
#             return jsonify({"error": "Connection request already sent"}), 400

#         connection_request = ConnectionRequest(requester_id=requester_id, receiver_id=receiver_id)
#         db.session.add(connection_request)
#         db.session.commit()
#         return jsonify({"message": "Connection request sent", "request_id": connection_request.id}), 200

#     # Fetch all received (pending) connection requests for the authenticated user
#     @bp.route('/received', methods=['GET'])
#     @auth.require_user
#     def get_received_requests():
#         user_id = current_user.get("user_id")
#         requests = ConnectionRequest.query.filter_by(receiver_id=user_id, status='pending').all()
#         results = []
#         for req in requests:
#             requester = User.query.filter_by(propel_user_id=req.requester_id).first()
#             results.append({
#                 "request_id": req.id,
#                 "requester_id": req.requester_id,
#                 "requester_name": requester.name if requester else "Unknown",
#                 "status": req.status
#             })
#         return jsonify(results), 200

#     # Fetch all sent connection requests by the authenticated user
#     @bp.route('/sent', methods=['GET'])
#     @auth.require_user
#     def get_sent_requests():
#         user_id = current_user.get("user_id")
#         requests = ConnectionRequest.query.filter_by(requester_id=user_id).all()
#         results = []
#         for req in requests:
#             receiver = User.query.filter_by(propel_user_id=req.receiver_id).first()
#             results.append({
#                 "request_id": req.id,
#                 "receiver_id": req.receiver_id,
#                 "receiver_name": receiver.name if receiver else "Unknown",
#                 "status": req.status
#             })
#         return jsonify(results), 200

#     # Respond to a connection request (accept/reject)
#     @bp.route('/respond', methods=['POST'])
#     @auth.require_user
#     def respond_to_request():
#         data = request.get_json()
#         request_id = data.get("request_id")
#         action = data.get("action")
#         if not request_id or action not in ['accept', 'reject']:
#             return jsonify({"error": "Invalid data"}), 400

#         connection_request = ConnectionRequest.query.get(request_id)
#         if not connection_request:
#             return jsonify({"error": "Connection request not found"}), 404

#         # Only the receiver can respond to the request
#         user_id = current_user.get("user_id")
#         if connection_request.receiver_id != user_id:
#             return jsonify({"error": "Not authorized"}), 403

#         connection_request.status = 'accepted' if action == 'accept' else 'rejected'
#         db.session.commit()
#         return jsonify({"message": f"Connection request {action}ed"}), 200

#     return bp
