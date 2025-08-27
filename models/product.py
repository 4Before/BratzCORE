from routes.extensions import db
from sqlalchemy.types import JSON

class Product(db.Model):
    """
    Representa um produto no estoque.
    """
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    item = db.Column(db.String(255), nullable=False, index=True)
    brand = db.Column(db.String(100), nullable=True)
    purchase_value = db.Column(db.Float, nullable=True)
    sale_value = db.Column(db.Float, nullable=False)
    expiration_date = db.Column(db.Date, nullable=True)
    
    # Adicionando um campo para metadados ou informações adicionais, se necessário
    desc = db.Column(JSON, nullable=True, default=dict)

    def __repr__(self) -> str:
        return f"<Product {self.id} {self.item}>"