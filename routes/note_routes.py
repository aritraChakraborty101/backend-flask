from flask import Blueprint, request, jsonify
from models import db, Note, User, NoteReport, NoteVote
from propelauth_flask import current_user
import json

def create_note_routes(auth):  # Add auth parameter here
    bp = Blueprint("note_routes", __name__)

    @bp.route("/upload", methods=["POST"])
    @auth.require_user
    def upload_note():
      try:
        # Get form data
        course_id = request.form.get("course_id")
        title = request.form.get("title")
        tags = request.form.get("tags", "").split(",")
        file = request.files.get("file")

        # Validate required fields
        if not all([course_id, title, file]):
            return jsonify({"error": "Course ID, title, and file are required"}), 400

        # Validate file type
        ALLOWED_TYPES = {'application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}
        if file.mimetype not in ALLOWED_TYPES:
            return jsonify({"error": "Only PDF and DOCX files are allowed"}), 400

        # Check user status
        user = User.query.filter_by(propel_user_id=current_user.user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
        if user.is_banned:
            return jsonify({"error": "Banned users cannot upload notes"}), 403

        # Upload to Google Drive
        drive_url = upload_to_drive(file, course_id)
        if not drive_url:
            return jsonify({"error": "Failed to upload to Google Drive"}), 500

        # Create note record
        note = Note(
            course_id=course_id,
            user_id=user.id,
            title=title,
            content=drive_url,
            category_tags=json.dumps(tags),
            status="pending"
        )
        db.session.add(note)
        user.contributions += 1
        db.session.commit()

        return jsonify({
            "message": "Note uploaded successfully and pending review",
            "note_id": note.id,
            "file_url": drive_url
        }), 201

      except Exception as e:
        print(f"Error uploading note: {e}")
        db.session.rollback()
        return jsonify({"error": "Internal Server Error"}), 500
      

    @bp.route("/<int:course_id>", methods=["GET"])
    def fetch_notes(course_id):
      try:
        notes = Note.query.filter_by(course_id=course_id, status="approved").all()
        note_list = [{
            "id": note.id,
            "title": note.title,
            "file_url": note.content,  # Now contains Drive URL
            "author": note.user.name,
            # ... rest of fields
        } for note in notes]
        return jsonify(note_list), 200
      except Exception as e:
        print(f"Error fetching notes: {e}")
        return jsonify({"error": "Internal Server Error"}), 500
    

    @bp.route("/vote/<int:note_id>", methods=["PATCH"])
    @auth.require_user
    def vote_note(note_id):
        try:
            data = request.get_json()
            vote_type = data.get("vote")  # "helpful" or "unhelpful"

            if vote_type not in ["helpful", "unhelpful"]:
                return jsonify({"error": "Invalid vote type"}), 400

            note = Note.query.get(note_id)
            if not note:
                return jsonify({"error": "Note not found"}), 404
            if note.status != "approved":
                return jsonify({"error": "Cannot vote on unapproved notes"}), 403

            user = User.query.filter_by(propel_user_id=current_user.user_id).first()
            if not user:
                return jsonify({"error": "User not found"}), 404
            if user.is_banned:
                return jsonify({"error": "Banned users cannot vote"}), 403

            # Check if user has already voted
            existing_vote = NoteVote.query.filter_by(note_id=note_id, user_id=user.id).first()
            if existing_vote:
                if existing_vote.vote_type == vote_type:
                    return jsonify({"error": f"You already voted this note as {vote_type}"}), 400
                else:
                    # Reverse previous vote
                    if existing_vote.vote_type == "helpful":
                        note.helpful_votes -= 1
                    else:
                        note.unhelpful_votes -= 1
                    # Update to new vote
                    existing_vote.vote_type = vote_type
            else:
                # Create new vote
                vote = NoteVote(note_id=note_id, user_id=user.id, vote_type=vote_type)
                db.session.add(vote)

            # Update note's vote count
            if vote_type == "helpful":
                note.helpful_votes += 1
            else:
                note.unhelpful_votes += 1

            db.session.commit()
            return jsonify({
                "message": "Vote recorded successfully",
                "helpful_votes": note.helpful_votes,
                "unhelpful_votes": note.unhelpful_votes
            }), 200
        except Exception as e:
            print(f"Error voting note: {e}")
            db.session.rollback()
            return jsonify({"error": "Internal Server Error"}), 500

    @bp.route("/review", methods=["GET"])
    @auth.require_user
    def review_notes():
        try:
            user = User.query.filter_by(propel_user_id=current_user.user_id).first()
            if not user or user.role not in ["Moderator", "Admin"]:
                return jsonify({"error": "Unauthorized"}), 403

            notes = Note.query.filter_by(status="pending").all()
            note_list = [
                {
                    "id": note.id,
                    "title": note.title,
                    "content": note.content,
                    "author": note.user.name,
                    "tags": json.loads(note.category_tags or "[]"),
                    "created_at": note.created_at.isoformat()
                }
                for note in notes
            ]
            return jsonify(note_list), 200
        except Exception as e:
            print(f"Error fetching notes for review: {e}")
            return jsonify({"error": "Internal Server Error"}), 500

    @bp.route("/review/<int:note_id>", methods=["PATCH"])
    @auth.require_user
    def update_note_status(note_id):
        try:
            user = User.query.filter_by(propel_user_id=current_user.user_id).first()
            if not user or user.role not in ["Moderator", "Admin"]:
                return jsonify({"error": "Unauthorized"}), 403

            note = Note.query.get(note_id)
            if not note:
                return jsonify({"error": "Note not found"}), 404

            data = request.get_json()
            status = data.get("status")
            if status not in ["approved", "rejected"]:
                return jsonify({"error": "Invalid status"}), 400

            note.status = status
            db.session.commit()

            return jsonify({"message": f"Note {status} successfully"}), 200
        except Exception as e:
            print(f"Error updating note status: {e}")
            db.session.rollback()
            return jsonify({"error": "Internal Server Error"}), 500

    @bp.route("/report", methods=["POST"])
    @auth.require_user
    def report_note():
        try:
            data = request.get_json()
            note_id = data.get("note_id")
            reason = data.get("reason")

            if not note_id or not reason:
                return jsonify({"error": "Note ID and reason are required"}), 400

            note = Note.query.get(note_id)
            if not note:
                return jsonify({"error": "Note not found"}), 404

            user = User.query.filter_by(propel_user_id=current_user.user_id).first()
            if not user:
                return jsonify({"error": "User not found"}), 404
            if user.is_banned:
                return jsonify({"error": "Banned users cannot report notes"}), 403

            # Check for duplicate reports by the same user
            existing_report = NoteReport.query.filter_by(note_id=note_id, reporter_user_id=user.id).first()
            if existing_report:
                return jsonify({"error": "You already reported this note"}), 400

            report = NoteReport(
                note_id=note.id,
                reporter_user_id=user.id,
                reason=reason
            )
            db.session.add(report)
            db.session.commit()

            return jsonify({"message": "Note reported successfully"}), 201
        except Exception as e:
            print(f"Error reporting note: {e}")
            db.session.rollback()
            return jsonify({"error": "Internal Server Error"}), 500

    @bp.route("/reports", methods=["GET"])
    @auth.require_user
    def get_note_reports():
        try:
            user = User.query.filter_by(propel_user_id=current_user.user_id).first()
            if not user or user.role not in ["Moderator", "Admin"]:
                return jsonify({"error": "Unauthorized"}), 403

            reports = NoteReport.query.all()
            report_list = [
                {
                    "id": report.id,
                    "note_id": report.note_id,
                    "note_title": Note.query.get(report.note_id).title,
                    "reason": report.reason,
                    "reporter": User.query.get(report.reporter_user_id).name,
                    "created_at": report.created_at.isoformat()
                }
                for report in reports
            ]
            return jsonify(report_list), 200
        except Exception as e:
            print(f"Error fetching note reports: {e}")
            return jsonify({"error": "Internal Server Error"}), 500

    @bp.route("/resolve_report/<int:report_id>", methods=["PATCH"])
    @auth.require_user
    def resolve_note_report(report_id):
        try:
            user = User.query.filter_by(propel_user_id=current_user.user_id).first()
            if not user or user.role not in ["Moderator", "Admin"]:
                return jsonify({"error": "Unauthorized"}), 403

            data = request.get_json()
            action = data.get("action")  # "remove" or "dismiss"

            report = NoteReport.query.get(report_id)
            if not report:
                return jsonify({"error": "Report not found"}), 404

            if action == "remove":
                note = Note.query.get(report.note_id)
                if note:
                    note.status = "rejected"  # Mark as rejected instead of deleting
            elif action != "dismiss":
                return jsonify({"error": "Invalid action"}), 400

            db.session.delete(report)
            db.session.commit()

            return jsonify({"message": "Report resolved successfully"}), 200
        except Exception as e:
            print(f"Error resolving note report: {e}")
            db.session.rollback()
            return jsonify({"error": "Internal Server Error"}), 500

    return bp