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
        data = request.get_json()
        requested_role = data.get("requested_role")
        user_id = current_user.user_id

        # Check if a request already exists
        existing_request = RoleRequest.query.filter_by(user_id=user_id, status="pending").first()
        if existing_request:
            return jsonify({"error": "You already have a pending role request"}), 400

        # Create a new role request
        role_request = RoleRequest(user_id=user_id, requested_role=requested_role)
        db.session.add(role_request)
        db.session.commit()

        return jsonify({"message": "Role request submitted successfully"}), 200
    
    @bp.route("/role_requests", methods=["GET"])
    @auth.require_user
    def get_role_requests():
        try:
            # Fetch the user's role from the database
            user = User.query.filter_by(propel_user_id=current_user.user_id).first()
            print(f"Current User ID: {user.id}")
            if not user:
                print("User not found in the database")
                return jsonify({"error": "User not found"}), 404

            # Ensure the user is a Moderator or Admin
            print(f"Current User Role: {user.role}")
            if user.role not in ["Moderator", "Admin"]:
                print("Unauthorized access attempt")
                return jsonify({"error": "Unauthorized"}), 403

            # Get all pending role requests
            role_requests = RoleRequest.query.filter_by(status="pending").all()
            print(f"Fetched {len(role_requests)} pending role requests")
            return jsonify([{
                "id": req.id,
                "user_id": req.user_id,
                "requested_role": req.requested_role,
                "status": req.status
            } for req in role_requests])
        except Exception as e:
            print(f"Error in /role_requests: {e}")
            return jsonify({"error": "Internal Server Error"}), 500
    

    @bp.route("/role_requests/<int:request_id>", methods=["PATCH"])
    @auth.require_user
    def update_role_request(request_id):
        try:
            # Fetch the user's role from the database
            user = User.query.filter_by(propel_user_id=current_user.user_id).first()
            if not user:
                return jsonify({"error": "User not found"}), 404

            # Ensure the user is a Moderator or Admin
            if user.role not in ["Moderator", "Admin"]:
                return jsonify({"error": "Unauthorized"}), 403

            # Get the role request
            role_request = RoleRequest.query.get(request_id)
            if not role_request:
                return jsonify({"error": "Role request not found"}), 404

            # Update the role request status
            data = request.get_json()
            status = data.get("status")
            if status not in ["approved", "rejected"]:
                return jsonify({"error": "Invalid status"}), 400

            role_request.status = status
            if status == "approved":
                # Fetch the user using the propel_user_id from the role request
                user_to_update = User.query.filter_by(propel_user_id=role_request.user_id).first()
                if not user_to_update:
                    return jsonify({"error": "User to update not found"}), 404

                user_to_update.role = role_request.requested_role
                db.session.commit()

            db.session.commit()
            return jsonify({"message": f"Role request {status} successfully"}), 200
        except Exception as e:
            print(f"Error in update_role_request: {e}")
            return jsonify({"error": "Internal Server Error"}), 500
    

    @bp.route("/users/<int:user_id>/ban", methods=["PATCH"])
    @auth.require_user
    def ban_user(user_id):
        # Fetch the current user's role from the database
        user = User.query.filter_by(propel_user_id=current_user.user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Ensure the user is a Moderator or Admin
        if user.role not in ["Moderator", "Admin"]:
            return jsonify({"error": "Unauthorized"}), 403

        user_to_ban = User.query.get(user_id)
        if not user_to_ban:
            return jsonify({"error": "User not found"}), 404

        user_to_ban.is_banned = True
        db.session.commit()
        return jsonify({"message": "User banned successfully"}), 200


    # @bp.route("/users/<int:user_id>", methods=["DELETE"])
    # @auth.require_user
    # def delete_user(user_id):
    #     if current_user.role != "Admin":
    #         return jsonify({"error": "Unauthorized"}), 403

    #     user = User.query.get(user_id)
    #     if not user:
    #         return jsonify({"error": "User not found"}), 404

    #     db.session.delete(user)
    #     db.session.commit()
    #     return jsonify({"message": "User deleted successfully"}), 200
    

    @bp.route("/get_role", methods=["GET"])
    @auth.require_user
    def get_role():
        user_id = current_user.user_id  # Get the user's ID from PropelAuth
        user = User.query.filter_by(propel_user_id=user_id).first()
        if request.method == "OPTIONS":
            return jsonify({"message": "Preflight response"}), 200
        


        if not user:
            return jsonify({"error": "User not found"}), 404

        return jsonify({"role": user.role}), 200


    return bp