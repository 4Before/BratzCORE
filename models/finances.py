from utils.extensions import db 
from datetime import datetime

class Sell(db.Model):
    __tablename__ = 'sells'
    id = db.Column(db.String(36), primary_key=True)
    id_caixa = db.Column(db.String(50), nullable=False)
    operator = db.Column(db.String(100), nullable=False)
    sell_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    total_value = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    received_value = db.Column(db.Float)
    change = db.Column(db.Float)
    items = db.relationship('ItemSold', backref='sell', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'sell_id': self.id,
            'cashier_id': self.id_caixa,
            'operator': self.operator,
            'sell_time': self.sell_time.isoformat() + 'Z', # Padrão ISO 8601, bom para frontends
            'total_value': self.total_value,
            'payment_method': self.payment_method,
            'received_value': self.received_value,
            'change': self.change,
            'items': [item.to_dict() for item in self.items] # Inclui os detalhes dos itens vendidos
        }

class ItemSold(db.Model):
    __tablename__ = 'sold_items'
    id = db.Column(db.Integer, primary_key=True)
    sell_id = db.Column(db.String(36), db.ForeignKey('sells.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    product_name = db.Column(db.String(150), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_value = db.Column(db.Float, nullable=False)
    total_value = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            'product_id': self.product_id,
            'product_name': self.product_name,
            'quantity': self.quantity,
            'unit_value': self.unit_value,
            'total_value': self.total_value
        }
