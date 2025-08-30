"""
Blueprint para Gerenciamento de Estoques
------------------------------------------
Este módulo contém todas as rotas da API para o gerenciamento de múltiplos
locais de armazenamento (Stocks) e a associação de produtos a esses locais,
incluindo o controle de suas quantidades específicas.
"""

from flask import Blueprint, request
from utils.extensions import db
from models.stock import Stock, stock_item
from models.product import Product
from utils.responses import success_response, error_response
import utils.auth as auth_utils
from pydantic import BaseModel, Field, ValidationError, model_validator
from typing import Optional
from sqlalchemy import func

stocks_bp = Blueprint("stocks", __name__)


# --- Modelos de Validação de Dados (Pydantic) ---

class StockPayload(BaseModel):
    """Valida o payload para criação e edição de um local de estoque."""
    name: str = Field(min_length=1)
    description: Optional[str] = None

class StockUpdatePayload(BaseModel):
    """Valida o payload para a atualização de um estoque. Campos são opcionais."""
    name: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None

    @model_validator(mode='after')
    def check_at_least_one_field(self) -> 'StockUpdatePayload':
        """Garante que o payload da atualização não esteja vazio."""
        if not self.model_dump(exclude_unset=True):
            raise ValueError("Pelo menos um campo deve ser fornecido para atualização.")
        return self


# ==========================================================
# ==== CRUD PARA LOCAIS DE ARMAZENAMENTO (STOCKS) ====
# ==========================================================

@stocks_bp.route("/stocks", methods=["POST"])
@auth_utils.token_required
@auth_utils.privilege_required("STOCK_MODIFIER")
def create_stock():
    """
    Cria um novo local de armazenamento (ex: Depósito, Gôndola).
    
    Privilégio Requerido: STOCK_MODIFIER
    Payload: {"name": str, "description": str (opcional)}
    """
    data = request.get_json(silent=True) or {}
    try:
        payload = StockPayload(**data)
    except ValidationError as e:
        return error_response(f"Validation Error: {e.errors()}", 400)

    if Stock.query.filter(func.lower(Stock.name) == payload.name.lower()).first():
        return error_response(f"O local de armazenamento '{payload.name}' já existe.", 409)

    new_stock = Stock(name=payload.name, description=payload.description)
    db.session.add(new_stock)
    db.session.commit()
    return success_response("Local de armazenamento criado com sucesso.", new_stock.to_dict(), 201)


@stocks_bp.route("/stocks", methods=["GET"])
@auth_utils.token_required
def list_stocks():
    """Lista todos os locais de armazenamento."""
    stocks = Stock.query.order_by(Stock.name.asc()).all()
    return success_response("Locais de armazenamento listados.", [s.to_dict() for s in stocks])


@stocks_bp.route("/stocks/<int:stock_id>", methods=["GET"])
@auth_utils.token_required
def get_stock(stock_id):
    """Retorna os detalhes de um local de armazenamento específico."""
    stock = Stock.query.get_or_404(stock_id)
    return success_response("Local de armazenamento recuperado.", stock.to_dict())


@stocks_bp.route("/stocks/<int:stock_id>", methods=["PUT"])
@auth_utils.token_required
@auth_utils.privilege_required("STOCK_MODIFIER")
def update_stock(stock_id):
    """Atualiza os dados de um local de armazenamento (nome, descrição)."""
    stock = Stock.query.get_or_404(stock_id)
    data = request.get_json(silent=True) or {}
    try:
        payload = StockUpdatePayload(**data)
    except (ValidationError, ValueError) as e:
        return error_response(f"Erro de validação: {str(e)}", 400)

    update_data = payload.model_dump(exclude_unset=True)
    
    # Se o nome está sendo alterado, verifica se já não existe em outro registro
    if 'name' in update_data and update_data['name'].lower() != stock.name.lower():
        if Stock.query.filter(func.lower(Stock.name) == update_data['name'].lower()).first():
            return error_response(f"O nome de estoque '{update_data['name']}' já está em uso.", 409)

    for key, value in update_data.items():
        setattr(stock, key, value)
        
    db.session.commit()
    return success_response("Local de armazenamento atualizado.", stock.to_dict())


