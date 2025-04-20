from flask import Blueprint, request, jsonify
from propelauth_flask import current_user
from models import db, Conversation, Message, User
from app import socketio




def create_message_routes(auth):
   bp = Blueprint('message_routes', __name__)


   @bp.route('/conversations', methods=['GET'])
   @auth.require_user
   def list_conversations():
       me = User.query.filter_by(propel_user_id=current_user.user_id).first()
       convos = Conversation.query.filter(
           (Conversation.user_a_id == me.id) | (Conversation.user_b_id == me.id)
       ).all()
       return jsonify([c.to_dict(me.id) for c in convos]), 200


   @bp.route('/conversations', methods=['POST'])
   @auth.require_user
   def start_conversation():
       other_pid = request.get_json().get('with_propel_user_id')
       me = User.query.filter_by(propel_user_id=current_user.user_id).first()
       other = User.query.filter_by(propel_user_id=other_pid).first_or_404()
       convo = Conversation.query.filter(
           ((Conversation.user_a_id == me.id) & (Conversation.user_b_id == other.id)) |
           ((Conversation.user_a_id == other.id) & (Conversation.user_b_id == me.id))
       ).first()
       if not convo:
           convo = Conversation(user_a_id=me.id, user_b_id=other.id)
           db.session.add(convo)
           db.session.commit()
       return jsonify({'conversation_id': convo.id}), 201


   @bp.route('/conversations/<int:cid>/messages', methods=['GET'])
   @auth.require_user
   def get_messages(cid):
       convo = Conversation.query.get_or_404(cid)
       me = User.query.filter_by(propel_user_id=current_user.user_id).first()
       if me.id not in (convo.user_a_id, convo.user_b_id):
           return jsonify({'error':'Unauthorized'}), 403
       return jsonify([m.to_dict() for m in convo.messages]), 200


   @bp.route('/conversations/<int:cid>/messages', methods=['POST'])
   @auth.require_user
   def send_message(cid):
       data = request.get_json() or {}
       body = data.get('body', '').strip()
       convo = Conversation.query.get_or_404(cid)
       me = User.query.filter_by(propel_user_id=current_user.user_id).first()
       if me.id not in (convo.user_a_id, convo.user_b_id) or not body:
           return jsonify({'error':'Invalid request'}), 400
       msg = Message(conversation_id=cid, sender_id=me.id, body=body)
       db.session.add(msg)
       db.session.commit()
       payload = msg.to_dict()
       socketio.emit('new_message', {
           'conversation_id': cid,
           'message': payload
       }, room=str(cid))
       return jsonify(payload), 201


   return bp