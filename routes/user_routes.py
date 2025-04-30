from flask import Blueprint, request, jsonify
from propelauth_flask import current_user
# from models import db, User, RoleRequest, UserReport

def create_user_routes(auth, supabase):
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

            # Check if user exists in Supabase
            response = supabase.table("user").select("*").eq("propel_user_id", propel_user_id).execute()
            user = response.data

            if not user:
                print("User not found in Supabase. Creating new user...")
                supabase.table("user").insert({
                    "propel_user_id": propel_user_id,
                    "email": email,
                    "name": name,
                    "role": "General"
                }).execute()
                print("User created successfully.")
            else:
                print("User already exists in Supabase.")

            # Update role if the user is an admin
            if email == "aritra.chakraborty@g.bracu.ac.bd" and user[0]["role"] != "Admin":
                supabase.table("user").update({"role": "Admin"}).eq("propel_user_id", propel_user_id).execute()
                print("User role updated to Admin.")

            return jsonify({"message": "User synced successfully"}), 200
        except Exception as e:
            print(f"Error in /users/sync: {e}")
            return jsonify({"error": "Internal Server Error"}), 500

    @bp.route("/info", methods=["GET"])
    @auth.require_user
    def user_info():
        try:
            propel_user_id = current_user.user_id

            # Fetch user info from Supabase
            response = supabase.table("user").select("*").eq("propel_user_id", propel_user_id).execute()
            user = response.data

            if not user:
                return jsonify({"error": "User not found"}), 404

            user = user[0]  # Supabase returns a list of results
            return jsonify({
                "name": user["name"],
                "email": user["email"],
                "role": user["role"],
                "courses_enrolled": user["courses_enrolled"],
                "contributions": user["contributions"]
            }), 200
        except Exception as e:
            print(f"Error in /users/info: {e}")
            return jsonify({"error": "Internal Server Error"}), 500
    
    @bp.route("/request_role", methods=["POST"])
    @auth.require_user
    def request_role():
        try:
            data = request.get_json()
            requested_role = data.get("requested_role")
            user_id = current_user.user_id

            # Check if a request already exists
            response = supabase.table("role_request").select("*").eq("user_id", user_id).eq("status", "pending").execute()
            existing_request = response.data

            if existing_request:
                return jsonify({"error": "You already have a pending role request"}), 400

            # Create a new role request
            supabase.table("role_request").insert({
                "user_id": user_id,
                "requested_role": requested_role,
                "status": "pending"
            }).execute()

            return jsonify({"message": "Role request submitted successfully"}), 200
        except Exception as e:
            print(f"Error in /request_role: {e}")
            return jsonify({"error": "Internal Server Error"}), 500


    @bp.route("/role_requests", methods=["GET"])
    @auth.require_user
    def get_role_requests():
        try:
            # Fetch the user's role from Supabase
            response = supabase.table("user").select("role").eq("propel_user_id", current_user.user_id).execute()
            user = response.data

            if not user:
                return jsonify({"error": "User not found"}), 404

            user_role = user[0]["role"]

            # Ensure the user is a Moderator or Admin
            if user_role not in ["Moderator", "Admin"]:
                return jsonify({"error": "Unauthorized"}), 403

            # Get all pending role requests
            response = supabase.table("role_request").select("*").eq("status", "pending").execute()
            role_requests = response.data

            return jsonify(role_requests), 200
        except Exception as e:
            print(f"Error in /role_requests: {e}")
            return jsonify({"error": "Internal Server Error"}), 500


    @bp.route("/role_requests/<int:request_id>", methods=["PATCH"])
    @auth.require_user
    def update_role_request(request_id):
        try:
            # Fetch the user's role from Supabase
            response = supabase.table("user").select("role").eq("propel_user_id", current_user.user_id).execute()
            user = response.data

            if not user:
                return jsonify({"error": "User not found"}), 404

            user_role = user[0]["role"]

            # Ensure the user is a Moderator or Admin
            if user_role not in ["Moderator", "Admin"]:
                return jsonify({"error": "Unauthorized"}), 403

            # Get the role request
            response = supabase.table("role_request").select("*").eq("id", request_id).execute()
            role_request = response.data

            if not role_request:
                return jsonify({"error": "Role request not found"}), 404

            # Update the role request status
            data = request.get_json()
            status = data.get("status")
            if status not in ["approved", "rejected"]:
                return jsonify({"error": "Invalid status"}), 400

            # Update the role request in Supabase
            supabase.table("role_request").update({"status": status}).eq("id", request_id).execute()

            if status == "approved":
                # Fetch the user to update their role
                user_id_to_update = role_request[0]["user_id"]
                supabase.table("user").update({"role": role_request[0]["requested_role"]}).eq("propel_user_id", user_id_to_update).execute()

            return jsonify({"message": f"Role request {status} successfully"}), 200
        except Exception as e:
            print(f"Error in update_role_request: {e}")
            return jsonify({"error": "Internal Server Error"}), 500
    

    # @bp.route("/users/<int:user_id>/ban", methods=["PATCH"])
    # @auth.require_user
    # def ban_user(user_id):
    #     # Fetch the current user's role from the database
    #     user = User.query.filter_by(propel_user_id=current_user.user_id).first()
    #     if not user:
    #         return jsonify({"error": "User not found"}), 404

    #     # Ensure the user is a Moderator or Admin
    #     if user.role not in ["Moderator", "Admin"]:
    #         return jsonify({"error": "Unauthorized"}), 403

    #     user_to_ban = User.query.get(user_id)
    #     if not user_to_ban:
    #         return jsonify({"error": "User not found"}), 404

    #     user_to_ban.is_banned = True
    #     db.session.commit()
    #     return jsonify({"message": "User banned successfully"}), 200
    

    @bp.route("/all_users", methods=["GET"])
    def get_all_users():
        try:
            # Fetch all users from Supabase
            response = supabase.table("user").select("propel_user_id, name, email").execute()
            users = response.data

            if not users:
                return jsonify({"error": "No users found"}), 404

            return jsonify(users), 200
        except Exception as e:
            print(f"Error fetching all users: {e}")
            return jsonify({"error": "Internal Server Error"}), 500
        
    
    @bp.route("/public_profile/<string:propel_user_id>", methods=["GET"])
    def get_public_profile(propel_user_id):
        try:
            # Fetch the user by their PropelAuth user ID
            response = supabase.table("user").select("name, email, contributions").eq("propel_user_id", propel_user_id).execute()
            user = response.data

            if not user:
                return jsonify({"error": "User not found"}), 404

            return jsonify(user[0]), 200
        except Exception as e:
            print(f"Error fetching public profile: {e}")
            return jsonify({"error": "Internal Server Error"}), 500
        
    
    @bp.route("/report_user", methods=["POST"])
    @auth.require_user
    def report_user():
        try:
            data = request.get_json()
            reported_user_id = data.get("reported_user_id")
            reporter_user_id = current_user.user_id  # Get reporter ID from the current user
            issue = data.get("issue")

            if not reported_user_id or not issue:
                return jsonify({"error": "Reported user ID and issue are required"}), 400

            # Check if the reported and reporter users exist in Supabase
            reported_user = supabase.table("user").select("*").eq("propel_user_id", reported_user_id).execute().data
            reporter_user = supabase.table("user").select("*").eq("propel_user_id", reporter_user_id).execute().data

            if not reported_user or not reporter_user:
                return jsonify({"error": "Invalid user IDs"}), 404

            # Create a new report in Supabase
            supabase.table("user_report").insert({
                "reported_user_id": reported_user_id,
                "reporter_user_id": reporter_user_id,
                "issue": issue,
                "status": "pending"
            }).execute()

            return jsonify({"message": "Report submitted successfully!"}), 201
        except Exception as e:
            print(f"Error reporting user: {e}")
            return jsonify({"error": "Internal Server Error"}), 500


    @bp.route("/reports", methods=["GET"])
    @auth.require_user
    def get_reports():
        try:
            # Fetch all reports from Supabase
            response = supabase.table("user_report").select("*").execute()
            reports = response.data

            if not reports:
                return jsonify({"error": "No reports found"}), 404

            # Fetch user details for each report
            report_list = []
            for report in reports:
                reported_user = supabase.table("user").select("name").eq("propel_user_id", report["reported_user_id"]).execute().data
                reporter_user = supabase.table("user").select("name").eq("propel_user_id", report["reporter_user_id"]).execute().data

                if report["status"] != "pending":
                    continue
                report_list.append({
                    "id": report["id"],
                    "reported_user": reported_user[0]["name"] if reported_user else "Unknown",
                    "reporter_user": reporter_user[0]["name"] if reporter_user else "Unknown",
                    "issue": report["issue"],
                    "status": report["status"],
                    "created_at": report["created_at"]
                })

            return jsonify(report_list), 200
        except Exception as e:
            print(f"Error fetching reports: {e}")
            return jsonify({"error": "Internal Server Error"}), 500


    @bp.route("/resolve_report/<int:report_id>", methods=["PATCH"])
    @auth.require_user
    def resolve_report(report_id):
        try:
            data = request.get_json()
            action = data.get("action")  # "ban" or "reject"

            # Fetch the report from Supabase
            response = supabase.table("user_report").select("*").eq("id", report_id).execute()
            report = response.data

            if not report:
                return jsonify({"error": "Report not found"}), 404

            report = report[0]  # Supabase returns a list of results

            if action == "ban":
                # Ban the reported user
                supabase.table("user").update({"is_banned": True}).eq("propel_user_id", report["reported_user_id"]).execute()
                supabase.table("user_report").update({"status": "resolved"}).eq("id", report_id).execute()
            elif action == "reject":
                # Reject the report
                supabase.table("user_report").update({"status": "rejected"}).eq("id", report_id).execute()
            else:
                return jsonify({"error": "Invalid action"}), 400

            return jsonify({"message": "Report resolved successfully!"}), 200
        except Exception as e:
            print(f"Error resolving report: {e}")
            return jsonify({"error": "Internal Server Error"}), 500
    

    @bp.route("/get_role", methods=["GET"])
    @auth.require_user
    def get_role():
        try:
            propel_user_id = current_user.user_id

            # Fetch user role from Supabase
            response = supabase.table("user").select("role").eq("propel_user_id", propel_user_id).execute()
            user = response.data

            if not user:
                return jsonify({"error": "User not found"}), 404

            return jsonify({"role": user[0]["role"]}), 200
        except Exception as e:
            print(f"Error in /users/get_role: {e}")
            return jsonify({"error": "Internal Server Error"}), 500

    return bp