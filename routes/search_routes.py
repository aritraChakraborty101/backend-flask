from flask import Blueprint, request, jsonify
from sqlalchemy import or_
# from models import User, Course, Note, db

# Optionally import an Organization model if available.
# try:
#     from models import Organization
# except ImportError:
#     Organization = None

def create_search_routes(auth, supabase):
    bp = Blueprint('search', __name__)

    @bp.route('', methods=['GET'])
    def search():
        try:
            query = request.args.get("query", "").strip()
            if not query:
                return jsonify([]), 200

            # Supabase wildcard for partial matching
            wildcard = f"%{query}%"
            users = courses = notes = []

            # --- Search Users ---
            user_results = supabase.table("user").select("*").ilike("name", wildcard).execute().data
            users = [{
                "id": u["propel_user_id"],
                "type": "user",
                "title": u["name"],
                "subtitle": u["email"],
                "url": f"/profile/{u['propel_user_id']}"
            } for u in user_results]

            # --- Search Courses ---
            course_results = supabase.table("course").select("*").ilike("name", wildcard).execute().data
            courses = [{
                "id": c["id"],
                "type": "course",
                "title": c["name"],
                "subtitle": "",
                "url": f"/courses/{c['id']}/notes"
            } for c in course_results]


            # --- Search Notes ---
            note_results = supabase.table("note").select("*").ilike("title", wildcard).execute().data
            notes = [{
                "id": n["id"],
                "type": "note",
                "title": n["title"],
                "subtitle": "",
                "url": f"/notes/{n['id']}"
            } for n in note_results]

            # Combine all results
            results = users + courses + notes
            return jsonify(results), 200
        except Exception as e:
            print(f"Error in search: {e}")
            return jsonify({"error": "Internal Server Error"}), 500

    return bp
