# app.py

from flask import Flask
from config import Config
from app import db, login_manager, csrf, limiter

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    login_manager.login_view = 'auth.login'

    # Register Blueprints
    from auth.routes import auth_bp
    from views.routes import views_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(views_bp)

    # Register user loader (after importing User correctly)
    from models.user import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    with app.app_context():
        db.create_all()

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
