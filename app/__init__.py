
# app/__init__.py

from flask import Flask
from config import Config
from extensions import db, login_manager, csrf, limiter
from auth.routes import auth_bp
from views.routes import views_bp
from flask_migrate import Migrate
from app.dv import dv_bp

migrate = Migrate()

def create_app():
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static"
    )
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)

    # Make sure models are imported so migrations see them
    from models.user import User, PointsLog, TokenTransaction, Course, Lesson, Purchase  # noqa

    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    login_manager.login_view = 'auth.login'

    app.register_blueprint(auth_bp)
    app.register_blueprint(views_bp)
    app.register_blueprint(dv_bp, url_prefix="/dv")

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # DO NOT call db.create_all() when using migrations
    # with app.app_context():
    #     db.create_all()

    return app
