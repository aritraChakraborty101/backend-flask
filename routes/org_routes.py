from flask import Blueprint, jsonify
from propelauth_flask import current_org

def create_org_routes(auth):
    bp = Blueprint("org_routes", __name__)

    @bp.route("/<org_id>")
    @auth.require_org_member()
    def org_info(org_id):
        """Get organization info"""
        return jsonify({
            "org_id": current_org.org_id,
            "org_name": current_org.org_name
        })

    return bp