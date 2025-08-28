from datetime import datetime
from typing import Optional
from flask import Blueprint, request
from pydantic import BaseModel, Field, ValidationError, field_validator
import utils.auth as auth_utils
from models.product import Product, db
from utils.responses import success_response, error_response

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