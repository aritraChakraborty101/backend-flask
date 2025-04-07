from app import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    propel_user_id = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255))
    email = db.Column(db.String(255), unique=True, nullable=False)
    role = db.Column(db.String(50), default="General")  # Default role is General
    courses_enrolled = db.Column(db.Text)  # JSON string for simplicity
    contributions = db.Column(db.Text)  # JSON string for metrics or rankings
    is_banned = db.Column(db.Boolean, default=False)

class RoleRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    requested_role = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default="pending")  # pending, approved, rejected