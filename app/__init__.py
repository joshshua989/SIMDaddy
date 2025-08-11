# app/__init__.py

from flask import Flask
from config import Config
from extensions import db, login_manager, csrf, limiter
from auth.routes import auth_bp
from views.routes import views_bp
from flask_migrate import Migrate
from app.dv import dv_bp  # DV blueprint lives in app/dv

migrate = Migrate()

def create_app():
    app = Flask(
        __name__,
        template_folder="../templates",  # unified templates root
        static_folder="../static"       # unified static root
    )
    app.config.from_object(Config)

    # --- Extensions ---
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    login_manager.login_view = "auth.login"

    # Import models so Alembic sees them
    from models.user import User, PointsLog, TokenTransaction, Course, Lesson, Purchase  # noqa: F401

    # --- Blueprints ---
    app.register_blueprint(auth_bp)
    app.register_blueprint(views_bp)
    app.register_blueprint(dv_bp, url_prefix="/dv")  # DraftVader pages

    # --- Login manager ---
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # NOTE: Do NOT call db.create_all() when using Flask-Migrate/Alembic
    # with app.app_context():
    #     db.create_all()

    return app
