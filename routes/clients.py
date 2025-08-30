from flask import Blueprint, request
from models.client import Client, db
from utils.responses import success_response, error_response
import utils.auth as auth_utils
from pydantic import BaseModel, Field, ValidationError, field_validator
from typing import Optional, Dict
from sqlalchemy.orm.attributes import flag_modified

clients_bp = Blueprint("clients", __name__)

# --- Modelos de Validação com Pydantic ---
class ClientPayload(BaseModel):
    cpf: str = Field(min_length=11, max_length=14)
    name: str = Field(min_length=1)
    nickname: Optional[str] = None
    discounts: Optional[Dict[str, float]] = None
    phone: Optional[str] = None
    notes: Optional[str] = None

    @field_validator('cpf')
    @classmethod
    def format_cpf(cls, v: str):
        return v.replace('.', '').replace('-', '')
    
    @field_validator('name', 'nickname')
    @classmethod
    def strip_strings(cls, v: str):
        if v:
            return v.strip()
        return v

# ====================================
# ==== CRUD BÁSICO DE CLIENTES ====
# ====================================

@clients_bp.route("/clients", methods=["POST"])
@auth_utils.token_required
@auth_utils.privilege_required("CLIENT_CREATOR")
def create_client():
    """Cria um novo cliente no sistema."""
    data = request.get_json(silent=True) or {}
    try:
        payload = ClientPayload(**data)
    except ValidationError as e:
        return error_response(f"Validation Error: {e.errors()}", 400)

    if Client.query.filter_by(cpf=payload.cpf).first():
        return error_response(f"Cliente com CPF '{payload.cpf}' já existe.", 409)

    new_client = Client(
        cpf=payload.cpf,
        name=payload.name,
        nickname=payload.nickname,
        discounts=payload.discounts or {},
        phone=payload.phone,
        notes=payload.notes
    )
    try:
        db.session.add(new_client)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return error_response(f"Falha ao criar cliente: {str(e)}", 500)
    
    return success_response("Cliente criado com sucesso", new_client.to_dict(), 201)

@clients_bp.route("/clients", methods=["GET"])
@auth_utils.token_required
def list_clients():
    """Lista todos os clientes com suporte a pesquisa."""
    search_query = request.args.get('q', '').strip()
    query = Client.query
    if search_query:
        search_term = f'%{search_query}%'
        query = query.filter(
            (Client.cpf.ilike(search_term)) |
            (Client.name.ilike(search_term)) |
            (Client.nickname.ilike(search_term))
        )
    clients = [c.to_dict() for c in query.all()]
    return success_response("Clientes recuperados com sucesso", {"clients": clients})

@clients_bp.route("/clients/<int:client_id>", methods=["DELETE"])
@auth_utils.token_required
@auth_utils.privilege_required("CLIENT_CREATOR")
def delete_client(client_id):
    """Deleta um cliente pelo ID."""
    client = Client.query.get_or_404(client_id)
    try:
        db.session.delete(client)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return error_response(f"Falha ao deletar cliente: {str(e)}", 500)
    return success_response("Cliente deletado com sucesso")

# ======================================
# ==== CRUD DE DESCONTOS DO CLIENTE ====
# ======================================

@clients_bp.route("/clients/<int:client_id>/discounts", methods=["GET"])
@auth_utils.token_required
def get_client_discounts(client_id):
    """Lista os descontos de um cliente específico."""
    client = Client.query.get_or_404(client_id)
    return success_response("Descontos do cliente recuperados.", client.discounts or {})

@clients_bp.route("/clients/<int:client_id>/discounts", methods=["POST"])
@auth_utils.token_required
@auth_utils.privilege_required("CLIENT_CREATOR")
def add_or_update_client_discount(client_id):
    """Adiciona ou atualiza um desconto para um cliente."""
    client = Client.query.get_or_404(client_id)
    data = request.get_json()
    category = data.get("category")
    percentage = data.get("percentage")

    if not category or not isinstance(percentage, (int, float)):
        return error_response("Campos 'category' (string) e 'percentage' (número) são obrigatórios.", 400)
        
    if client.discounts is None:
        client.discounts = {}

    client.discounts[category.lower()] = percentage
    
    # Avisa o SQLAlchemy que o campo JSON foi modificado
    flag_modified(client, "discounts")
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return error_response(f"Falha ao salvar desconto: {str(e)}", 500)
        
    return success_response(f"Desconto para '{category}' atualizado com sucesso.", client.discounts)

@clients_bp.route("/clients/<int:client_id>/discounts/<string:category>", methods=["DELETE"])
@auth_utils.token_required
@auth_utils.privilege_required("CLIENT_CREATOR")
def remove_client_discount(client_id, category):
    """Remove um desconto de um cliente pela categoria."""
    client = Client.query.get_or_404(client_id)
    category_key = category.lower()

    if client.discounts is None or category_key not in client.discounts:
        return error_response(f"Desconto para a categoria '{category}' não encontrado.", 404)
        
    del client.discounts[category_key]
    
    # Avisa o SQLAlchemy que o campo JSON foi modificado
    flag_modified(client, "discounts")

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return error_response(f"Falha ao remover desconto: {str(e)}", 500)
        
    return success_response(f"Desconto para '{category}' removido com sucesso.")