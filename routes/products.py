"""
Blueprint para Gerenciamento de Produtos
-----------------------------------------
Este módulo gerencia todas as operações da API relacionadas a produtos,
incluindo CRUD completo, cálculo de estoque agregado e geração de relatórios
de estoque baixo e produtos perto do vencimento.
"""

from datetime import datetime, timedelta, date
from typing import Optional
from flask import Blueprint, request
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator
import utils.auth as auth_utils
from models.product import Product, db
from models.stock import stock_item
from utils.responses import success_response, error_response
from sqlalchemy import func

products_bp = Blueprint("products", __name__)

# --- Modelos de Validação de Dados (Pydantic) ---

class ProductCreatePayload(BaseModel):
    """
    Valida o payload para a CRIAÇÃO de um novo produto.
    """
    item: str = Field(min_length=1)
    brand: Optional[str] = None
    purchase_value: Optional[float] = None
    sale_value: float = Field(gt=0)
    expiration_date: Optional[str] = None
    category: Optional[str] = None

    @field_validator('item', 'brand', 'category')
    @classmethod
    def strip_strings(cls, v: Optional[str]) -> Optional[str]:
        """Remove espaços em branco no início e fim dos campos de texto."""
        if v:
            return v.strip()
        return v

    @field_validator('expiration_date')
    @classmethod
    def parse_expiration_date(cls, v: Optional[str]) -> Optional[date]:
        """Converte a string de data (DD-MM-AAAA) para um objeto date."""
        if not v:
            return None
        try:
            return datetime.strptime(v, '%d-%m-%Y').date()
        except ValueError:
            raise ValueError("Formato de data inválido. Use DD-MM-AAAA.")

class ProductUpdatePayload(BaseModel):
    """
    Valida o payload para a ATUALIZAÇÃO de um produto.
    Todos os campos são opcionais para permitir updates parciais.
    """
    item: Optional[str] = Field(None, min_length=1)
    brand: Optional[str] = None
    purchase_value: Optional[float] = None
    sale_value: Optional[float] = Field(None, gt=0)
    expiration_date: Optional[str] = None
    category: Optional[str] = None

    # Reutiliza os validadores do modelo de criação
    _strip_strings = field_validator('item', 'brand', 'category')(ProductCreatePayload.strip_strings)
    _parse_date = field_validator('expiration_date')(ProductCreatePayload.parse_expiration_date)

    @model_validator(mode='after')
    def check_at_least_one_field(self) -> 'ProductUpdatePayload':
        """Garante que o payload da atualização não esteja vazio."""
        if not self.model_dump(exclude_unset=True):
            raise ValueError("Pelo menos um campo deve ser fornecido para atualização.")
        return self

# ====================================
# ==== CRUD DE PRODUTOS ====
# ====================================

@products_bp.route("/products", methods=["POST"])
@auth_utils.token_required
@auth_utils.privilege_required("STOCK_MODIFIER")
def create_product():
    """Cria um novo produto."""
    data = request.get_json(silent=True) or {}
    try:
        payload = ProductCreatePayload(**data)
        new_product = Product(
            item=payload.item,
            brand=payload.brand,
            purchase_value=payload.purchase_value,
            sale_value=payload.sale_value,
            expiration_date=payload.expiration_date,
            category=payload.category
        )
        db.session.add(new_product)
        db.session.commit()
    except (ValidationError, ValueError) as e:
        return error_response(f"Erro de validação: {e}", 400)
    except Exception as e:
        db.session.rollback()
        return error_response(f"Falha ao criar produto: {str(e)}", 500)

    return success_response("Produto criado com sucesso", new_product.to_dict(), 201)


