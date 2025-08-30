from datetime import datetime, timedelta, date
from typing import Optional
from flask import Blueprint, request
from pydantic import BaseModel, Field, ValidationError, field_validator
import utils.auth as auth_utils
from models.product import Product, db
from models.stock import stock_item
from utils.responses import success_response, error_response
from sqlalchemy import func

products_bp = Blueprint("products", __name__)

class ProductCreatePayload(BaseModel):
    """
    Modelo de validação para a criação de um produto.
    Define os campos e suas regras.
    """
    item: str = Field(min_length=1)
    brand: Optional[str] = None
    purchase_value: Optional[float] = None
    sale_value: float = Field(gt=0)
    expiration_date: Optional[str] = None

    @field_validator('item')
    @classmethod
    def strip_item(cls, v: str):
        """Remove espaços em branco do campo 'item'."""
        return v.strip()
   
    @field_validator('brand')
    @classmethod
    def strip_brand(cls, v: Optional[str]):
        """Remove espaços em branco do campo 'brand'."""
        if v:
            return v.strip()
        return v

    @field_validator('expiration_date')
    @classmethod
    def parse_expiration_date(cls, v: Optional[str]):
        """Converte a string de data (DD-MM-AAAA) para objeto date."""
        if not v:
            return None
        try:
            return datetime.strptime(v, '%d-%m-%Y').date()
        except ValueError:
            raise ValueError("Invalid date format. Expected DD-MM-AAAA.")


# ====================================
# ==== POST - /BRATZ/PRODUCTS/ ====
# ====================================
@products_bp.route("/products", methods=["POST"])
@auth_utils.token_required
@auth_utils.privilege_required("STOCK_MODIFIER")
def create_product():
    """
    Cria um novo produto.
    Requer privilégio 'STOCK_MODIFIER'.
    
    Campos necessários:
    - item: str (obrigatório)
    - sale_value: float (obrigatório)
    
    Campos opcionais:
    - brand: str
    - purchase_value: float
    - expiration_date: str (formato DD-MM-AAAA)
    """
    data = request.get_json(silent=True) or {}

    try:
        # Usa Pydantic para validação
        payload = ProductCreatePayload(**data)
        
        # Cria o objeto do novo produto
        new_product = Product(
            item=payload.item,
            brand=payload.brand,
            purchase_value=payload.purchase_value,
            sale_value=payload.sale_value,
            expiration_date=payload.expiration_date
        )
    except ValidationError as e:
        return error_response(f"Validation Error: {e.errors()}", 400)
    except (TypeError, ValueError) as e:
        return error_response(f"Invalid data format: {str(e)}", 400)
    
    try:
        db.session.add(new_product)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return error_response(f"Failed to create product: {str(e)}", 500)

    return success_response("Product created successfully", {
        "id": new_product.id,
        "item": new_product.item,
        "brand": new_product.brand,
        "purchase_value": new_product.purchase_value,
        "sale_value": new_product.sale_value,
        "expiration_date": str(new_product.expiration_date) if new_product.expiration_date else None
    }, 201)


