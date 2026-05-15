from flask import Flask

from config import Config
from extensions import db, login_manager


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    with app.app_context():
        from models.user import User
        from models.chat import ChatSession, ChatMessage
        from routes.auth import auth_bp
        from routes.chat import chat_bp

        app.register_blueprint(auth_bp)
        app.register_blueprint(chat_bp)

        @login_manager.user_loader
        def load_user(user_id):
            return db.session.get(User, int(user_id))

        db.create_all()

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
