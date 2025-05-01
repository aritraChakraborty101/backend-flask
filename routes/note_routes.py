from flask import Blueprint, request, jsonify
from flask_cors import CORS
from datetime import datetime
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


def create_note_routes(auth, supabase):
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

            # Check if the user exists
            user = supabase.table("user").select("*").eq("propel_user_id", current_user.user_id).execute().data
            if not user:
                return jsonify({"error": "User not found"}), 404
            user = user[0]
            if user.get("is_banned"):
                return jsonify({"error": "Banned users cannot upload notes"}), 403

            # Upload the file to Cloudinary
            upload_result = cloudinary.uploader.upload(file, resource_type="raw", folder=f"courses/{course_id}")
            file_url = upload_result.get("secure_url")

            # Insert the note into Supabase
            note_data = {
                "course_id": course_id,
                "user_id": user["id"],
                "title": title,
                "content": file_url,
                "category_tags": json.dumps(tags),
                "status": "pending",
                "helpful_votes": 0,
                "unhelpful_votes": 0,
                "created_at": datetime.utcnow().isoformat()
            }
            supabase.table("note").insert(note_data).execute()

            # Update the user's contributions
            contributions = user.get("contributions", 0) + 1
            supabase.table("user").update({"contributions": contributions}).eq("id", user["id"]).execute()

            return jsonify({
                "message": "Note uploaded successfully and pending review",
                "file_url": file_url
            }), 201
        except Exception as e:
            print(f"Error uploading note: {e}")
            return jsonify({"error": "Internal Server Error"}), 500

    @bp.route("/<int:course_id>", methods=["GET"])
    def fetch_notes(course_id):
        try:
            # Fetch all approved notes for the course
            notes = supabase.table("note").select("*").eq("course_id", course_id).eq("status", "approved").execute().data

            note_list = []
            for note in notes:
                user = supabase.table("user").select("name", "propel_user_id").eq("id", note["user_id"]).execute().data
                author_name = user[0]["name"] if user else "Unknown"
                propel_user_id = user[0]["propel_user_id"] if user else "Unknown"
                

                note_list.append({
                    "id": note["id"],
                    "title": note["title"],
                    "file_url": note["content"],
                    "author": author_name,
                    "tags": json.loads(note["category_tags"] or "[]"),
                    "created_at": note["created_at"],
                    "user_id": propel_user_id,
                    "helpful_votes": note["helpful_votes"],
                    "unhelpful_votes": note["unhelpful_votes"]
                })

            return jsonify(note_list), 200
        except Exception as e:
            print(f"Error fetching notes: {e}")
            return jsonify({"error": "Internal Server Error"}), 500

    @bp.route("/<int:course_id>/<int:note_id>", methods=["GET"])
    def fetch_note(course_id, note_id):
        try:
            # Fetch the note
            note = supabase.table("note").select("*").eq("course_id", course_id).eq("id", note_id).eq("status", "approved").execute().data
            if not note:
                return jsonify({"error": "Note not found"}), 404
            note = note[0]

            # Fetch the author's name
            user = supabase.table("user").select("name").eq("id", note["user_id"]).execute().data
            author_name = user[0]["name"] if user else "Unknown"
            

            return jsonify({
                "id": note["id"],
                "title": note["title"],
                "file_url": note["content"],
                "author": author_name,
                "tags": json.loads(note["category_tags"] or "[]"),
                "created_at": note["created_at"],
                "user_id": note["user_id"],
                "helpful_votes": note["helpful_votes"],
                "unhelpful_votes": note["unhelpful_votes"]
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
            voter_id = current_user.user_id

            if vote_type not in ["upvote", "downvote"]:
                return jsonify({"error": "Invalid vote type."}), 400

            # Fetch the note
            note = supabase.table("note").select("*").eq("id", note_id).execute().data
            if not note:
                return jsonify({"error": "Note not found"}), 404
            note = note[0]

            # Check if the user has already voted
            existing_vote = supabase.table("note_vote").select("*").eq("note_id", note_id).eq("user_id", voter_id).execute().data
            if existing_vote:
                existing_vote = existing_vote[0]
                if existing_vote["vote_type"] == vote_type:
                    # Cancel the vote
                    supabase.table("note_vote").delete().eq("id", existing_vote["id"]).execute()
                    if vote_type == "upvote":
                        new_helpful_votes = max(0, note["helpful_votes"] - 1)
                        supabase.table("note").update({"helpful_votes": new_helpful_votes}).eq("id", note_id).execute()
                    else:
                        new_unhelpful_votes = max(0, note["unhelpful_votes"] - 1)
                        supabase.table("note").update({"unhelpful_votes": new_unhelpful_votes}).eq("id", note_id).execute()
                    return jsonify({"message": f"{vote_type.capitalize()} canceled"}), 200
                else:
                    # Change the vote type
                    supabase.table("note_vote").update({"vote_type": vote_type}).eq("id", existing_vote["id"]).execute()
                    if vote_type == "upvote":
                        new_helpful_votes = note["helpful_votes"] + 1
                        new_unhelpful_votes = max(0, note["unhelpful_votes"] - 1)
                        supabase.table("note").update({"helpful_votes": new_helpful_votes, "unhelpful_votes": new_unhelpful_votes}).eq("id", note_id).execute()
                    else:
                        new_unhelpful_votes = note["unhelpful_votes"] + 1
                        new_helpful_votes = max(0, note["helpful_votes"] - 1)
                        supabase.table("note").update({"unhelpful_votes": new_unhelpful_votes, "helpful_votes": new_helpful_votes}).eq("id", note_id).execute()
                    return jsonify({"message": f"Vote changed to {vote_type}"}), 200

            # Add a new vote
            supabase.table("note_vote").insert({
                "note_id": note_id,
                "user_id": voter_id,
                "vote_type": vote_type,
                "created_at": datetime.utcnow().isoformat()
            }).execute()

            # Update the vote counts
            if vote_type == "upvote":
                new_helpful_votes = note["helpful_votes"] + 1
                supabase.table("note").update({"helpful_votes": new_helpful_votes}).eq("id", note_id).execute()
            else:
                new_unhelpful_votes = note["unhelpful_votes"] + 1
                supabase.table("note").update({"unhelpful_votes": new_unhelpful_votes}).eq("id", note_id).execute()

            return jsonify({"message": f"Note {vote_type}d successfully"}), 201
        except Exception as e:
            print(f"Error voting: {e}")
            return jsonify({"error": "Internal Server Error"}), 500


    @bp.route("/<int:note_id>/comments", methods=["POST"])
    @auth.require_user
    def create_note_comment(note_id):
        try:
            data = request.get_json()
            content = data.get("content")
            user_id = current_user.user_id  # Get the current user's ID

            if not content:
                return jsonify({"error": "Content is required"}), 400

            # Check if the note exists
            note = supabase.table("note").select("*").eq("id", note_id).execute().data
            if not note:
                return jsonify({"error": "Note not found"}), 404

            # Insert the comment into the database
            supabase.table("note_comment").insert({
                "note_id": note_id,
                "user_id": user_id,
                "content": content,
                "created_at": datetime.utcnow().isoformat()
            }).execute()

            return jsonify({"message": "Comment added successfully!"}), 201
        except Exception as e:
            print(f"Error creating comment: {e}")
            return jsonify({"error": "Internal Server Error"}), 500

    @bp.route("/<int:note_id>/comments", methods=["GET"])
    def get_note_comments(note_id):
        try:
            # Fetch all comments for the note
            comments = supabase.table("note_comment").select("*").eq("note_id", note_id).order("created_at", desc=False).execute().data

            # if not comments:
            #     return jsonify({"error": "No comments found"}), 404

            # Fetch user details for each comment
            comments_data = []
            for comment in comments:
                user = supabase.table("user").select("name").eq("propel_user_id", comment["user_id"]).execute().data
                author_name = user[0]["name"] if user else "Unknown"

                comments_data.append({
                    "id": comment["id"],
                    "user_id": comment["user_id"],
                    "author": author_name,
                    "content": comment["content"],
                    "created_at": comment["created_at"]
                })

            return jsonify(comments_data), 200
        except Exception as e:
            print(f"Error fetching comments: {e}")
            return jsonify({"error": "Internal Server Error"}), 500

    @bp.route("/<int:note_id>/comments/<int:comment_id>", methods=["DELETE"])
    @auth.require_user
    def delete_note_comment(note_id, comment_id):
        try:
            # Fetch the comment
            comment = supabase.table("note_comment").select("*").eq("id", comment_id).eq("note_id", note_id).execute().data
            if not comment:
                return jsonify({"error": "Comment not found"}), 404
            comment = comment[0]

            # Ensure the user is the author of the comment or an admin
            user = supabase.table("user").select("*").eq("propel_user_id", current_user.user_id).execute().data
            if not user:
                return jsonify({"error": "User not found"}), 404
            user = user[0]
            if str(comment["user_id"]) != str(user["propel_user_id"]) and user["role"] != "Admin":
                return jsonify({"error": "Unauthorized to delete this comment"}), 403

            # Delete the comment
            supabase.table("note_comment").delete().eq("id", comment_id).execute()

            return jsonify({"message": "Comment deleted successfully!"}), 200
        except Exception as e:
            print(f"Error deleting comment: {e}")
            return jsonify({"error": "Internal Server Error"}), 500


    # @bp.route("/<int:note_id>/report", methods=["POST"])
    # @auth.require_user
    # def report_note(note_id):
    #     try:
    #         data = request.get_json()
    #         reporter_id = data.get("reporter_user_id")
    #         reason = data.get("reason")
    #         if not reason:
    #             return jsonify({"error": "Report reason required"}), 400
    #         note = Note.query.get(note_id)
    #         if not note:
    #             return jsonify({"error": "Note not found"}), 404
    #         report = NoteReport(note_id=note_id, reporter_user_id=reporter_id, reason=reason)
    #         db.session.add(report)
    #         db.session.commit()
    #         return jsonify({"message": "Note reported successfully", "report_id": report.id}), 201
    #     except Exception as e:
    #         print(f"Error reporting note: {e}")
    #         db.session.rollback()
    #         return jsonify({"error": "Internal Server Error"}), 500
        




    @bp.route("/review", methods=["GET"])
    @auth.require_user
    def review_notes():
        try:
            # Ensure the user is an admin
            user = supabase.table("user").select("*").eq("propel_user_id", current_user.user_id).execute().data
            if not user or user[0]["role"] != "Admin":
                return jsonify({"error": "Unauthorized"}), 403

            # Fetch all pending notes
            notes = supabase.table("note").select("*").eq("status", "pending").execute().data

            note_list = [
                {
                    "id": note["id"],
                    "title": note["title"],
                    "content": note["content"],
                    "author": supabase.table("user").select("name").eq("id", note["user_id"]).execute().data[0]["name"],
                    "tags": json.loads(note["category_tags"] or "[]"),
                    "created_at": note["created_at"],
                    "course_id": note["course_id"]
                }
                for note in notes
            ]
            return jsonify(note_list), 200
        except Exception as e:
            print(f"Error fetching pending notes: {e}")
            return jsonify({"error": "Internal Server Error"}), 500

    @bp.route("/review/<int:note_id>", methods=["PATCH"])
    @auth.require_user
    def update_note_status(note_id):
        try:
            # Ensure the user is an admin
            user = supabase.table("user").select("*").eq("propel_user_id", current_user.user_id).execute().data
            if not user or user[0]["role"] != "Admin":
                return jsonify({"error": "Unauthorized"}), 403

            # Fetch the note
            note = supabase.table("note").select("*").eq("id", note_id).execute().data
            if not note:
                return jsonify({"error": "Note not found"}), 404
            note = note[0]

            # Get the new status from the request
            data = request.get_json()
            status = data.get("status")
            if status not in ["approved", "rejected"]:
                return jsonify({"error": "Invalid status"}), 400

            if status == "rejected":
                # Delete the note file from Cloudinary
                public_id = note["content"].split("/")[-1].split(".")[0]  # Extract public_id from the URL
                cloudinary.uploader.destroy(f"courses/{note['course_id']}/{public_id}", resource_type="raw")

                # Delete the note from Supabase
                supabase.table("note").delete().eq("id", note_id).execute()
            else:
                # Update the note's status to approved
                supabase.table("note").update({"status": status}).eq("id", note_id).execute()

            return jsonify({"message": f"Note {status} successfully"}), 200
        except Exception as e:
            print(f"Error updating note status: {e}")
            return jsonify({"error": "Internal Server Error"}), 500

    @bp.route("/<int:note_id>", methods=["DELETE"])
    @auth.require_user
    def delete_note(note_id):
        try:
            # Fetch the note
            note = supabase.table("note").select("*").eq("id", note_id).execute().data
            if not note:
                return jsonify({"error": "Note not found"}), 404
            note = note[0]

            # Ensure the user is the owner of the note or an admin
            user = supabase.table("user").select("*").eq("propel_user_id", current_user.user_id).execute().data
            if not user:
                return jsonify({"error": "User not found"}), 404
            user = user[0]
            if str(note["user_id"]) != str(user["id"]) and user["role"] != "Admin":
                return jsonify({"error": "Unauthorized to delete this note"}), 403

            # Delete associated comments
            supabase.table("note_comment").delete().eq("note_id", note_id).execute()

            # Delete associated votes
            supabase.table("note_vote").delete().eq("note_id", note_id).execute()

            # Delete the note file from Cloudinary
            public_id = note["content"].split("/")[-1].split(".")[0]  # Extract public_id from the URL
            cloudinary.uploader.destroy(f"courses/{note['course_id']}/{public_id}", resource_type="raw")

            # Delete the note itself
            supabase.table("note").delete().eq("id", note_id).execute()

            return jsonify({"message": "Note and all associated data deleted successfully"}), 200
        except Exception as e:
            print(f"Error deleting note: {e}")
            return jsonify({"error": "Internal Server Error"}), 500

    return bp




    