from utils.extensions import db
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
    desc = db.Column(JSON, nullable=True, default=dict)

    def __repr__(self) -> str:
        return f"<Product {self.id} {self.item}>"

    def to_dict(self):
        return {
            "id": self.id,
            "item": self.item,
            "brand": self.brand,
            "purchase_value": self.purchase_value,
            "sale_value": self.sale_value,
            "expiration_date": str(self.expiration_date) if self.expiration_date else None,
            "desc": self.desc
        }