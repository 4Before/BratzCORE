from utils.extensions import db
from sqlalchemy.types import JSON

class Client(db.Model):
    __tablename__ = "clients"

    id = db.Column(db.Integer, primary_key=True)
    cpf = db.Column(db.String(14), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    nickname = db.Column(db.String(100))
    discounts = db.Column(JSON, default=dict)
    phone = db.Column(db.String(20))
    notes = db.Column(db.Text)

    def to_dict(self):
        """Converte o objeto Client para um dicionário."""
        return {
            "id": self.id,
            "cpf": self.cpf,
            "name": self.name,
            "nickname": self.nickname,
            "discounts": self.discounts,
            "phone": self.phone,
            "notes": self.notes,
        }