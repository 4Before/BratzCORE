from utils.extensions import db

stock_item = db.Table('stock_item',
    db.Column('stock_id', db.Integer, db.ForeignKey('stock.id'), primary_key=True),
    db.Column('product_id', db.Integer, db.ForeignKey('product.id'), primary_key=True),
    db.Column('quantity', db.Integer, nullable=False, default=0)
)

class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.String(255), nullable=True)
    
    products = db.relationship('Product', secondary=stock_item, lazy='subquery',
                            backref=db.backref('stocks', lazy=True))

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description
        }