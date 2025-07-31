from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)

    from routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/bratz/auth")
    from routes.accounts import accounts_bp
    app.register_blueprint(accounts_bp, url_prefix="/bratz")

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
