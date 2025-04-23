from app import db
from flask_sqlalchemy import SQLAlchemy
import json

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    propel_user_id = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255))
    email = db.Column(db.String(255), unique=True, nullable=False)
    role = db.Column(db.String(50), default="General")
    courses_enrolled = db.Column(db.Text)  # JSON string
    contributions = db.Column(db.Integer, default=0)
    is_banned = db.Column(db.Boolean, default=False)
    def __repr__(self):
        return f"<User {self.email}>"

class RoleRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    requested_role = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default="pending")

class UserReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reported_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reporter_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    issue = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=db.func.now())

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    helpful_votes = db.Column(db.Integer, default=0)
    unhelpful_votes = db.Column(db.Integer, default=0)
    category_tags = db.Column(db.Text)  # JSON string
    status = db.Column(db.String(20), default="pending")  # pending, approved, rejected
    created_at = db.Column(db.DateTime, default=db.func.now())
    user = db.relationship('User', backref='notes')

class NoteVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey('note.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    vote_type = db.Column(db.String(20), nullable=False)  # "helpful" or "unhelpful"
    created_at = db.Column(db.DateTime, default=db.func.now())
    __table_args__ = (db.UniqueConstraint('note_id', 'user_id', name='unique_user_note_vote'),)

class NoteReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey('note.id'), nullable=False)
    reporter_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())
    status = db.Column(db.String(20), default="pending")  # pending, resolved, rejected
    created_at = db.Column(db.DateTime, default=db.func.now())

class NoteComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey('note.id'), nullable=False)
    user_id = db.Column(db.String(255), nullable=False)  # Or use an integer foreign key if you prefer
    content = db.Column(db.Text, nullable=False)
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


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.String(255), db.ForeignKey('user.propel_user_id'), nullable=False)
    receiver_id = db.Column(db.String(255), db.ForeignKey('user.propel_user_id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages')


#TESTING FOR PAYMENT - DO NOT DELETE
    # 4242 4242 4242 4242
    # 12/34
    # 123