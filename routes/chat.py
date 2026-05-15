import json
import os
import random

from flask import Blueprint, Response, current_app, jsonify, redirect, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import desc

from extensions import db
from models.chat import ChatMessage, ChatSession
from services.zhipu import chat_stream

CAT_STATUS_KEYWORDS = ['在干嘛', '在做什么', '干嘛呢', '在干什么', '现在在干嘛', '在忙什么']
CAT_STATUSES = ['发呆', '观察', '撒娇', '睡觉', '玩耍']
CAT_PHOTOS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'cat_photos')

chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/')
@login_required
def index():
    return redirect('/chat')


@chat_bp.route('/chat')
@login_required
def chat_page():
    sessions = (ChatSession.query
                .filter_by(user_id=current_user.id)
                .order_by(desc(ChatSession.created_at))
                .all())
    return render_template('chat.html', sessions=sessions)


@chat_bp.route('/api/sessions', methods=['GET'])
@login_required
def get_sessions():
    sessions = (ChatSession.query
                .filter_by(user_id=current_user.id)
                .order_by(desc(ChatSession.created_at))
                .all())
    return jsonify([{
        'id': s.id,
        'title': s.title,
        'created_at': s.created_at.isoformat(),
    } for s in sessions])


@chat_bp.route('/api/sessions', methods=['POST'])
@login_required
def create_session():
    session = ChatSession(user_id=current_user.id, title='新对话')
    db.session.add(session)
    db.session.commit()
    return jsonify({'id': session.id, 'title': session.title}), 201


@chat_bp.route('/api/sessions/<int:session_id>', methods=['DELETE'])
@login_required
def delete_session(session_id):
    session = ChatSession.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
    ChatMessage.query.filter_by(session_id=session_id).delete()
    db.session.delete(session)
    db.session.commit()
    return jsonify({'ok': True})


@chat_bp.route('/api/sessions/<int:session_id>/messages')
@login_required
def get_messages(session_id):
    session = ChatSession.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
    messages = session.messages.all()
    return jsonify([{
        'id': m.id,
        'role': m.role,
        'content': m.content,
        'created_at': m.created_at.isoformat(),
    } for m in messages])


@chat_bp.route('/api/chat/<int:session_id>', methods=['POST'])
@login_required
def send_message(session_id):
    session = ChatSession.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
    data = request.get_json()
    user_content = data.get('content', '').strip()

    if not user_content:
        return jsonify({'error': '消息不能为空'}), 400

    user_msg = ChatMessage(session_id=session_id, role='user', content=user_content)
    db.session.add(user_msg)

    if session.title == '新对话':
        session.title = user_content[:20] + ('...' if len(user_content) > 20 else '')

    db.session.commit()

    history = session.messages.order_by(ChatMessage.created_at).all()
    api_messages = [{'role': m.role, 'content': m.content} for m in history]

    api_key = current_app.config['ZHIPU_API_KEY']
    app = current_app._get_current_object()

    # 判断是否问在干嘛，提前选好状态和对应照片
    ask_status = any(kw in user_content for kw in CAT_STATUS_KEYWORDS)
    chosen_status = random.choice(CAT_STATUSES) if ask_status else None
    chosen_photo = None
    if chosen_status:
        status_dir = os.path.join(CAT_PHOTOS_DIR, chosen_status)
        photos = [f for f in os.listdir(status_dir) if f.endswith(('.jpg', '.png', '.gif'))]
        if photos:
            chosen_photo = f'/static/cat_photos/{chosen_status}/{random.choice(photos)}'

    extra_system = ''
    if chosen_status:
        extra_system = f'用户在问你现在在干嘛，你现在正在{chosen_status}，请用可爱的语气告诉用户你正在{chosen_status}。'

    def generate():
        full_reply = ''
        try:
            for chunk in chat_stream(api_key, api_messages, extra_system):
                full_reply += chunk
                yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
            return

        with app.app_context():
            assistant_msg = ChatMessage(session_id=session_id, role='assistant', content=full_reply)
            db.session.add(assistant_msg)
            db.session.commit()

        yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"

        if chosen_photo:
            yield f"data: {json.dumps({'photo': chosen_photo}, ensure_ascii=False)}\n\n"

    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})
