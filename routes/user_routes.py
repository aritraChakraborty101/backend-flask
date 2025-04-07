from flask import Blueprint, request, jsonify
from propelauth_flask import current_user
from models import db, User, RoleRequest

def create_user_routes(auth):
    bp = Blueprint("user_routes", __name__)

    @bp.route("/sync", methods=["POST"])
    def sync_user():
        try:
            print("Received request to /users/sync")
            data = request.get_json()
            propel_user_id = data.get("userId")
            email = data.get("email")
            name = data.get("name")
            print(f"Extracted user info: ID={propel_user_id}, Email={email}, Name={name}")

            # Check if user exists
            user = User.query.filter_by(propel_user_id=propel_user_id).first()
            if not user:
                print("User not found in database. Creating new user...")
                user = User(propel_user_id=propel_user_id, email=email, name=name)
                db.session.add(user)
                db.session.commit()
                print("User created successfully.")

            return jsonify({"message": "User synced successfully", "user": {"id": user.id, "name": user.name, "email": user.email, "role": user.role}})
        except Exception as e:
            print(f"Error in /users/sync: {e}")
            return jsonify({"error": "Internal Server Error"}), 500
        
    @bp.route("/info", methods=["GET"])
    @auth.require_user
    def user_info():
        """Display user information"""
        propel_user_id = current_user.user_id
        user = User.query.filter_by(propel_user_id=propel_user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        return jsonify({
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "courses_enrolled": user.courses_enrolled,
            "contributions": user.contributions
        })

    @bp.route("/request_role", methods=["POST"])
    @auth.require_user
    def request_role():
        """Request a higher-level role"""
        propel_user_id = current_user.user_id
        user = User.query.filter_by(propel_user_id=propel_user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        data = request.get_json()
        requested_role = data.get("requested_role")
        if not requested_role:
            return jsonify({"error": "Requested role is required"}), 400

        role_request = RoleRequest(user_id=user.id, requested_role=requested_role)
        db.session.add(role_request)
        db.session.commit()

        return jsonify({"message": "Role request submitted successfully"})

    return bp