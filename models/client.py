"""
Modelo de Dados para Clientes
-----------------------------
Este módulo define o modelo `Client`, que representa os clientes cadastrados
no sistema da loja. Armazena informações pessoais e as regras de desconto
específicas para cada um.
"""

from utils.extensions import db
from sqlalchemy.types import JSON

class Client(db.Model):
    """
    Representa um cliente da loja.
    
    Esta tabela armazena dados cadastrais dos clientes, permitindo a
    identificação em vendas para aplicação de descontos e construção de
    um histórico de compras.
    """
    __tablename__ = "clients"

    # --- Colunas da Tabela ---
    id = db.Column(db.Integer, primary_key=True)
    cpf = db.Column(db.String(14), unique=True, nullable=False, comment="CPF do cliente, usado como identificador único de pessoa física.")
    name = db.Column(db.String(255), nullable=False, comment="Nome completo do cliente.")
    nickname = db.Column(db.String(100), comment="Apelido ou nome preferido do cliente.")
    discounts = db.Column(JSON, default=dict, comment="Dicionário com descontos percentuais por categoria (ex: {'geral': 5.0}).")
    phone = db.Column(db.String(20), comment="Número de telefone para contato.")
    notes = db.Column(db.Text, comment="Campo de texto livre para observações sobre o cliente.")

    # --- Relações SQLAlchemy ---
    # Relação One-to-Many: Um cliente pode ter muitas vendas.
    # O backref 'client' cria um atributo 'client' em cada objeto Sell.
    sales = db.relationship('Sell', backref='client', lazy='dynamic')

    def to_dict(self) -> dict:
        """
        Serializa o objeto Client para um dicionário, para uso em respostas de API.
        
        A relação 'sales' não é incluída aqui para evitar cargas pesadas de dados.
        O histórico de vendas deve ser obtido através de um endpoint específico.
        """
        return {
            "id": self.id,
            "cpf": self.cpf,
            "name": self.name,
            "nickname": self.nickname,
            "discounts": self.discounts,
            "phone": self.phone,
            "notes": self.notes,
        }

    def __repr__(self) -> str:
        """Representação do objeto em string, útil para depuração."""
        return f"<Client id={self.id} name='{self.name}'>"