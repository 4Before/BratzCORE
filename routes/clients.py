from flask import Blueprint, request
from models.client import Client, db
from utils.responses import success_response, error_response
import utils.auth as auth_utils
from pydantic import BaseModel, Field, ValidationError, field_validator
from typing import Optional, Dict

clients_bp = Blueprint("clients", __name__)

# --- Models de Validação com Pydantic ---
class ClientCreatePayload(BaseModel):
    """Modelo de validação para a criação de um cliente."""
    cpf: str = Field(min_length=11, max_length=14)
    name: str = Field(min_length=1)
    nickname: Optional[str] = None
    # A validação de Dict é feita diretamente aqui pela Pydantic
    discounts: Optional[Dict[str, float]] = None
    phone: Optional[str] = None
    notes: Optional[str] = None

    @field_validator('cpf')
    @classmethod
    def format_cpf(cls, v: str):
        """Formata o CPF removendo pontos e traços."""
        return v.replace('.', '').replace('-', '')
    
    @field_validator('name', 'nickname')
    @classmethod
    def strip_strings(cls, v: str):
        """Remove espaços em branco no início e fim de strings."""
        return v.strip()

# ====================================
# ==== POST - /BRATZ/CLIENTS/ ====
# ====================================
@clients_bp.route("/clients", methods=["POST"])
@auth_utils.token_required
@auth_utils.privilege_required("CLIENT_CREATOR")
def create_client():
    """
    Cria um novo cliente no sistema.
    Requer privilégio 'CLIENT_CREATOR'.
    """
    data = request.get_json(silent=True) or {}

    try:
        # Valida os dados de entrada usando Pydantic
        payload = ClientCreatePayload(**data)
    except ValidationError as e:
        return error_response(f"Validation Error: {e.errors()}", 400)

    # Verifica se o CPF já existe no banco de dados
    existing_client = Client.query.filter_by(cpf=payload.cpf).first()
    if existing_client:
        return error_response(f"Client with CPF '{payload.cpf}' already exists.", 409)

    # Cria a nova instância do cliente
    new_client = Client(
        cpf=payload.cpf,
        name=payload.name,
        nickname=payload.nickname,
        discounts=payload.discounts,
        phone=payload.phone,
        notes=payload.notes
    )

    try:
        db.session.add(new_client)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return error_response(f"Failed to create client: {str(e)}", 500)

    return success_response("Client created successfully", {
        "id": new_client.id,
        "cpf": new_client.cpf,
        "name": new_client.name,
        "nickname": new_client.nickname,
        "phone": new_client.phone
    }, 201)

# ====================================
# ==== GET - /BRATZ/CLIENTS/ ====
# ====================================
@clients_bp.route("/clients", methods=["GET"])
@auth_utils.token_required
def list_clients():
    """
    Lista todos os clientes com suporte a pesquisa e paginação.
    """
    search_query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    query = Client.query
    if search_query:
        # Permite buscar por CPF, nome ou apelido
        query = query.filter(
            (Client.cpf.ilike(f'%{search_query}%')) |
            (Client.name.ilike(f'%{search_query}%')) |
            (Client.nickname.ilike(f'%{search_query}%'))
        )
        
    clients_pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    clients = [
        {
            "id": c.id,
            "cpf": c.cpf,
            "name": c.name,
            "nickname": c.nickname,
            "phone": c.phone,
            "discounts": c.discounts
        }
        for c in clients_pagination.items
    ]

    return success_response("Clients retrieved successfully", {
        "clients": clients,
        "total": clients_pagination.total,
        "pages": clients_pagination.pages,
        "current_page": clients_pagination.page
    })
    
# ======================================
# ==== DELETE - /BRATZ/CLIENTS/<id> ====
# ======================================
@clients_bp.route("/clients/<int:client_id>", methods=["DELETE"])
@auth_utils.token_required
@auth_utils.privilege_required("CLIENT_CREATOR")
def delete_client(client_id):
    """
    Deleta um cliente pelo ID.
    Requer privilégio 'CLIENT_CREATOR'.
    """
    client = Client.query.get(client_id)
    if not client:
        return error_response("Client not found", 404)

    try:
        db.session.delete(client)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return error_response(f"Failed to delete client: {str(e)}", 500)

    return success_response("Client deleted successfully")