@products_bp.route("/products", methods=["GET"])
@auth_utils.token_required
def list_products():
    """Lista todos os produtos com estoque calculado e paginação."""
    item_filter = request.args.get('item', '').strip()
    brand_filter = request.args.get('brand', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    stock_subquery = db.session.query(
        stock_item.c.product_id,
        func.sum(stock_item.c.quantity).label('total_stock')
    ).group_by(stock_item.c.product_id).subquery()

    query = db.session.query(Product, stock_subquery.c.total_stock)\
        .outerjoin(stock_subquery, Product.id == stock_subquery.c.product_id)

    if item_filter:
        query = query.filter(Product.item.ilike(f'%{item_filter}%'))
    if brand_filter:
        query = query.filter(Product.brand.ilike(f'%{brand_filter}%'))
        
    products_pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    products_list = []
    for product, total_stock in products_pagination.items:
        product_data = product.to_dict()
        product_data['quantity_in_stock'] = total_stock or 0
        products_list.append(product_data)

    return success_response("Produtos recuperados com sucesso", {
        "products": products_list,
        "total": products_pagination.total,
        "pages": products_pagination.pages,
        "current_page": products_pagination.page
    })


@products_bp.route("/products/<int:product_id>", methods=["GET"])
@auth_utils.token_required
def get_product(product_id):
    """Retorna um produto específico pelo ID com estoque calculado."""
    product = Product.query.get_or_404(product_id)
    
    stmt = db.select(func.sum(stock_item.c.quantity)).where(stock_item.c.product_id == product_id)
    total_stock = db.session.execute(stmt).scalar_one_or_none()

    product_data = product.to_dict()
    product_data['quantity_in_stock'] = total_stock or 0
    
    return success_response("Produto recuperado com sucesso", product_data)


@products_bp.route("/products/<int:product_id>", methods=["PUT"])
@auth_utils.token_required
@auth_utils.privilege_required("STOCK_MODIFIER")
def update_product(product_id):
    """
    Atualiza os dados de um produto existente.

    Privilégio Requerido: STOCK_MODIFIER

    Payload (JSON, opcional):
    - item: str
    - brand: str
    - purchase_value: float
    - sale_value: float
    - expiration_date: str (DD-MM-AAAA)
    - category: str

    Retorna:
    - 200 OK: Produto atualizado com sucesso, com os novos dados.
    """
    product = Product.query.get_or_404(product_id)
    data = request.get_json(silent=True) or {}
    
    try:
        payload = ProductUpdatePayload(**data)
    except (ValidationError, ValueError) as e:
        return error_response(f"Erro de validação: {str(e)}", 400)

    # Itera sobre os campos que foram enviados e atualiza o objeto
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return error_response(f"Falha ao atualizar produto: {str(e)}", 500)

    # Recalcula o estoque para retornar o dado completo
    stmt = db.select(func.sum(stock_item.c.quantity)).where(stock_item.c.product_id == product_id)
    total_stock = db.session.execute(stmt).scalar_one_or_none()
    
    product_data = product.to_dict()
    product_data['quantity_in_stock'] = total_stock or 0

    return success_response("Produto atualizado com sucesso.", product_data)


@products_bp.route("/products/<int:product_id>", methods=["DELETE"])
@auth_utils.token_required
@auth_utils.privilege_required("STOCK_MODIFIER")
def delete_product(product_id):
    """Deleta um produto pelo ID, incluindo suas referências em estoques."""
    product = Product.query.get_or_404(product_id)
    try:
        # Remove as associações do produto em todos os estoques
        delete_stmt = db.delete(stock_item).where(stock_item.c.product_id == product_id)
        db.session.execute(delete_stmt)
        
        db.session.delete(product)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return error_response(f"Falha ao deletar produto: {str(e)}", 500)
    return success_response("Produto deletado com sucesso")


# =======================================================
# ==== RELATÓRIOS DE PRODUTOS ====
# =======================================================

@products_bp.route("/products/reports/low-stock", methods=["GET"])
@auth_utils.token_required
@auth_utils.privilege_required("STORAGE_MODIFIER")
def get_low_stock_report():
    """Gera um relatório paginado de produtos com estoque baixo."""
    try:
        threshold = request.args.get('threshold', 10, type=int)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        stock_subquery = db.session.query(
            stock_item.c.product_id.label("product_id"),
            func.sum(stock_item.c.quantity).label("total_stock")
        ).group_by(stock_item.c.product_id).subquery()

        query = db.session.query(Product, stock_subquery.c.total_stock)\
            .join(stock_subquery, Product.id == stock_subquery.c.product_id)\
            .filter(stock_subquery.c.total_stock <= threshold)
        
        products_pagination = query.order_by(stock_subquery.c.total_stock.asc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        products_data = [
            {
                "id": p.id,
                "item": p.item,
                "brand": p.brand,
                "quantity_in_stock": total_stock or 0,
                "sale_value": p.sale_value,
            }
            for p, total_stock in products_pagination.items
        ]

        return success_response("Relatório de estoque baixo recuperado.", {
            "products": products_data,
            "total": products_pagination.total,
            "pages": products_pagination.pages,
            "current_page": products_pagination.page,
            "threshold": threshold
        })
    except Exception as e:
        return error_response(f"Falha ao gerar relatório de estoque baixo: {str(e)}", 500)


@products_bp.route("/products/reports/expiring", methods=["GET"])
@auth_utils.token_required
@auth_utils.privilege_required("STORAGE_MODIFIER")
def get_expiring_products_report():
    """Gera um relatório paginado de produtos próximos do vencimento."""
    try:
        days_ahead = request.args.get('days', 30, type=int)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        today = date.today()
        expiration_limit_date = today + timedelta(days=days_ahead)

        stock_subquery = db.session.query(
            stock_item.c.product_id,
            func.sum(stock_item.c.quantity).label('total_stock')
        ).group_by(stock_item.c.product_id).subquery()

        query = db.session.query(Product, stock_subquery.c.total_stock)\
            .outerjoin(stock_subquery, Product.id == stock_subquery.c.product_id)\
            .filter(
                Product.expiration_date.isnot(None),
                Product.expiration_date.between(today, expiration_limit_date)
            )

        products_pagination = query.order_by(Product.expiration_date.asc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        products_data = [
            {
                "id": p.id,
                "item": p.item,
                "brand": p.brand,
                "quantity_in_stock": total_stock or 0,
                "expiration_date": str(p.expiration_date),
            }
            for p, total_stock in products_pagination.items
        ]
        
        return success_response("Relatório de produtos a vencer recuperado.", {
            "products": products_data,
            "total": products_pagination.total,
            "pages": products_pagination.pages,
            "current_page": products_pagination.page,
            "days_ahead": days_ahead
        })
    except Exception as e:
        return error_response(f"Falha ao gerar relatório de produtos a vencer: {str(e)}", 500)