"""
Modelo de Dados para Fornecedores
---------------------------------
Representa um fornecedor ou distribuidor de produtos no sistema.
"""

from utils.extensions import db

class Supplier(db.Model):
    __tablename__ = "suppliers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    cnpj = db.Column(db.String(18), unique=True, nullable=True) # Ex: 00.000.000/0001-00
    contact_person = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    address = db.Column(db.Text, nullable=True)

    # Relação One-to-Many: Um fornecedor pode ter muitos produtos.
    # O backref 'supplier' cria um atributo 'supplier' em cada objeto Product.
    products = db.relationship('Product', backref='supplier', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        """Converte o objeto Supplier para um dicionário serializável."""
        return {
            "id": self.id,
            "name": self.name,
            "cnpj": self.cnpj,
            "contact_person": self.contact_person,
            "phone": self.phone,
            "email": self.email,
            "address": self.address
        }