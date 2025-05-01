from flask import Blueprint, request, jsonify
from propelauth_flask import current_user
from datetime import datetime

def create_course_routes(auth, supabase):
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
            existing_course = supabase.table("course").select("*").eq("name", name).execute().data
            if existing_course:
                return jsonify({"error": "Course already exists"}), 400

            # Add the course
            supabase.table("course").insert({"name": name}).execute()
            return jsonify({"message": "Course added successfully!"}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # Fetch all courses
    @bp.route("/courses", methods=["GET"])
    def get_courses():
        try:
            # Fetch all courses
            courses = supabase.table("course").select("*").execute().data
            course_list = [{"id": course["id"], "name": course["name"]} for course in courses]
            return jsonify(course_list), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # Fetch all posts for a course
    @bp.route("/courses/<int:course_id>/posts", methods=["GET"])
    def get_posts(course_id):
        try:
            # Fetch the course name
            course = supabase.table("course").select("name").eq("id", course_id).execute().data
            if not course:
                return jsonify({"error": "Course not found"}), 404
            course_name = course[0]["name"]

            # Fetch posts for the course
            posts = supabase.table("post").select("*").eq("course_id", course_id).execute().data
            post_list = []
            for post in posts:
                user = supabase.table("user").select("name").eq("propel_user_id", post["user_id"]).execute().data
                author_name = user[0]["name"] if user else "Unknown User"

                post_list.append({
                    "id": post["id"],
                    "title": post["title"],
                    "content": post["content"],
                    "author": author_name,
                    "user_id": post["user_id"],
                    "upvotes": post["upvotes"],
                    "downvotes": post["downvotes"],
                    "created_at": post["created_at"],
                    "course_name": course_name,
                })

            return jsonify(post_list), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # Create a new post
    @bp.route("/courses/<int:course_id>/posts", methods=["POST"])
    @auth.require_user
    def create_post(course_id):
        try:
            data = request.get_json()
            title = data.get("title")
            content = data.get("content")
            user_id = current_user.user_id  # Get user ID from the current user

            if not title or not content:
                return jsonify({"error": "Title and content are required"}), 400

            # Insert the post into the database
            supabase.table("post").insert({
                "course_id": course_id,
                "user_id": user_id,
                "title": title,
                "content": content,
                "upvotes": 0,
                "downvotes": 0,
                "created_at": datetime.utcnow().isoformat()
            }).execute()

            return jsonify({"message": "Post created successfully!"}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # Vote a post
    @bp.route("/posts/<int:post_id>/vote", methods=["POST"])
    @auth.require_user
    def vote_post(post_id):
        try:
            data = request.get_json()
            user_id = current_user.user_id  # Get user ID from the current user
            vote_type = data.get("vote_type")  # "upvote" or "downvote"

            if vote_type not in ["upvote", "downvote"]:
                return jsonify({"error": "Invalid vote type"}), 400

            # Check if the user has already voted on this post
            existing_vote = supabase.table("vote").select("*").eq("post_id", post_id).eq("user_id", user_id).execute().data

            if existing_vote:
                if existing_vote[0]["vote_type"] == vote_type:
                    # Cancel the vote
                    supabase.table("vote").delete().eq("id", existing_vote[0]["id"]).execute()

                    # Fetch the current post
                    post = supabase.table("post").select("*").eq("id", post_id).execute().data
                    if not post:
                        return jsonify({"error": "Post not found"}), 404

                    # Update the upvotes or downvotes count
                    if vote_type == "upvote":
                        new_upvotes = max(0, post[0]["upvotes"] - 1)
                        supabase.table("post").update({"upvotes": new_upvotes}).eq("id", post_id).execute()
                    elif vote_type == "downvote":
                        new_downvotes = max(0, post[0]["downvotes"] - 1)
                        supabase.table("post").update({"downvotes": new_downvotes}).eq("id", post_id).execute()

                    return jsonify({"message": f"{vote_type.capitalize()} canceled"}), 200
                else:
                    # Change the vote type
                    supabase.table("vote").update({"vote_type": vote_type}).eq("id", existing_vote[0]["id"]).execute()

                    # Fetch the current post
                    post = supabase.table("post").select("*").eq("id", post_id).execute().data
                    if not post:
                        return jsonify({"error": "Post not found"}), 404

                    # Update the upvotes and downvotes count
                    if vote_type == "upvote":
                        new_upvotes = post[0]["upvotes"] + 1
                        new_downvotes = max(0, post[0]["downvotes"] - 1)
                        supabase.table("post").update({"upvotes": new_upvotes, "downvotes": new_downvotes}).eq("id", post_id).execute()
                    elif vote_type == "downvote":
                        new_downvotes = post[0]["downvotes"] + 1
                        new_upvotes = max(0, post[0]["upvotes"] - 1)
                        supabase.table("post").update({"downvotes": new_downvotes, "upvotes": new_upvotes}).eq("id", post_id).execute()

                    return jsonify({"message": f"Vote changed to {vote_type}"}), 200

            # Add a new vote
            supabase.table("vote").insert({
                "post_id": post_id,
                "user_id": user_id,
                "vote_type": vote_type,
                "created_at": datetime.utcnow().isoformat()
            }).execute()

            # Fetch the current post
            post = supabase.table("post").select("*").eq("id", post_id).execute().data
            if not post:
                return jsonify({"error": "Post not found"}), 404

            # Update the upvotes or downvotes count
            if vote_type == "upvote":
                new_upvotes = post[0]["upvotes"] + 1
                supabase.table("post").update({"upvotes": new_upvotes}).eq("id", post_id).execute()
            elif vote_type == "downvote":
                new_downvotes = post[0]["downvotes"] + 1
                supabase.table("post").update({"downvotes": new_downvotes}).eq("id", post_id).execute()

            return jsonify({"message": f"Post {vote_type}d successfully"}), 201
        except Exception as e:
            print(f"Error in vote_post: {e}")
            return jsonify({"error": str(e)}), 500
    

    @bp.route("/posts/<int:post_id>", methods=["PUT"])
    @auth.require_user
    def edit_post(post_id):
        try:
            data = request.get_json()
            user_id = current_user.user_id  # Get user ID from the current user
            title = data.get("title")
            content = data.get("content")

            if not title or not content:
                return jsonify({"error": "Title and content are required"}), 400

            # Fetch the post
            post = supabase.table("post").select("*").eq("id", post_id).execute().data
            if not post:
                return jsonify({"error": "Post not found"}), 404

            # Ensure the user is the author of the post
            if post[0]["user_id"] != user_id:
                return jsonify({"error": "You are not authorized to edit this post"}), 403

            # Update the post
            supabase.table("post").update({"title": title, "content": content}).eq("id", post_id).execute()

            return jsonify({"message": "Post updated successfully!"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    

    @bp.route("/posts/<int:post_id>", methods=["DELETE"])
    @auth.require_user
    def delete_post(post_id):
        try:
            user_id = current_user.user_id  # Get user ID from the current user

            # Fetch the post
            post = supabase.table("post").select("*").eq("id", post_id).execute().data
            if not post:
                return jsonify({"error": "Post not found"}), 404

            # Ensure the user is the author of the post
            if post[0]["user_id"] != user_id:
                return jsonify({"error": "You are not authorized to delete this post"}), 403

            # Delete the post
            supabase.table("post").delete().eq("id", post_id).execute()

            return jsonify({"message": "Post deleted successfully!"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    # Create a new comment
    @bp.route("/posts/<int:post_id>/comments", methods=["POST"])
    @auth.require_user
    def create_comment(post_id):
        try:
            data = request.get_json()
            user_id = current_user.user_id  # Get user ID from the current user
            content = data.get("content")

            if not content:
                return jsonify({"error": "Content is required"}), 400

            # Insert the comment into the database
            supabase.table("comment").insert({
                "post_id": post_id,
                "user_id": user_id,
                "content": content,
                "created_at": datetime.utcnow().isoformat()
            }).execute()

            return jsonify({"message": "Comment added successfully!"}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        

    # Fetch all comments for a post
    @bp.route("/posts/<int:post_id>/comments", methods=["GET"])
    def get_comments(post_id):
        try:
            # Fetch all comments for the post, ordered by created_at in ascending order
            comments = supabase.table("comment").select("*").eq("post_id", post_id).order("created_at", desc=False).execute().data

            # if not comments:
            #     return jsonify({"error": "No comments found"}), 404

            # Fetch user details for each comment
            comments_data = []
            for comment in comments:
                user = supabase.table("user").select("name").eq("propel_user_id", comment["user_id"]).execute().data
                author_name = user[0]["name"] if user else "Unknown User"

                comments_data.append({
                    "id": comment["id"],
                    "user_id": comment["user_id"],
                    "author": author_name,
                    "content": comment["content"],
                    "created_at": comment["created_at"]
                })

            return jsonify(comments_data), 200
        except Exception as e:
            print(f"Error in get_comments: {e}")
            return jsonify({"error": str(e)}), 500
        
    # Edit a comment
    @bp.route("/comments/<int:comment_id>", methods=["PUT"])
    @auth.require_user
    def edit_comment(comment_id):
        try:
            data = request.get_json()
            user_id = current_user.user_id  # Get user ID from the current user
            content = data.get("content")

            if not content:
                return jsonify({"error": "Content is required"}), 400

            # Fetch the comment
            comment = supabase.table("comment").select("*").eq("id", comment_id).execute().data
            if not comment:
                return jsonify({"error": "Comment not found"}), 404

            # Ensure the user is the author of the comment
            if comment[0]["user_id"] != user_id:
                return jsonify({"error": "You are not authorized to edit this comment"}), 403

            # Update the comment
            supabase.table("comment").update({"content": content}).eq("id", comment_id).execute()

            # Fetch the updated comment
            updated_comment = supabase.table("comment").select("*").eq("id", comment_id).execute().data
            if not updated_comment:
                return jsonify({"error": "Failed to fetch updated comment"}), 500

            return jsonify({"message": "Comment updated successfully!", "comment": updated_comment[0]}), 200
        except Exception as e:
            print(f"Error in edit_comment: {e}")
            return jsonify({"error": str(e)}), 500
        
    # Delete a comment
    @bp.route("/comments/<int:comment_id>", methods=["DELETE"])
    @auth.require_user
    def delete_comment(comment_id):
        try:
            user_id = current_user.user_id  # Get user ID from the current user

            # Fetch the comment
            comment = supabase.table("comment").select("*").eq("id", comment_id).execute().data
            if not comment:
                return jsonify({"error": "Comment not found"}), 404

            # Ensure the user is the author of the comment
            if comment[0]["user_id"] != user_id:
                return jsonify({"error": "You are not authorized to delete this comment"}), 403

            # Delete the comment
            supabase.table("comment").delete().eq("id", comment_id).execute()

            return jsonify({"message": "Comment deleted successfully!"}), 200
        except Exception as e:
            print(f"Error in delete_comment: {e}")
            return jsonify({"error": str(e)}), 500
    

    return bp

    