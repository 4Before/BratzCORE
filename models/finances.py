"""
Modelos de Dados para Finanças
------------------------------
Este módulo define as tabelas do banco de dados relacionadas a transações
financeiras, primariamente as vendas e os itens contidos nelas.
"""

from utils.extensions import db 
from datetime import datetime

class Sell(db.Model):
    """
    Representa uma única transação de venda (um recibo).
    
    Esta tabela armazena o cabeçalho da venda, contendo informações sobre
    o caixa, operador, valores totais e o cliente associado (se houver).
    """
    __tablename__ = 'sells'

    # --- Colunas da Tabela ---
    id = db.Column(db.String(36), primary_key=True, comment="ID único da venda, gerado pelo cliente (UUID4).")
    id_caixa = db.Column(db.String(50), nullable=False, comment="Identificador do caixa/estação que realizou a venda.")
    operator = db.Column(db.String(100), nullable=False, comment="Nome do operador que realizou a venda.")
    sell_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, comment="Data e hora UTC em que a venda foi registrada.")
    total_value = db.Column(db.Float, nullable=False, comment="Valor total final da venda, com descontos aplicados.")
    payment_method = db.Column(db.String(50), nullable=False, comment="Método de pagamento utilizado (ex: 'dinheiro', 'pix').")
    received_value = db.Column(db.Float, comment="Valor recebido do cliente (relevante para pagamentos em dinheiro).")
    change = db.Column(db.Float, comment="Valor do troco devolvido ao cliente.")
    
    # --- Chave Estrangeira ---
    # Se a venda for para um cliente não identificado, este campo será nulo.
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=True, comment="Link para o cliente associado à venda, se houver.")

    # --- Relações SQLAlchemy ---
    # Relação One-to-Many com os itens vendidos nesta transação.
    # O cascade garante que, ao deletar uma venda, todos os seus itens vendidos também sejam deletados.
    items_sold = db.relationship('ItemSold', backref='sell', lazy=True, cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        """
        Serializa o objeto Sell para um dicionário, ideal para respostas JSON.
        
        Inclui uma lista de todos os itens vendidos na transação, chamando
        recursivamente o método to_dict() de cada item.
        """
        return {
            'id': self.id,
            'id_caixa': self.id_caixa,
            'operator': self.operator,
            'sell_time': self.sell_time.isoformat() + 'Z', # Padrão ISO 8601 UTC
            'total_value': self.total_value,
            'payment_method': self.payment_method,
            'received_value': self.received_value,
            'change': self.change,
            'client_id': self.client_id,
            'items_sold': [item.to_dict() for item in self.items_sold]
        }

class ItemSold(db.Model):
    """
    Representa um item de produto individual dentro de uma venda.
    
    Esta tabela funciona como uma linha de um recibo, detalhando qual produto
    foi vendido, em que quantidade e por qual valor.
    """
    __tablename__ = 'sold_items'

    # --- Colunas da Tabela ---
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, comment="Link para o produto original na tabela 'products'.")
    product_name = db.Column(db.String(150), nullable=False, comment="Nome do produto no momento da venda (para histórico).")
    quantity = db.Column(db.Integer, nullable=False, comment="Quantidade de unidades vendidas deste item.")
    unit_value = db.Column(db.Float, nullable=False, comment="Valor unitário do produto no momento da venda.")
    total_value = db.Column(db.Float, nullable=False, comment="Valor total para esta linha (unit_value * quantity).")

    # --- Chave Estrangeira ---
    sell_id = db.Column(db.String(36), db.ForeignKey('sells.id'), nullable=False, comment="Link para a venda à qual este item pertence.")
    
    def to_dict(self) -> dict:
        """Serializa o objeto ItemSold para um dicionário."""
        return {
            'product_id': self.product_id,
            'product_name': self.product_name,
            'quantity': self.quantity,
            'unit_value': self.unit_value,
            'total_value': self.total_value
        }