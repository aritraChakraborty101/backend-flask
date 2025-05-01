from flask_socketio import emit, join_room
from app import socketio
import os
# from models import Message, db, User
from propelauth_flask import current_user
from flask import Blueprint, request, jsonify
from supabase import create_client, Client


url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

@socketio.on('join')
def handle_join(data):
    sender_id = data['sender_id']
    receiver_id = data['receiver_id']

    # Standardize the room name by sorting sender_id and receiver_id alphabetically
    room = f"conversation_{'_'.join(sorted([sender_id, receiver_id]))}"
    print(f"User joined room: {room}")  # Debugging: Log the room being joined

    join_room(room)
    emit('status', {'message': f'User has joined room {room}'}, room=room)

@socketio.on('send_message')
def handle_send_message(data):
    sender_id = data['sender_id']
    receiver_id = data['receiver_id']
    content = data['content']

    room = f"conversation_{'_'.join(sorted([sender_id, receiver_id]))}"

    # Save the message to the database
    result = supabase.table("message").insert({
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "content": content,
        "created_at": "NOW()" 
    }).execute()


    # Extract the saved message
    saved_message = result.data[0]  # Get the first inserted row


    # Emit the message to the room
    emit('receive_message', {
        'sender_id': saved_message["sender_id"],
        'receiver_id': saved_message["receiver_id"],
        'content': saved_message["content"],
        'created_at': saved_message["created_at"]
    }, room=room)
    print(f"Message emitted to room {room}")  # Debugging: Log the emission


# HTTP Routes
def create_message_routes(auth, supabase):
    bp = Blueprint('messages', __name__)

    @bp.route('/conversations', methods=['GET'])
    @auth.require_user
    def get_conversations():
        try:
            user_id = current_user.user_id  # Get the current user's ID

            # Query for conversations where the user is either the sender or receiver
            messages = supabase.table("message").select("*").or_(
                f"sender_id.eq.{user_id},receiver_id.eq.{user_id}"
            ).execute().data

            if not messages:
                return jsonify({"conversations": {}}), 200

            # Extract unique conversation partner IDs
            conversation_partners = {}
            for message in messages:
                other_user_id = (
                    message["receiver_id"] if message["sender_id"] == user_id else message["sender_id"]
                )
                if other_user_id not in conversation_partners:
                    conversation_partners[other_user_id] = message["created_at"]

            # Fetch user details for the conversation partners
            user_ids = list(conversation_partners.keys())
            users = supabase.table("user").select("propel_user_id, name").in_("propel_user_id", user_ids).execute().data
            user_map = {user["propel_user_id"]: user["name"] for user in users}

            # Build the response
            response = {
                other_user_id: user_map.get(other_user_id, "Unknown User")
                for other_user_id in conversation_partners
            }

            return jsonify({"conversations": response}), 200
        except Exception as e:
            print(f"Error in get_conversations: {e}")
            return jsonify({"error": "Internal Server Error"}), 500

    @bp.route('/conversation', methods=['GET'])
    @auth.require_user
    def get_conversation():
        sender_id = request.args.get('sender_id')  # Get sender_id from query parameters
        receiver_id = request.args.get('receiver_id')  # Get receiver_id from query parameters

        if not sender_id or not receiver_id:
            return jsonify({"error": "Both sender_id and receiver_id are required"}), 400
        
        sender_name = supabase.table("user").select("name").eq("propel_user_id", sender_id).execute().data

        # Query messages sent by the sender to the receiver
        sent_messages = supabase.table("message").select("*").eq("sender_id", sender_id).eq("receiver_id", receiver_id).execute().data


        # Query messages sent by the receiver to the sender
        received_messages = supabase.table("message").select("*").eq("sender_id", receiver_id).eq("receiver_id", sender_id).execute().data

        # Merge the two lists
        all_messages = sent_messages + received_messages

        # Sort the merged list by created_at
        all_messages.sort(key=lambda x: x["created_at"])
        print(all_messages)

        # Return the sorted messages
        return jsonify([{
            "id": message["id"],
            "sender_id": message["sender_id"],
            "receiver_id": message["receiver_id"],
            "content": message["content"],
            "created_at": message["created_at"],
            "sender_name": sender_name[0]["name"] if sender_name else "Unknown User"
        } for message in all_messages]), 200
    

    return bp