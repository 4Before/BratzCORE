"""
Blueprint para Autenticação de Usuários
---------------------------------------
Este módulo lida com os processos fundamentais de autenticação: registro público
de usuários básicos e login para todos os tipos de conta.
"""

from flask import Blueprint, request
from pydantic import BaseModel, EmailStr, Field, ValidationError, field_validator, model_validator
from models.user import User
from utils.responses import success_response, error_response
from utils.jwt_manager import generate_token
from utils.extensions import db 

auth_bp = Blueprint("auth", __name__)


# --- Modelos de Validação de Dados (Pydantic) ---

class LoginPayload(BaseModel):
    """Valida o payload para a rota de login."""
    email: EmailStr
    password: str

class RegisterPayload(BaseModel):
    """Valida o payload para a rota de registro público."""
    email: EmailStr
    password: str = Field(min_length=8)
    confirm_password: str
    
    # Opcional, mas limitado a tipos de conta não privilegiados
    account_type: str = "BASIC" 

    @model_validator(mode='after')
    def check_passwords_match(self) -> 'RegisterPayload':
        """Verifica se as senhas no payload são idênticas."""
        pw1 = self.password
        pw2 = self.confirm_password
        if pw1 is not None and pw2 is not None and pw1 != pw2:
            raise ValueError("As senhas não correspondem.")
        return self


# ==================================
# ==== REGISTRO E LOGIN PÚBLICO ====
# ==================================

@auth_bp.route("/auth/register", methods=["POST"])
def register():
    """
    Registra um novo usuário básico no sistema.
    Esta rota é pública e destina-se a um auto-cadastro simples.
    Contas com privilégios devem ser criadas pela rota de administrador /accounts.
    
    Payload (JSON):
    - email: str (obrigatório, formato de email válido)
    - password: str (obrigatório, mínimo 8 caracteres)
    - confirm_password: str (obrigatório, deve ser igual a 'password')
    - account_type: str (opcional, default: "BASIC")

    Retorna:
    - 201 Created: Usuário registrado com sucesso, com token de acesso.
    - 400 Bad Request: Erro de validação nos dados.
    - 409 Conflict: O e-mail enviado já está cadastrado.
    """
    data = request.get_json(silent=True) or {}
    try:
        payload = RegisterPayload(**data)
    except (ValidationError, ValueError) as e:
        return error_response(f"Erro de validação: {str(e)}", 400)

    # Medida de segurança: impede a criação de contas privilegiadas por esta rota pública
    allowed_types = ["BASIC", "CLIENT"] # Defina aqui os tipos permitidos para auto-cadastro
    if payload.account_type.upper() not in allowed_types:
        return error_response(f"O tipo de conta '{payload.account_type}' não é permitido para registro público.", 403)
        
    if User.query.filter_by(email=payload.email).first():
        return error_response("Este e-mail já está registrado.", 409)

    user = User(
        email=payload.email, 
        account_type=payload.account_type.upper(), 
        privileges={} # Contas criadas publicamente começam sem privilégios
    )
    user.set_password(payload.password)

    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return error_response(f"Falha ao registrar usuário: {str(e)}", 500)

    token = generate_token(user)

    # A resposta do registro é consistente com a do login
    return success_response("Usuário registrado com sucesso", {
        "token": token,
        "email": user.email,
        "account_type": user.account_type,
        "privileges": user.privileges,
        "profile": user.profile
    }, 201)


@auth_bp.route("/auth/login", methods=["POST"])
def login():
    """
    Autentica um usuário com e-mail e senha e retorna um token de acesso JWT.
    
    Payload (JSON):
    - email: str (obrigatório)
    - password: str (obrigatório)

    Retorna:
    - 200 OK: Login bem-sucedido, com token e dados do usuário.
    - 401 Unauthorized: Credenciais inválidas (e-mail ou senha incorretos).
    """
    data = request.get_json(silent=True) or {}
    try:
        payload = LoginPayload(**data)
    except ValidationError as e:
        return error_response(f"Erro de validação: {str(e)}", 400)

    user = User.query.filter_by(email=payload.email).first()

    if not user or not user.check_password(payload.password):
        return error_response("Credenciais inválidas.", 401)

    token = generate_token(user)

    return success_response("Login bem-sucedido", {
        "token": token,
        "email": user.email,
        "account_type": user.account_type,
        "privileges": user.privileges,
        "profile": user.profile
    })