import json

from flask import Blueprint, Response, current_user, jsonify, login_required, redirect, render_template, request
from sqlalchemy import desc

from app import db
from models.chat import ChatMessage, ChatSession
from services.zhipu import chat_stream

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

    # 保存用户消息
    user_msg = ChatMessage(session_id=session_id, role='user', content=user_content)
    db.session.add(user_msg)

    # 更新会话标题（首条消息的前20字）
    if session.title == '新对话':
        session.title = user_content[:20] + ('...' if len(user_content) > 20 else '')

    db.session.commit()

    # 构建对话历史
    history = session.messages.order_by(ChatMessage.created_at).all()
    api_messages = [{'role': m.role, 'content': m.content} for m in history]

    def generate():
        full_reply = ''
        try:
            for chunk in chat_stream(api_messages):
                full_reply += chunk
                yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
            return

        # 保存AI回复
        assistant_msg = ChatMessage(session_id=session_id, role='assistant', content=full_reply)
        db.session.add(assistant_msg)
        db.session.commit()

        yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"

    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})
