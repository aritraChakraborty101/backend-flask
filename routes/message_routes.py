from flask_socketio import emit, join_room
from app import socketio
from models import Message, db, User
from propelauth_flask import current_user
from flask import Blueprint, request, jsonify

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

    # Standardize the room name by sorting sender_id and receiver_id alphabetically
    room = f"conversation_{'_'.join(sorted([sender_id, receiver_id]))}"

    print(f"Message received for room {room}: {data}")  # Debugging: Log the message data

    # Save the message to the database
    message = Message(sender_id=sender_id, receiver_id=receiver_id, content=content)
    db.session.add(message)
    db.session.commit()

    print(f"Message saved to database: {message.content}")  # Debugging: Log the saved message

    # Emit the message to the room
    emit('receive_message', {
        'sender_id': sender_id,
        'receiver_id': receiver_id,
        'content': content,
        'created_at': message.created_at.isoformat()
    }, room=room)
    print(f"Message emitted to room {room}")  # Debugging: Log the emission


# HTTP Routes
def create_message_routes(auth):
    bp = Blueprint('messages', __name__)

    @bp.route('/conversations', methods=['GET'])
    @auth.require_user
    def get_conversations():
        user_id = request.args.get('user_id')  # Get user_id from query parameters
        if not user_id:
            return jsonify({"error": "User ID is required"}), 400

        # Query for conversations
        conversations = db.session.query(
            db.case(
                (Message.sender_id == user_id, Message.receiver_id),  # Pass as positional arguments
                else_=Message.sender_id
            ).label('other_user_id'),
            db.func.max(Message.created_at).label('last_message_time')
        ).filter(
            (Message.sender_id == user_id) | (Message.receiver_id == user_id)
        ).group_by('other_user_id').all()

        # Replace with actual user fetching logic
        users = {conv.other_user_id: f"User {conv.other_user_id}" for conv in conversations}
        return jsonify({"conversations": users}), 200
    

    @bp.route('/conversation', methods=['GET'])
    @auth.require_user
    def get_conversation():
        sender_id = request.args.get('sender_id')  # Get sender_id from query parameters
        receiver_id = request.args.get('receiver_id')  # Get receiver_id from query parameters

        if not sender_id or not receiver_id:
            return jsonify({"error": "Both sender_id and receiver_id are required"}), 400

        # Query messages sent by the sender to the receiver
        sent_messages = Message.query.filter(
            (Message.sender_id == sender_id) & (Message.receiver_id == receiver_id)
        ).all()

        # Query messages sent by the receiver to the sender
        received_messages = Message.query.filter(
            (Message.sender_id == receiver_id) & (Message.receiver_id == sender_id)
        ).all()

        # Merge the two lists
        all_messages = sent_messages + received_messages

        # Sort the merged list by created_at
        all_messages.sort(key=lambda msg: msg.created_at)

        # Return the sorted messages
        return jsonify([{
            "id": msg.id,
            "sender_id": msg.sender_id,
            "receiver_id": msg.receiver_id,
            "content": msg.content,
            "created_at": msg.created_at.isoformat()
        } for msg in all_messages]), 200

    return bp