@stocks_bp.route("/stocks/<int:stock_id>", methods=["DELETE"])
@auth_utils.token_required
@auth_utils.privilege_required("STOCK_MODIFIER")
def delete_stock(stock_id):
    """
    Deleta um local de armazenamento.
    Isso removerá a associação de todos os produtos com este local,
    mas não deletará os produtos em si.
    """
    stock = Stock.query.get_or_404(stock_id)
    try:
        # Remove as associações na tabela stock_item antes de deletar o estoque
        delete_stmt = db.delete(stock_item).where(stock_item.c.stock_id == stock_id)
        db.session.execute(delete_stmt)
        
        db.session.delete(stock)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return error_response(f"Falha ao deletar estoque: {str(e)}", 500)
    return success_response("Local de armazenamento deletado com sucesso.")


# =================================================================
# ==== GERENCIAMENTO DE PRODUTOS DENTRO DE UM ESTOQUE ESPECÍFICO ====
# =================================================================

@stocks_bp.route("/stocks/<int:stock_id>/products/<int:product_id>", methods=["POST"])
@auth_utils.token_required
@auth_utils.privilege_required("STOCK_MODIFIER")
def add_product_to_stock(stock_id, product_id):
    """
    Adiciona um produto a um estoque ou incrementa sua quantidade se já existir.
    
    Payload: {"quantity": int (positivo)}
    """
    stock = Stock.query.get_or_404(stock_id)
    product = Product.query.get_or_404(product_id)
    data = request.get_json()
    quantity = data.get('quantity')

    if not isinstance(quantity, int) or quantity <= 0:
        return error_response("O campo 'quantity' deve ser um inteiro positivo.", 400)

    stmt = db.select(stock_item.c.quantity).where(
        stock_item.c.stock_id == stock_id,
        stock_item.c.product_id == product_id
    )
    existing_quantity = db.session.execute(stmt).scalar_one_or_none()

    if existing_quantity is not None:
        # Se já existe, soma a quantidade
        update_stmt = db.update(stock_item).where(
            stock_item.c.stock_id == stock_id,
            stock_item.c.product_id == product_id
        ).values(quantity=stock_item.c.quantity + quantity)
        db.session.execute(update_stmt)
    else:
        # Se não existe, cria a associação
        insert_stmt = db.insert(stock_item).values(
            stock_id=stock_id,
            product_id=product_id,
            quantity=quantity
        )
        db.session.execute(insert_stmt)
    
    db.session.commit()
    return success_response(f"'{product.item}' adicionado/atualizado no estoque '{stock.name}'.")


@stocks_bp.route("/stocks/<int:stock_id>/products", methods=["GET"])
@auth_utils.token_required
def get_products_in_stock(stock_id):
    """Lista todos os produtos e suas quantidades em um estoque específico."""
    stock = Stock.query.get_or_404(stock_id)
    
    results = db.session.query(Product, stock_item.c.quantity)\
        .join(stock_item, Product.id == stock_item.c.product_id)\
        .filter(stock_item.c.stock_id == stock_id).all()

    products_list = [p.to_dict() | {"quantity": q} for p, q in results]

    return success_response(f"Produtos no estoque '{stock.name}'.", {"products": products_list})


@stocks_bp.route("/stocks/<int:stock_id>/products/<int:product_id>/quantity", methods=["PATCH"])
@auth_utils.token_required
@auth_utils.privilege_required("STOCK_MODIFIER")
def set_product_quantity_in_stock(stock_id, product_id):
    """Define/sobrescreve a quantidade exata de um produto em um estoque."""
    Stock.query.get_or_404(stock_id)
    Product.query.get_or_404(product_id)
    data = request.get_json()
    quantity = data.get('quantity')

    if not isinstance(quantity, int) or quantity < 0:
        return error_response("O campo 'quantity' deve ser um inteiro igual ou maior que zero.", 400)

    update_stmt = db.update(stock_item).where(
        stock_item.c.stock_id == stock_id,
        stock_item.c.product_id == product_id
    ).values(quantity=quantity)
    
    result = db.session.execute(update_stmt)
    
    if result.rowcount == 0:
        return error_response("O produto não está neste estoque. Use o método POST para adicioná-lo primeiro.", 404)

    db.session.commit()
    return success_response("Quantidade do produto atualizada com sucesso.")