from flask import Flask
from config import Config
from utils.extensions import db, migrate 
from routes.auth import auth_bp
from routes.accounts import accounts_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)


    app.register_blueprint(auth_bp, url_prefix="/bratz/auth")
    app.register_blueprint(accounts_bp, url_prefix="/bratz")

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)