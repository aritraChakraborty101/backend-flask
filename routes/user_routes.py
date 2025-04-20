from flask import Blueprint, request, jsonify
from propelauth_flask import current_user
from models import db, User, RoleRequest, UserReport


def create_user_routes(auth):
   bp = Blueprint("user_routes", __name__)


   @bp.route("/sync", methods=["POST"])
   def sync_user():
       """Called on login/signup to ensure our DB has this user."""
       data = request.get_json() or {}
       pid   = data.get("userId")
       email = data.get("email")
       name  = data.get("name")


       if not pid or not email:
           return jsonify({"error": "Missing userId or email"}), 400


       user = User.query.filter_by(propel_user_id=pid).first()
       if not user:
           user = User(propel_user_id=pid, email=email, name=name)
           db.session.add(user)
           db.session.commit()


       return jsonify({
           "message": "User synced successfully",
           "user": {
               "id":   user.id,
               "name": user.name,
               "email": user.email,
               "role": user.role
           }
       }), 200


   @bp.route("/info", methods=["GET"])
   @auth.require_user
   def user_info():
       """Returns the logged‑in user’s private info."""
       me = User.query.filter_by(propel_user_id=current_user.user_id).first_or_404()
       return jsonify({
           "name":             me.name,
           "email":            me.email,
           "role":             me.role,
           "courses_enrolled": me.courses_enrolled,
           "contributions":    me.contributions
       }), 200


   @bp.route("/request_role", methods=["POST"])
   @auth.require_user
   def request_role():
       data = request.get_json() or {}
       req_role = data.get("requested_role")
       me = User.query.filter_by(propel_user_id=current_user.user_id).first_or_404()


       if RoleRequest.query.filter_by(user_id=me.id, status="pending").first():
           return jsonify({"error": "You already have a pending role request"}), 400


       rr = RoleRequest(user_id=me.id, requested_role=req_role)
       db.session.add(rr)
       db.session.commit()
       return jsonify({"message": "Role request submitted successfully"}), 200


   @bp.route("/role_requests", methods=["GET"])
   @auth.require_user
   def get_role_requests():
       me = User.query.filter_by(propel_user_id=current_user.user_id).first_or_404()
       if me.role not in ["Moderator", "Admin"]:
           return jsonify({"error": "Unauthorized"}), 403


       pending = RoleRequest.query.filter_by(status="pending").all()
       return jsonify([
           {
               "id":             r.id,
               "user_id":        r.user_id,
               "requested_role": r.requested_role,
               "status":         r.status
           }
           for r in pending
       ]), 200


   @bp.route("/role_requests/<int:request_id>", methods=["PATCH"])
   @auth.require_user
   def update_role_request(request_id):
       me = User.query.filter_by(propel_user_id=current_user.user_id).first_or_404()
       if me.role not in ["Moderator", "Admin"]:
           return jsonify({"error": "Unauthorized"}), 403


       rr = RoleRequest.query.get_or_404(request_id)
       data = request.get_json() or {}
       status = data.get("status")
       if status not in ["approved", "rejected"]:
           return jsonify({"error": "Invalid status"}), 400


       rr.status = status
       if status == "approved":
           user_to_update = User.query.get_or_404(rr.user_id)
           user_to_update.role = rr.requested_role


       db.session.commit()
       return jsonify({"message": f"Role request {status} successfully"}), 200


   @bp.route("/users/<int:user_id>/ban", methods=["PATCH"])
   @auth.require_user
   def ban_user(user_id):
       me = User.query.filter_by(propel_user_id=current_user.user_id).first_or_404()
       if me.role not in ["Moderator", "Admin"]:
           return jsonify({"error": "Unauthorized"}), 403


       to_ban = User.query.get_or_404(user_id)
       to_ban.is_banned = True
       db.session.commit()
       return jsonify({"message": "User banned successfully"}), 200


   @bp.route("/all_users", methods=["GET"])
   def get_all_users():
       """Used by UserList.jsx"""
       users = User.query.all()
       return jsonify([
           {
               "propel_user_id": u.propel_user_id,
               "name":           u.name,
               "email":          u.email
           }
           for u in users
       ]), 200


   @bp.route("/public_profile/<string:propel_user_id>", methods=["GET"])
   def get_public_profile(propel_user_id):
       """Used by PublicProfile.jsx"""
       u = User.query.filter_by(propel_user_id=propel_user_id).first_or_404()
       return jsonify({
           "name":          u.name,
           "email":         u.email,
           "contributions": u.contributions
       }), 200


   @bp.route("/report_user", methods=["POST"])
   @auth.require_user
   def report_user():
       data = request.get_json() or {}
       reported_pid = data.get("reported_user_id")
       issue = data.get("issue")
       me = User.query.filter_by(propel_user_id=current_user.user_id).first_or_404()
       other = User.query.filter_by(propel_user_id=reported_pid).first_or_404()


       report = UserReport(
           reported_user_id=other.id,
           reporter_user_id=me.id,
           issue=issue
       )
       db.session.add(report)
       db.session.commit()
       return jsonify({"message": "Report submitted successfully!"}), 201


   @bp.route("/reports", methods=["GET"])
   @auth.require_user
   def get_reports():
       me = User.query.filter_by(propel_user_id=current_user.user_id).first_or_404()
       if me.role not in ["Moderator", "Admin"]:
           return jsonify({"error": "Unauthorized"}), 403


       all_reports = UserReport.query.all()
       return jsonify([
           {
               "id":              r.id,
               "reported_user":   User.query.get(r.reported_user_id).name,
               "reporter_user":   User.query.get(r.reporter_user_id).name,
               "issue":           r.issue,
               "status":          r.status,
               "created_at":      r.created_at.isoformat()
           }
           for r in all_reports
       ]), 200


   @bp.route("/resolve_report/<int:report_id>", methods=["PATCH"])
   @auth.require_user
   def resolve_report(report_id):
       data = request.get_json() or {}
       action = data.get("action")  # "ban" or "reject"
       report = UserReport.query.get_or_404(report_id)


       if action == "ban":
           usr = User.query.get_or_404(report.reported_user_id)
           usr.is_banned = True
           report.status = "resolved"
       elif action == "reject":
           report.status = "rejected"
       else:
           return jsonify({"error": "Invalid action"}), 400


       db.session.commit()
       # optionally: db.session.delete(report)
       return jsonify({"message": "Report resolved"}), 200


   @bp.route("/get_role", methods=["GET"])
   @auth.require_user
   def get_role():
       u = User.query.filter_by(propel_user_id=current_user.user_id).first_or_404()
       return jsonify({"role": u.role}), 200


   @bp.route("/update_name", methods=["PATCH"])
   @auth.require_user
   def update_name():
       data = request.get_json() or {}
       new_name = data.get("name")
       if not new_name:
           return jsonify({"error": "Name is required"}), 400


       u = User.query.filter_by(propel_user_id=current_user.user_id).first_or_404()
       u.name = new_name
       db.session.commit()
       return jsonify({"message": "Name updated successfully!"}), 200


   return bp