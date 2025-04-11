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


class UserReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reported_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reporter_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    issue = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="pending")  # pending, resolved, rejected
    created_at = db.Column(db.DateTime, default=db.func.now())

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    user_id = db.Column(db.String(255), db.ForeignKey('user.propel_user_id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    upvotes = db.Column(db.Integer, default=0)
    downvotes = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.String(255), db.ForeignKey('user.propel_user_id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.String(255), db.ForeignKey('user.propel_user_id'), nullable=False)
    vote_type = db.Column(db.String(10), nullable=False)  # "upvote" or "downvote"
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())