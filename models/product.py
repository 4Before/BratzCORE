"""
Modelo de Dados para Produtos
-----------------------------
Este módulo define o modelo `Product`, que é central para a aplicação.
Ele representa os itens únicos do catálogo que podem ser vendidos,
independentemente de sua quantidade ou localização no estoque.
"""

from utils.extensions import db
from sqlalchemy.types import JSON

class Product(db.Model):
    """
    Representa um produto no catálogo da loja.
    
    Esta tabela armazena todas as informações intrínsecas de um produto, como
    seu nome, marca, preços e categoria. A quantidade em estoque é gerenciada
    através da relação com o modelo `Stock`.
    """
    __tablename__ = "products"

    # --- Colunas da Tabela ---
    id = db.Column(db.Integer, primary_key=True)
    item = db.Column(db.String(255), nullable=False, index=True, comment="Nome descritivo do produto (ex: 'Molho de Tomate Elefante').")
    brand = db.Column(db.String(100), nullable=True, comment="Marca do produto (ex: 'Elefante').")
    purchase_value = db.Column(db.Float, nullable=True, comment="Custo de aquisição do produto junto ao fornecedor.")
    sale_value = db.Column(db.Float, nullable=False, comment="Preço de venda do produto ao consumidor final.")
    expiration_date = db.Column(db.Date, nullable=True, comment="Data de validade do produto, se aplicável.")
    desc = db.Column(JSON, nullable=True, default=dict, comment="Campo JSON para dados adicionais e flexíveis sobre o produto.")
    category = db.Column(db.String(100), nullable=True, index=True, comment="Categoria à qual o produto pertence (ex: 'Higiene', 'Bebidas').")

    # --- Chave Estrangeira ---
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True, comment="Link para o fornecedor deste produto.")

    # --- Relações SQLAlchemy (implícitas via backref) ---
    # O atributo `stocks` (lista de locais de estoque onde este produto está)
    # é criado dinamicamente pelo `backref` definido no modelo `Stock`.
    
    # O atributo `supplier` (o objeto do fornecedor deste produto)
    # é criado dinamicamente pelo `backref` definido no modelo `Supplier`.

    def __repr__(self) -> str:
        """Representação do objeto em string, útil para depuração."""
        return f"<Product id={self.id} item='{self.item}'>"

    def to_dict(self) -> dict:
        """
        Serializa o objeto Product para um dicionário, ideal para respostas JSON.
        """
        return {
            "id": self.id,
            "item": self.item,
            "brand": self.brand,
            "purchase_value": self.purchase_value,
            "sale_value": self.sale_value,
            "expiration_date": str(self.expiration_date) if self.expiration_date else None,
            "desc": self.desc,
            "category": self.category,
            "supplier_id": self.supplier_id
        }