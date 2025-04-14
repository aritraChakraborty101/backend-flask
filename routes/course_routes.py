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
            course_name = Course.query.filter_by(id=course_id).first()
            if not course_name:
                return jsonify({"error": "Course not found"}), 404
            course_name = course_name.name

            # Fetch posts for the course
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
                    "course_name": course_name,
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
    

    @bp.route("/posts/<int:post_id>", methods=["DELETE"])
    @auth.require_user
    def delete_post(post_id):
        data = request.get_json()
        user_id = data.get("user_id")

        post = Post.query.get(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404

        if post.user_id != user_id:
            return jsonify({"error": "You are not authorized to delete this post"}), 403

        db.session.delete(post)
        db.session.commit()
        return jsonify({"message": "Post deleted successfully!"}), 200
    
    # Create a new comment
    @bp.route("/posts/<int:post_id>/comments", methods=["POST"])
    @auth.require_user
    def create_comment(post_id):
        """Create a comment for a post."""
        data = request.get_json()
        user_id = data.get("user_id")
        content = data.get("content")

        if not content:
            return jsonify({"error": "Content is required"}), 400

        try:
            comment = Comment(post_id=post_id, user_id=user_id, content=content)
            db.session.add(comment)
            db.session.commit()
            return jsonify({"message": "Comment added successfully!"}), 201
        except Exception as e:
            return jsonify({"error": "Failed to add comment", "details": str(e)}), 500
        

    # Fetch all comments for a post
    @bp.route("/posts/<int:post_id>/comments", methods=["GET"])
    def get_comments(post_id):
        """Fetch all comments for a post."""
        try:
            comments = Comment.query.filter_by(post_id=post_id).order_by(Comment.created_at.asc()).all()
            comments_data = [
                {
                    "id": comment.id,
                    "user_id": comment.user_id,
                    "author": User.query.filter_by(propel_user_id=comment.user_id).first().name,
                    "content": comment.content,
                    "created_at": comment.created_at
                }
                for comment in comments
            ]
            return jsonify(comments_data), 200
        except Exception as e:
            return jsonify({"error": "Failed to fetch comments", "details": str(e)}), 500
        
    # Edit a comment
    @bp.route("/comments/<int:comment_id>", methods=["PUT"])
    @auth.require_user
    def edit_comment(comment_id):
        """Edit a comment."""
        data = request.get_json()
        user_id = data.get("user_id")
        content = data.get("content")

        if not content:
            return jsonify({"error": "Content is required"}), 400

        comment = Comment.query.get(comment_id)
        if not comment:
            return jsonify({"error": "Comment not found"}), 404

        if comment.user_id != user_id:
            return jsonify({"error": "You are not authorized to edit this comment"}), 403

        try:
            comment.content = content
            db.session.commit()
            return jsonify({"message": "Comment updated successfully!"}), 200
        except Exception as e:
            return jsonify({"error": "Failed to update comment", "details": str(e)}), 500
        
    # Delete a comment
    @bp.route("/comments/<int:comment_id>", methods=["DELETE"])
    @auth.require_user
    def delete_comment(comment_id):
        """Delete a comment."""
        data = request.get_json()
        user_id = data.get("user_id")

        comment = Comment.query.get(comment_id)
        if not comment:
            return jsonify({"error": "Comment not found"}), 404

        if comment.user_id != user_id:
            return jsonify({"error": "You are not authorized to delete this comment"}), 403

        try:
            db.session.delete(comment)
            db.session.commit()
            return jsonify({"message": "Comment deleted successfully!"}), 200
        except Exception as e:
            return jsonify({"error": "Failed to delete comment", "details": str(e)}), 500
    

    return bp

    