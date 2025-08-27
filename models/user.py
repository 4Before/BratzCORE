from utils.extensions import db
from sqlalchemy.types import JSON
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    account_type = db.Column(db.String(50), nullable=False, index=True)
    privileges = db.Column(JSON, nullable=False, default=dict)
    profile = db.Column(JSON, nullable=True, default=dict)

    def __init__(self, email: str, account_type: str, privileges: dict | None = None, profile: dict | None = None):
        self.email = email
        self.account_type = account_type
        self.privileges = privileges or {}
        self.profile = profile or {}

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User {self.id} {self.email} ({self.account_type})>"
