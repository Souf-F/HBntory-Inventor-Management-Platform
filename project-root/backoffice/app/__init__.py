"""
HBntory — Flask application factory.

Wires the app, the config, and the shared SQLAlchemy instance together.
"""

from flask import Flask
from flask_login import LoginManager
from flask_cors import CORS

from app.config import Config
from app.models import db, User


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    CORS(app, supports_credentials=True, origins=["http://127.0.0.1:5500", "http://localhost:5500"])

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # --- Blueprints ---
    from routes.auth import auth_bp
    from routes.stock import stock_bp
    from routes.users import users_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(stock_bp)
    app.register_blueprint(users_bp)

    return app