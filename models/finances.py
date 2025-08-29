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

class ItemSold(db.Model):
    __tablename__ = 'sold_items'
    id = db.Column(db.Integer, primary_key=True)
    sell_id = db.Column(db.String(36), db.ForeignKey('sells.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    product_name = db.Column(db.String(150), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_value = db.Column(db.Float, nullable=False)
    total_value = db.Column(db.Float, nullable=False)
