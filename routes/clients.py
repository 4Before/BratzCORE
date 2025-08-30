"""
Blueprint para Gerenciamento de Clientes
-----------------------------------------
Este módulo contém todas as rotas da API relacionadas ao CRUD (Create, Read, Update, Delete)
de clientes, bem como o gerenciamento de seus descontos associados.

A validação de dados de entrada é realizada utilizando a biblioteca Pydantic
para garantir a integridade e o formato correto dos payloads.
"""

from flask import Blueprint, request
from models.client import Client, db
from utils.responses import success_response, error_response
import utils.auth as auth_utils
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator
from typing import Optional, Dict
from sqlalchemy.orm.attributes import flag_modified

clients_bp = Blueprint("clients", __name__)


# --- Modelos de Validação de Dados (Pydantic) ---

class ClientCreatePayload(BaseModel):
    """
    Modelo de validação para o PAYLOAD de CRIAÇÃO de um novo cliente.
    Define os campos obrigatórios, opcionais e suas regras de validação/formatação.
    """
    cpf: str = Field(min_length=11, max_length=14, description="CPF do cliente. Pontos e traços são removidos.")
    name: str = Field(min_length=1, description="Nome completo do cliente.")
    nickname: Optional[str] = None
    discounts: Optional[Dict[str, float]] = Field(default={}, description="Dicionário de descontos por categoria.")
    phone: Optional[str] = None
    notes: Optional[str] = None

    @field_validator('cpf')
    @classmethod
    def format_cpf(cls, v: str) -> str:
        """Remove formatação do CPF, mantendo apenas os dígitos."""
        return v.replace('.', '').replace('-', '')
    
    @field_validator('name', 'nickname')
    @classmethod
    def strip_strings(cls, v: Optional[str]) -> Optional[str]:
        """Remove espaços em branco no início e fim dos campos de texto."""
        if v:
            return v.strip()
        return v

class ClientUpdatePayload(BaseModel):
    """
    Modelo de validação para o PAYLOAD de ATUALIZAÇÃO de um cliente existente.
    Todos os campos são opcionais, permitindo atualizações parciais.
    O CPF não é incluído, pois é considerado um identificador imutável.
    Os descontos são gerenciados por endpoints específicos.
    """
    name: Optional[str] = Field(None, min_length=1)
    nickname: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None

    @field_validator('name', 'nickname')
    @classmethod
    def strip_strings(cls, v: Optional[str]) -> Optional[str]:
        """Remove espaços em branco no início e fim dos campos de texto."""
        if v is not None:
            return v.strip()
        return v

    @model_validator(mode='after')
    def check_at_least_one_field(self) -> 'ClientUpdatePayload':
        """Garante que o payload da atualização não esteja vazio."""
        if not self.model_dump(exclude_unset=True):
            raise ValueError("Pelo menos um campo deve ser fornecido para atualização.")
        return self


# ====================================
# ==== CRUD BÁSICO DE CLIENTES ====
# ====================================

@clients_bp.route("/clients", methods=["POST"])
@auth_utils.token_required
@auth_utils.privilege_required("CLIENT_CREATOR")
def create_client():
    """
    Cria um novo cliente no sistema.

    Privilégio Requerido: CLIENT_CREATOR

    Payload (JSON):
    - cpf: str (obrigatório)
    - name: str (obrigatório)
    - nickname: str (opcional)
    - discounts: dict (opcional, ex: {"geral": 5.0})
    - phone: str (opcional)
    - notes: str (opcional)

    Retorna:
    - 201 Created: Cliente criado com sucesso, com os dados do novo cliente.
    - 400 Bad Request: Erro de validação nos dados enviados.
    - 409 Conflict: O CPF enviado já está cadastrado.
    """
    data = request.get_json(silent=True) or {}
    try:
        payload = ClientCreatePayload(**data)
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
    """
    Lista todos os clientes ou busca por um termo específico.
    A busca é realizada nos campos de nome, CPF e apelido.

    Query Params:
    - q: str (opcional) - Termo de busca.

    Retorna:
    - 200 OK: Lista de clientes encontrados.
    """
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


@clients_bp.route("/clients/<int:client_id>", methods=["GET"])
@auth_utils.token_required
def get_client(client_id):
    """
    Busca e retorna os dados de um cliente específico pelo seu ID.

    Retorna:
    - 200 OK: Dados do cliente.
    - 404 Not Found: Cliente com o ID especificado não foi encontrado.
    """
    client = Client.query.get_or_404(client_id)
    return success_response("Cliente recuperado com sucesso.", client.to_dict())


@clients_bp.route("/clients/<int:client_id>", methods=["PUT"])
@auth_utils.token_required
@auth_utils.privilege_required("CLIENT_CREATOR")
def update_client(client_id):
    """
    Atualiza os dados de um cliente existente.
    Permite a atualização parcial de um ou mais campos.

    Privilégio Requerido: CLIENT_CREATOR

    Payload (JSON, opcional):
    - name: str
    - nickname: str
    - phone: str
    - notes: str

    Retorna:
    - 200 OK: Cliente atualizado com sucesso, com os novos dados.
    - 400 Bad Request: Erro de validação ou payload vazio.
    - 404 Not Found: Cliente não encontrado.
    """
    client = Client.query.get_or_404(client_id)
    data = request.get_json(silent=True) or {}
    
    try:
        payload = ClientUpdatePayload(**data)
    except (ValidationError, ValueError) as e:
        return error_response(f"Validation Error: {str(e)}", 400)

    # Itera sobre os campos que foram enviados pelo usuário e atualiza o objeto
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(client, key, value)
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return error_response(f"Falha ao atualizar cliente: {str(e)}", 500)

    return success_response("Cliente atualizado com sucesso.", client.to_dict())


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
    """Adiciona ou atualiza um desconto (por categoria ou geral) para um cliente."""
    client = Client.query.get_or_404(client_id)
    data = request.get_json()
    category = data.get("category")
    percentage = data.get("percentage")

    if not category or not isinstance(percentage, (int, float)):
        return error_response("Campos 'category' (string) e 'percentage' (número) são obrigatórios.", 400)
        
    if client.discounts is None:
        client.discounts = {}

    client.discounts[category.lower()] = percentage
    
    # Avisa o SQLAlchemy que o campo JSON mutável foi modificado
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
    """Remove um desconto de um cliente pela sua chave/categoria."""
    client = Client.query.get_or_404(client_id)
    category_key = category.lower()

    if client.discounts is None or category_key not in client.discounts:
        return error_response(f"Desconto para a categoria '{category}' não encontrado.", 404)
        
    del client.discounts[category_key]
    
    # Avisa o SQLAlchemy que o campo JSON mutável foi modificado
    flag_modified(client, "discounts")

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return error_response(f"Falha ao remover desconto: {str(e)}", 500)
        
    return success_response(f"Desconto para '{category}' removido com sucesso.")