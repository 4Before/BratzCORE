from flask import Flask
from config import Config
from utils.extensions import db, migrate
from utils.error_handling import register_error_handlers
from routes import accounts_bp, products_bp, clients_bp, finances_bp, auth_bp, stocks_bp

ALL_BLUEPRINTS = [
    accounts_bp,
    products_bp,
    clients_bp,
    finances_bp,
    auth_bp,
    stocks_bp
]

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)

    for blueprint in ALL_BLUEPRINTS:
        app.register_blueprint(blueprint, url_prefix="/bratz")

    register_error_handlers(app)

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)