# ====================================
# ==== GET - /BRATZ/PRODUCTS/ ====
# ====================================
@products_bp.route("/products", methods=["GET"])
@auth_utils.token_required
def list_products():
    """
    Lista todos os produtos registrados.
    
    Permite filtrar por item ou marca, e também paginar os resultados.
    Exemplo: /products?item=shampoo&page=1&per_page=10
    """
    item_filter = request.args.get('item', '').strip()
    brand_filter = request.args.get('brand', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    query = Product.query
    if item_filter:
        query = query.filter(Product.item.ilike(f'%{item_filter}%'))
    if brand_filter:
        query = query.filter(Product.brand.ilike(f'%{brand_filter}%'))
        
    products_pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    products = [
        {
            "id": prod.id,
            "item": prod.item,
            "brand": prod.brand,
            "purchase_value": prod.purchase_value,
            "sale_value": prod.sale_value,
            "expiration_date": str(prod.expiration_date) if prod.expiration_date else None,
        }
        for prod in products_pagination.items
    ]

    return success_response("Products retrieved successfully", {
        "products": products,
        "total": products_pagination.total,
        "pages": products_pagination.pages,
        "current_page": products_pagination.page
    })


# ====================================
# ==== GET - /BRATZ/PRODUCTS/<id> ====
# ====================================
@products_bp.route("/products/<int:product_id>", methods=["GET"])
@auth_utils.token_required
def get_product(product_id):
    """
    Retorna um produto específico pelo ID.
    """
    product = Product.query.get(product_id)
    if not product:
        return error_response("Product not found", 404)

    return success_response("Product retrieved successfully", {
        "id": product.id,
        "item": product.item,
        "brand": product.brand,
        "purchase_value": product.purchase_value,
        "sale_value": product.sale_value,
        "expiration_date": str(product.expiration_date) if product.expiration_date else None
    })

@products_bp.route('/products', methods=['GET'])
@auth_utils.token_required
def get_products():
    """
    Lista todos os produtos ou busca por item/marca.
    Agora também retorna a quantidade total em estoque para cada produto.
    """
    search_query = request.args.get('item', None)
    
    # Subquery para calcular a soma do estoque para cada produto
    stock_subquery = db.session.query(
        stock_item.c.product_id,
        func.sum(stock_item.c.quantity).label('total_stock')
    ).group_by(stock_item.c.product_id).subquery()

    # Query principal que junta o produto com seu estoque total
    query = db.session.query(Product, stock_subquery.c.total_stock)\
        .outerjoin(stock_subquery, Product.id == stock_subquery.c.product_id)

    if search_query:
        query = query.filter(Product.item.ilike(f'%{search_query}%'))

    results = query.all()
    
    products_list = []
    for product, total_stock in results:
        product_data = product.to_dict()
        # Adiciona a quantidade de estoque ao dicionário do produto
        product_data['quantity_in_stock'] = total_stock or 0
        products_list.append(product_data)
        
    return success_response("Produtos listados com sucesso", {"products": products_list})


    

# ====================================
# ==== DELETE - /BRATZ/PRODUCTS/<id> ====
# ====================================
@products_bp.route("/products/<int:product_id>", methods=["DELETE"])
@auth_utils.token_required
@auth_utils.privilege_required("STOCK_MODIFIER")
def delete_product(product_id):
    """
    Deleta um produto pelo ID.
    Requer privilégio 'STOCK_MODIFIER'.
    """
    product = Product.query.get(product_id)
    if not product:
        return error_response("Product not found", 404)

    try:
        db.session.delete(product)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return error_response(f"Failed to delete product: {str(e)}", 500)

    return success_response("Product deleted successfully")


# =======================================================
# ==== GET - /BRATZ/PRODUCTS/REPORTS/LOW-STOCK ====
# =======================================================
@products_bp.route("/products/reports/low-stock", methods=["GET"])
@auth_utils.token_required
@auth_utils.privilege_required("STORAGE_MODIFIER") # Usando um privilégio que já existe
def get_low_stock_report():
    """
    Lista produtos com estoque baixo.
    Requer privilégio 'STORAGE_MODIFIER'.
    
    Query Params:
    - threshold: int (opcional, padrão 10) - O nível de estoque considerado baixo.
    - page: int (opcional, padrão 1)
    - per_page: int (opcional, padrão 20)
    """
    try:
        threshold = request.args.get('threshold', 10, type=int)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        query = Product.query.filter(Product.quantity_in_stock <= threshold)
        
        products_pagination = query.order_by(Product.quantity_in_stock.asc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        products_data = [
            {
                "id": p.id,
                "item": p.item,
                "brand": p.brand,
                "quantity_in_stock": p.quantity_in_stock,
                "sale_value": p.sale_value,
            }
            for p in products_pagination.items
        ]

        return success_response("Low stock report retrieved successfully", {
            "products": products_data,
            "total": products_pagination.total,
            "pages": products_pagination.pages,
            "current_page": products_pagination.page,
            "threshold": threshold
        })
    except Exception as e:
        return error_response(f"Failed to generate low stock report: {str(e)}", 500)

# =======================================================
# ==== GET - /BRATZ/PRODUCTS/REPORTS/EXPIRING ====
# =======================================================
@products_bp.route("/products/reports/expiring", methods=["GET"])
@auth_utils.token_required
@auth_utils.privilege_required("STORAGE_MODIFIER")
def get_expiring_products_report():
    """
    Lista produtos que estão próximos da data de vencimento.
    Requer privilégio 'STORAGE_MODIFIER'.
    
    Query Params:
    - days: int (opcional, padrão 30) - O número de dias no futuro a serem verificados.
    - page: int (opcional, padrão 1)
    - per_page: int (opcional, padrão 20)
    """
    try:
        days_ahead = request.args.get('days', 30, type=int)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        today = date.today()
        expiration_limit_date = today + timedelta(days=days_ahead)

        query = Product.query.filter(
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
                "quantity_in_stock": p.quantity_in_stock,
                "expiration_date": str(p.expiration_date),
            }
            for p in products_pagination.items
        ]
        
        return success_response("Expiring products report retrieved successfully", {
            "products": products_data,
            "total": products_pagination.total,
            "pages": products_pagination.pages,
            "current_page": products_pagination.page,
            "days_ahead": days_ahead
        })
    except Exception as e:
        return error_response(f"Failed to generate expiring products report: {str(e)}", 500)
