from flask import Flask
from config import Config
from utils.extensions import db, migrate
from routes.auth import auth_bp
from routes.accounts import accounts_bp
from utils.error_handling import register_error_handlers

app = Flask(__name__)

def create_app():
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    register_error_handlers(app)


    app.register_blueprint(auth_bp, url_prefix="/bratz/auth")
    app.register_blueprint(accounts_bp, url_prefix="/bratz")
    

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)