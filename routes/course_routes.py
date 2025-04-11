from flask import Blueprint, request, jsonify
from models import db, Course, Post, Comment, User, Vote
from propelauth_flask import current_user
from datetime import datetime

def create_course_routes(auth):
    bp = Blueprint("course_routes", __name__)

    #add course
    @bp.route("add_course", methods=["POST"])
    @auth.require_user
    def add_course():
        try:
            data = request.get_json()
            name = data.get("name")
            if not name:
                return jsonify({"error": "Course name is required"}), 400
            
            # Check if course already exists
            existing_course = Course.query.filter_by(name=name).first()
            if existing_course:
                return jsonify({"error": "Course already exists"}), 400
            
            course = Course(name=name)
            db.session.add(course)
            db.session.commit()
            return jsonify({"message": "Course added successfully!"}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # Fetch all courses
    @bp.route("/courses", methods=["GET"])
    def get_courses():
        courses = Course.query.all()
        course_list = [{"id": course.id, "name": course.name} for course in courses]
        return jsonify(course_list), 200

    # Fetch all posts for a course
    @bp.route("/courses/<int:course_id>/posts", methods=["GET"])
    def get_posts(course_id):
        """Fetch all posts for a course"""
        try:
            posts = Post.query.filter_by(course_id=course_id).all()
            post_list = []
            for post in posts:
                user = User.query.filter_by(propel_user_id=post.user_id).first()  # Query by propel_user_id
                if not user:
                    author_name = "Unknown User"  # Handle missing user gracefully
                else:
                    author_name = user.name

                post_list.append({
                    "id": post.id,
                    "title": post.title,
                    "content": post.content,
                    "author": author_name,
                    "user_id": post.user_id,
                    "upvotes": post.upvotes,
                    "downvotes": post.downvotes,
                    "created_at": post.created_at,
                })

            return jsonify(post_list), 200
        except Exception as e:
            print(f"Error fetching posts: {e}")  # Log the error
            return jsonify({"error": "Internal Server Error"}), 500

    # Create a new post
    @bp.route("/courses/<int:course_id>/posts", methods=["POST"])
    @auth.require_user
    def create_post(course_id):
        """Create a new post for a course"""
        data = request.get_json()
        title = data.get("title")
        content = data.get("content")
        user_id = data.get("user_id") 

        if not title or not content or not user_id:
            print(f"Title: {title}, Content: {content}, User ID: {user_id}")
            return jsonify({"error": "Title, content, and user_id are required"}), 400

        post = Post(course_id=course_id, user_id=user_id, title=title, content=content)
        db.session.add(post)
        db.session.commit()

        return jsonify({"message": "Post created successfully!"}), 201

    # Vote a post
    @bp.route("/posts/<int:post_id>/vote", methods=["POST"])
    @auth.require_user
    def vote_post(post_id):
        """Handle upvote or downvote for a post"""
        data = request.get_json()
        user_id = data.get("user_id")
        vote_type = data.get("vote_type")  # "upvote" or "downvote"

        if vote_type not in ["upvote", "downvote"]:
            return jsonify({"error": "Invalid vote type"}), 400

        # Check if the user has already voted on this post
        existing_vote = Vote.query.filter_by(post_id=post_id, user_id=user_id).first()

        if existing_vote:
            if existing_vote.vote_type == vote_type:
                # If the user clicks the same vote type again, cancel the vote
                db.session.delete(existing_vote)
                post = Post.query.get(post_id)
                if vote_type == "upvote":
                    post.upvotes -= 1
                elif vote_type == "downvote":
                    post.downvotes -= 1
                db.session.commit()
                return jsonify({"message": f"{vote_type.capitalize()} canceled"}), 200
            else:
                # Change the vote type
                existing_vote.vote_type = vote_type
                post = Post.query.get(post_id)
                if vote_type == "upvote":
                    post.upvotes += 1
                    post.downvotes -= 1
                elif vote_type == "downvote":
                    post.downvotes += 1
                    post.upvotes -= 1
                db.session.commit()
                return jsonify({"message": f"Vote changed to {vote_type}"}), 200

        # Add a new vote
        vote = Vote(post_id=post_id, user_id=user_id, vote_type=vote_type)
        db.session.add(vote)

        # Update the post's upvote/downvote count
        post = Post.query.get(post_id)
        if vote_type == "upvote":
            post.upvotes += 1
        elif vote_type == "downvote":
            post.downvotes += 1

        db.session.commit()
        return jsonify({"message": f"Post {vote_type}d successfully"}), 201
    

    @bp.route("/posts/<int:post_id>", methods=["PUT"])
    @auth.require_user
    def edit_post(post_id):
        """Edit an existing post"""
        data = request.get_json()
        user_id = data.get("user_id")
        title = data.get("title")
        content = data.get("content")

        if not title or not content:
            return jsonify({"error": "Title and content are required"}), 400

        # Fetch the post
        post = Post.query.get(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404

        # Ensure the user is the author of the post
        if post.user_id != user_id:
            return jsonify({"error": "You are not authorized to edit this post"}), 403

        # Update the post
        post.title = title
        post.content = content
        db.session.commit()

        return jsonify({"message": "Post updated successfully!"}), 200
    

    return bp