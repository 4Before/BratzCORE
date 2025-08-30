"""
Modelo de Dados para Usuários
-----------------------------
Este módulo define o modelo `User`, que é a base para todo o sistema
de autenticação e autorização da aplicação.
"""

from utils.extensions import db
from sqlalchemy.types import JSON
from werkzeug.security import generate_password_hash, check_password_hash
from typing import Dict, Optional

class User(db.Model):
    """
    Representa uma conta de usuário no sistema.

    Esta tabela armazena as credenciais de login e as informações de permissão.
    A senha nunca é armazenada em texto plano, apenas seu hash.
    Os campos `privileges` e `profile` são do tipo JSON para máxima flexibilidade.
    """
    __tablename__ = "users"

    # --- Colunas da Tabela ---
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True, comment="E-mail de login do usuário, deve ser único.")
    password_hash = db.Column(db.String(255), nullable=False, comment="Armazena o hash da senha, nunca a senha em texto plano.")
    account_type = db.Column(db.String(50), nullable=False, index=True, comment="Tipo de conta (ex: OWNER, CAIXA, ADMIN).")
    
    # --- Campos JSON Flexíveis ---
    privileges = db.Column(JSON, nullable=False, default=dict, comment="Dicionário de permissões booleanas que definem o que o usuário pode fazer.")
    profile = db.Column(JSON, nullable=True, default=dict, comment="Dicionário para dados adicionais específicos de cada tipo de conta (ex: número do caixa).")

    def __init__(self, email: str, account_type: str, privileges: Optional[Dict] = None, profile: Optional[Dict] = None):
        """
        Construtor para a criação de uma nova instância de User.
        """
        self.email = email
        self.account_type = account_type
        self.privileges = privileges or {}
        self.profile = profile or {}

    def set_password(self, password: str) -> None:
        """
        Gera um hash seguro para a senha fornecida e o armazena.
        Este método deve SEMPRE ser usado para definir ou alterar senhas.
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """
        Verifica se a senha fornecida corresponde ao hash armazenado.
        
        Args:
            password (str): A senha em texto plano a ser verificada.
        
        Returns:
            bool: True se a senha for correta, False caso contrário.
        """
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> Dict:
        """
        Serializa o objeto User para um dicionário, para uso em respostas de API.
        
        IMPORTANTE: Este método omite intencionalmente o `password_hash` por razões de segurança.
        """
        return {
            "id": self.id,
            "email": self.email,
            "account_type": self.account_type,
            "privileges": self.privileges,
            "profile": self.profile
        }

    def __repr__(self) -> str:
        """Representação do objeto em string, útil para depuração."""
        return f"<User id={self.id} email='{self.email}' type='{self.account_type}'>"