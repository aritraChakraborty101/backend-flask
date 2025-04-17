from flask import Blueprint, request, jsonify
from flask_cors import CORS
from models import db, Note, User, NoteVote, NoteReport, NoteComment
from propelauth_flask import current_user
import os
from werkzeug.utils import secure_filename
import json
import cloudinary
import cloudinary.uploader

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

UPLOAD_FOLDER = 'uploads/notes'
ALLOWED_EXTENSIONS = {'pdf'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Check if the file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def create_note_routes(auth):
    bp = Blueprint("note_routes", __name__)
    # Enable CORS for this blueprint
    CORS(bp, supports_credentials=True)

    @bp.route("/upload", methods=["POST"])
    @auth.require_user
    def upload_note():
        try:
            course_id = request.form.get("course_id")
            title = request.form.get("title")
            content = request.form.get("content")
            tags = request.form.get("tags", "").split(",")
            file = request.files.get("file")

            if not all([course_id, title, content, file]):
                return jsonify({"error": "Course ID, title, content, and file are required"}), 400

            if not allowed_file(file.filename):
                return jsonify({"error": "Only PDF files are allowed"}), 400

            user = User.query.filter_by(propel_user_id=current_user.user_id).first()
            if not user:
                return jsonify({"error": "User not found"}), 404
            if user.is_banned:
                return jsonify({"error": "Banned users cannot upload notes"}), 403

            upload_result = cloudinary.uploader.upload(file, resource_type="raw", folder=f"courses/{course_id}")
            file_url = upload_result.get("secure_url")

            note = Note(
                course_id=course_id,
                user_id=user.id,
                title=title,
                content=file_url,
                category_tags=json.dumps(tags),
                status="pending"
            )
            db.session.add(note)
            user.contributions += 1
            db.session.commit()

            return jsonify({
                "message": "Note uploaded successfully and pending review",
                "note_id": note.id,
                "file_url": file_url
            }), 201

        except Exception as e:
            print(f"Error uploading note: {e}")
            db.session.rollback()
            return jsonify({"error": "Internal Server Error"}), 500

    @bp.route("/<int:course_id>", methods=["GET"])
    def fetch_notes(course_id):
        try:
            notes = Note.query.filter_by(course_id=course_id).all()
            note_list = [{
                "id": note.id,
                "title": note.title,
                "file_url": note.content,
                "author": note.user.name,
                "tags": json.loads(note.category_tags or "[]"),
                "created_at": note.created_at.isoformat(),
                "user_id": note.user_id
            } for note in notes]
            return jsonify(note_list), 200
        except Exception as e:
            print(f"Error fetching notes: {e}")
            return jsonify({"error": "Internal Server Error"}), 500

    @bp.route("/<int:course_id>/<int:note_id>", methods=["GET"])
    def fetch_note(course_id, note_id):
        try:
            note = Note.query.filter_by(course_id=course_id, id=note_id).first()
            if not note:
                return jsonify({"error": "Note not found"}), 404

            return jsonify({
                "id": note.id,
                "title": note.title,
                "file_url": note.content,
                "author": note.user.name,
                "tags": json.loads(note.category_tags or "[]"),
                "created_at": note.created_at.isoformat(),
                "user_id": note.user_id
            }), 200
        except Exception as e:
            print(f"Error fetching note: {e}")
            return jsonify({"error": "Internal Server Error"}), 500

    @bp.route("/<int:note_id>/vote", methods=["POST"])
    @auth.require_user
    def vote_note(note_id):
        try:
            data = request.get_json()
            vote_type = data.get("vote_type")
            voter_id = data.get("user_id")

            if vote_type not in ["upvote", "downvote"]:
                return jsonify({"error": "Invalid vote type."}), 400

            note = Note.query.get(note_id)
            if not note:
                return jsonify({"error": "Note not found"}), 404

            existing = NoteVote.query.filter_by(note_id=note_id, user_id=voter_id).first()
            if existing:
                if existing.vote_type == vote_type:
                    db.session.delete(existing)
                    if vote_type == "upvote": note.helpful_votes = max(note.helpful_votes - 1, 0)
                    else: note.unhelpful_votes = max(note.unhelpful_votes - 1, 0)
                    message = f"{vote_type.capitalize()} canceled"
                else:
                    prev = existing.vote_type
                    existing.vote_type = vote_type
                    if vote_type == "upvote":
                        note.helpful_votes += 1
                        note.unhelpful_votes = max(note.unhelpful_votes - 1, 0)
                    else:
                        note.unhelpful_votes += 1
                        note.helpful_votes = max(note.helpful_votes - 1, 0)
                    message = f"Vote changed from {prev} to {vote_type}"
                db.session.commit()
                return jsonify({"message": message}), 200

            new_vote = NoteVote(note_id=note_id, user_id=voter_id, vote_type=vote_type)
            db.session.add(new_vote)
            if vote_type == "upvote": note.helpful_votes += 1
            else: note.unhelpful_votes += 1
            db.session.commit()
            return jsonify({"message": f"Note {vote_type}d successfully"}), 201
        except Exception as e:
            print(f"Error voting: {e}")
            db.session.rollback()
            return jsonify({"error": "Internal Server Error"}), 500

    @bp.route("/<int:note_id>/comments", methods=["POST"])
    @auth.require_user
    def create_note_comment(note_id):
        try:
            data = request.get_json()
            uid = data.get("user_id")
            content = data.get("content")
            if not content:
                return jsonify({"error": "Content is required"}), 400
            note = Note.query.get(note_id)
            if not note:
                return jsonify({"error": "Note not found"}), 404
            comment = NoteComment(note_id=note_id, user_id=uid, content=content)
            db.session.add(comment)
            db.session.commit()
            return jsonify({"message": "Comment added successfully!", "comment_id": comment.id}), 201
        except Exception as e:
            print(f"Error adding comment: {e}")
            db.session.rollback()
            return jsonify({"error": "Internal Server Error"}), 500

    @bp.route("/<int:note_id>/comments", methods=["GET"])
    def get_note_comments(note_id):
        try:
            comments = NoteComment.query.filter_by(note_id=note_id).order_by(NoteComment.created_at.asc()).all()
            out = []
            for c in comments:
                user_obj = User.query.filter_by(propel_user_id=c.user_id).first()
                out.append({
                    "id": c.id,
                    "user_id": c.user_id,
                    "author": user_obj.name if user_obj else "Unknown",
                    "content": c.content,
                    "created_at": c.created_at.isoformat()
                })
            return jsonify(out), 200
        except Exception as e:
            print(f"Error fetching comments: {e}")
            return jsonify({"error": "Internal Server Error"}), 500

    @bp.route("/<int:note_id>/comments/<int:comment_id>", methods=["DELETE"])
    @auth.require_user
    def delete_note_comment(note_id, comment_id):
        try:
            print(f"Attempting delete comment {comment_id} on note {note_id} by user {current_user.user_id}")
            comment = NoteComment.query.filter_by(id=comment_id, note_id=note_id).first()
            if not comment:
                print("Comment not found")
                return jsonify({"error": "Comment not found"}), 404

            user_obj = User.query.filter_by(propel_user_id=current_user.user_id).first()
            if not user_obj:
                print("User not found")
                return jsonify({"error": "User not found"}), 404

            if str(comment.user_id) != current_user.user_id and user_obj.role != "Admin":
                print(f"Unauthorized delete by {current_user.user_id}")
                return jsonify({"error": "Unauthorized to delete this comment"}), 403

            db.session.delete(comment)
            db.session.commit()
            print(f"Comment {comment_id} deleted successfully")

            # Return updated comments list
            updated_comments = NoteComment.query.filter_by(note_id=note_id).order_by(NoteComment.created_at.asc()).all()
            comments_data = []
            for c in updated_comments:
                usr = User.query.filter_by(propel_user_id=c.user_id).first()
                comments_data.append({
                    "id": c.id,
                    "user_id": c.user_id,
                    "author": usr.name if usr else "Unknown",
                    "content": c.content,
                    "created_at": c.created_at.isoformat()
                })
            return jsonify({"message": "Comment deleted successfully", "comments": comments_data}), 200

        except Exception as e:
            print(f"Error deleting comment: {e}")
            db.session.rollback()
            return jsonify({"error": "Internal Server Error"}), 500

    @bp.route("/<int:note_id>/report", methods=["POST"])
    @auth.require_user
    def report_note(note_id):
        try:
            data = request.get_json()
            reporter_id = data.get("reporter_user_id")
            reason = data.get("reason")
            if not reason:
                return jsonify({"error": "Report reason required"}), 400
            note = Note.query.get(note_id)
            if not note:
                return jsonify({"error": "Note not found"}), 404
            report = NoteReport(note_id=note_id, reporter_user_id=reporter_id, reason=reason)
            db.session.add(report)
            db.session.commit()
            return jsonify({"message": "Note reported successfully", "report_id": report.id}), 201
        except Exception as e:
            print(f"Error reporting note: {e}")
            db.session.rollback()
            return jsonify({"error": "Internal Server Error"}), 500

    return bp




    # @bp.route("/<int:course_id>", methods=["GET"])
    # def fetch_notes(course_id):
    #   try:
    #     notes = Note.query.filter_by(course_id=course_id, status="approved").all()
    #     note_list = [{
    #         "id": note.id,
    #         "title": note.title,
    #         "file_url": note.content,  # Now contains Drive URL
    #         "author": note.user.name,
    #         # ... rest of fields
    #     } for note in notes]
    #     return jsonify(note_list), 200
    #   except Exception as e:
    #     print(f"Error fetching notes: {e}")
    #     return jsonify({"error": "Internal Server Error"}), 500
    

    # @bp.route("/vote/<int:note_id>", methods=["PATCH"])
    # @auth.require_user
    # def vote_note(note_id):
    #     try:
    #         data = request.get_json()
    #         vote_type = data.get("vote")  # "helpful" or "unhelpful"

    #         if vote_type not in ["helpful", "unhelpful"]:
    #             return jsonify({"error": "Invalid vote type"}), 400

    #         note = Note.query.get(note_id)
    #         if not note:
    #             return jsonify({"error": "Note not found"}), 404
    #         if note.status != "approved":
    #             return jsonify({"error": "Cannot vote on unapproved notes"}), 403

    #         user = User.query.filter_by(propel_user_id=current_user.user_id).first()
    #         if not user:
    #             return jsonify({"error": "User not found"}), 404
    #         if user.is_banned:
    #             return jsonify({"error": "Banned users cannot vote"}), 403

    #         # Check if user has already voted
    #         existing_vote = NoteVote.query.filter_by(note_id=note_id, user_id=user.id).first()
    #         if existing_vote:
    #             if existing_vote.vote_type == vote_type:
    #                 return jsonify({"error": f"You already voted this note as {vote_type}"}), 400
    #             else:
    #                 # Reverse previous vote
    #                 if existing_vote.vote_type == "helpful":
    #                     note.helpful_votes -= 1
    #                 else:
    #                     note.unhelpful_votes -= 1
    #                 # Update to new vote
    #                 existing_vote.vote_type = vote_type
    #         else:
    #             # Create new vote
    #             vote = NoteVote(note_id=note_id, user_id=user.id, vote_type=vote_type)
    #             db.session.add(vote)

    #         # Update note's vote count
    #         if vote_type == "helpful":
    #             note.helpful_votes += 1
    #         else:
    #             note.unhelpful_votes += 1

    #         db.session.commit()
    #         return jsonify({
    #             "message": "Vote recorded successfully",
    #             "helpful_votes": note.helpful_votes,
    #             "unhelpful_votes": note.unhelpful_votes
    #         }), 200
    #     except Exception as e:
    #         print(f"Error voting note: {e}")
    #         db.session.rollback()
    #         return jsonify({"error": "Internal Server Error"}), 500

    # @bp.route("/review", methods=["GET"])
    # @auth.require_user
    # def review_notes():
    #     try:
    #         user = User.query.filter_by(propel_user_id=current_user.user_id).first()
    #         if not user or user.role not in ["Moderator", "Admin"]:
    #             return jsonify({"error": "Unauthorized"}), 403

    #         notes = Note.query.filter_by(status="pending").all()
    #         note_list = [
    #             {
    #                 "id": note.id,
    #                 "title": note.title,
    #                 "content": note.content,
    #                 "author": note.user.name,
    #                 "tags": json.loads(note.category_tags or "[]"),
    #                 "created_at": note.created_at.isoformat()
    #             }
    #             for note in notes
    #         ]
    #         return jsonify(note_list), 200
    #     except Exception as e:
    #         print(f"Error fetching notes for review: {e}")
    #         return jsonify({"error": "Internal Server Error"}), 500

    # @bp.route("/review/<int:note_id>", methods=["PATCH"])
    # @auth.require_user
    # def update_note_status(note_id):
    #     try:
    #         user = User.query.filter_by(propel_user_id=current_user.user_id).first()
    #         if not user or user.role not in ["Moderator", "Admin"]:
    #             return jsonify({"error": "Unauthorized"}), 403

    #         note = Note.query.get(note_id)
    #         if not note:
    #             return jsonify({"error": "Note not found"}), 404

    #         data = request.get_json()
    #         status = data.get("status")
    #         if status not in ["approved", "rejected"]:
    #             return jsonify({"error": "Invalid status"}), 400

    #         note.status = status
    #         db.session.commit()

    #         return jsonify({"message": f"Note {status} successfully"}), 200
    #     except Exception as e:
    #         print(f"Error updating note status: {e}")
    #         db.session.rollback()
    #         return jsonify({"error": "Internal Server Error"}), 500

    # @bp.route("/report", methods=["POST"])
    # @auth.require_user
    # def report_note():
    #     try:
    #         data = request.get_json()
    #         note_id = data.get("note_id")
    #         reason = data.get("reason")

    #         if not note_id or not reason:
    #             return jsonify({"error": "Note ID and reason are required"}), 400

    #         note = Note.query.get(note_id)
    #         if not note:
    #             return jsonify({"error": "Note not found"}), 404

    #         user = User.query.filter_by(propel_user_id=current_user.user_id).first()
    #         if not user:
    #             return jsonify({"error": "User not found"}), 404
    #         if user.is_banned:
    #             return jsonify({"error": "Banned users cannot report notes"}), 403

    #         # Check for duplicate reports by the same user
    #         existing_report = NoteReport.query.filter_by(note_id=note_id, reporter_user_id=user.id).first()
    #         if existing_report:
    #             return jsonify({"error": "You already reported this note"}), 400

    #         report = NoteReport(
    #             note_id=note.id,
    #             reporter_user_id=user.id,
    #             reason=reason
    #         )
    #         db.session.add(report)
    #         db.session.commit()

    #         return jsonify({"message": "Note reported successfully"}), 201
    #     except Exception as e:
    #         print(f"Error reporting note: {e}")
    #         db.session.rollback()
    #         return jsonify({"error": "Internal Server Error"}), 500

    # @bp.route("/reports", methods=["GET"])
    # @auth.require_user
    # def get_note_reports():
    #     try:
    #         user = User.query.filter_by(propel_user_id=current_user.user_id).first()
    #         if not user or user.role not in ["Moderator", "Admin"]:
    #             return jsonify({"error": "Unauthorized"}), 403

    #         reports = NoteReport.query.all()
    #         report_list = [
    #             {
    #                 "id": report.id,
    #                 "note_id": report.note_id,
    #                 "note_title": Note.query.get(report.note_id).title,
    #                 "reason": report.reason,
    #                 "reporter": User.query.get(report.reporter_user_id).name,
    #                 "created_at": report.created_at.isoformat()
    #             }
    #             for report in reports
    #         ]
    #         return jsonify(report_list), 200
    #     except Exception as e:
    #         print(f"Error fetching note reports: {e}")
    #         return jsonify({"error": "Internal Server Error"}), 500

    # @bp.route("/resolve_report/<int:report_id>", methods=["PATCH"])
    # @auth.require_user
    # def resolve_note_report(report_id):
    #     try:
    #         user = User.query.filter_by(propel_user_id=current_user.user_id).first()
    #         if not user or user.role not in ["Moderator", "Admin"]:
    #             return jsonify({"error": "Unauthorized"}), 403

    #         data = request.get_json()
    #         action = data.get("action")  # "remove" or "dismiss"

    #         report = NoteReport.query.get(report_id)
    #         if not report:
    #             return jsonify({"error": "Report not found"}), 404

    #         if action == "remove":
    #             note = Note.query.get(report.note_id)
    #             if note:
    #                 note.status = "rejected"  # Mark as rejected instead of deleting
    #         elif action != "dismiss":
    #             return jsonify({"error": "Invalid action"}), 400

    #         db.session.delete(report)
    #         db.session.commit()

    #         return jsonify({"message": "Report resolved successfully"}), 200
    #     except Exception as e:
    #         print(f"Error resolving note report: {e}")
    #         db.session.rollback()
    #         return jsonify({"error": "Internal Server Error"}), 500

    return bp