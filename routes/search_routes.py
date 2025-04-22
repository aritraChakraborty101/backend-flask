from flask import Blueprint, request, jsonify
from sqlalchemy import or_
from models import User, Course, Note, db

# Optionally import an Organization model if available.
try:
    from models import Organization
except ImportError:
    Organization = None

def create_search_routes(auth):
    bp = Blueprint('search', __name__)

    @bp.route('', methods=['GET'])
    def search():
        query = request.args.get("query", "").strip()
        if not query:
            return jsonify([]), 200

        # SQLite wildcard for partial matching
        wildcard = f"%{query}%"
        users = courses = orgs = notes = []

        # --- Search Users ---
        user_objs = User.query.filter(
            or_(
                User.name.ilike(wildcard),
                User.email.ilike(wildcard)
            )
        ).limit(10).all()
        users = [{
            "id": u.propel_user_id,
            "type": "user",
            "title": u.name,
            "subtitle": u.email,
            "url": f"/profile/{u.propel_user_id}"
        } for u in user_objs]

        # --- Search Courses ---
        course_objs = Course.query.filter(Course.name.ilike(wildcard)).limit(10).all()
        courses = [{
            "id": c.id,
            "type": "course",
            "title": c.name,
            "subtitle": "",
            "url": f"/courses/{c.id}/notes"
        } for c in course_objs]

        # --- Search Organizations (if available) ---
        if Organization:
            org_objs = Organization.query.filter(
                Organization.name.ilike(wildcard)
            ).limit(10).all()
            orgs = [{
                "id": o.id,
                "type": "organization",
                "title": o.name,
                "subtitle": getattr(o, 'description', ''),
                "url": f"/org/{o.id}"
            } for o in org_objs]

  
        # Combine all results
        results = users + courses + orgs + notes
        if not results:
            # Instead of returning a dummy object, you can return an empty list.
            # Your frontend must display a "No results found" message when it gets an empty list.
            return jsonify([]), 200

        return jsonify(results), 200

    return bp
