"""
Blueprint para Gerenciamento de Fornecedores
--------------------------------------------
Este módulo contém todas as rotas da API para o CRUD de fornecedores.
"""

from flask import Blueprint, request
from models.supplier import Supplier, db
from models.product import Product
from utils.responses import success_response, error_response
import utils.auth as auth_utils
from pydantic import BaseModel, EmailStr, Field, ValidationError
from typing import Optional

suppliers_bp = Blueprint("suppliers", __name__)


# --- Pydantic Payload Validator ---
class SupplierPayload(BaseModel):
    name: str = Field(min_length=1)
    cnpj: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None


# --- Rotas CRUD ---

@suppliers_bp.route("/suppliers", methods=["POST"])
@auth_utils.token_required
@auth_utils.privilege_required("ADMIN")
def create_supplier():
    """Cria um novo fornecedor."""
    data = request.get_json(silent=True) or {}
    try:
        payload = SupplierPayload(**data)
    except ValidationError as e:
        return error_response(f"Erro de validação: {e.errors()}", 400)

    if Supplier.query.filter_by(name=payload.name).first():
        return error_response(f"Fornecedor com o nome '{payload.name}' já existe.", 409)

    new_supplier = Supplier(**payload.model_dump())
    db.session.add(new_supplier)
    db.session.commit()
    return success_response("Fornecedor criado com sucesso.", new_supplier.to_dict(), 201)

@suppliers_bp.route("/suppliers", methods=["GET"])
@auth_utils.token_required
def list_suppliers():
    """Lista todos os fornecedores."""
    suppliers = [s.to_dict() for s in Supplier.query.order_by(Supplier.name.asc()).all()]
    return success_response("Fornecedores recuperados com sucesso.", {"suppliers": suppliers})

@suppliers_bp.route("/suppliers/<int:supplier_id>", methods=["GET"])
@auth_utils.token_required
def get_supplier(supplier_id):
    """Retorna um fornecedor específico."""
    supplier = Supplier.query.get_or_404(supplier_id)
    return success_response("Fornecedor recuperado com sucesso.", supplier.to_dict())

@suppliers_bp.route("/suppliers/<int:supplier_id>", methods=["PUT"])
@auth_utils.token_required
@auth_utils.privilege_required("ADMIN")
def update_supplier(supplier_id):
    """Atualiza um fornecedor existente."""
    supplier = Supplier.query.get_or_404(supplier_id)
    data = request.get_json(silent=True) or {}
    try:
        payload = SupplierPayload(**data)
    except ValidationError as e:
        return error_response(f"Erro de validação: {e.errors()}", 400)

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(supplier, key, value)
    
    db.session.commit()
    return success_response("Fornecedor atualizado com sucesso.", supplier.to_dict())

@suppliers_bp.route("/suppliers/<int:supplier_id>", methods=["DELETE"])
@auth_utils.token_required
@auth_utils.privilege_required("ADMIN")
def delete_supplier(supplier_id):
    """Deleta um fornecedor."""
    supplier = Supplier.query.get_or_404(supplier_id)
    
    # Regra de negócio: antes de deletar, desvincula os produtos
    Product.query.filter_by(supplier_id=supplier_id).update({"supplier_id": None})
    
    db.session.delete(supplier)
    db.session.commit()
    return success_response("Fornecedor deletado com sucesso.")

@suppliers_bp.route("/suppliers/<int:supplier_id>/products", methods=["GET"])
@auth_utils.token_required
def get_supplier_products(supplier_id):
    """Lista todos os produtos associados a um fornecedor específico."""
    supplier = Supplier.query.get_or_404(supplier_id)
    products = [p.to_dict() for p in supplier.products]
    return success_response(f"Produtos do fornecedor '{supplier.name}' recuperados.", {"products": products})