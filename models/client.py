from utils.extensions import db
from sqlalchemy.types import JSON

class Client(db.Model):
    """
    Representa um cliente no sistema.
    """
    __tablename__ = "clients"

    id = db.Column(db.Integer, primary_key=True)
    cpf = db.Column(db.String(14), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    nickname = db.Column(db.String(100), nullable=True)
    discounts = db.Column(JSON, nullable=True, default=dict)
    phone = db.Column(db.String(20), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Client {self.id} {self.cpf} ({self.name})>"
