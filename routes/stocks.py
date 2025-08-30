from flask import Blueprint, request
from utils.extensions import db
from models.stock import Stock, stock_item
from models.product import Product
from utils.responses import success_response, error_response
import utils.auth as auth_utils
from sqlalchemy.orm import aliased

stocks_bp = Blueprint("stocks", __name__)

@stocks_bp.route("/stocks", methods=["POST"])
@auth_utils.token_required
@auth_utils.privilege_required("STOCK_MODIFIER")
def create_stock():
    """Cria um novo local de armazenamento (ex: Depósito, Verdureira)."""
    data = request.get_json()
    name = data.get('name')
    if not name:
        return error_response("O campo 'name' é obrigatório.", 400)

    if Stock.query.filter_by(name=name).first():
        return error_response(f"O local de armazenamento '{name}' já existe.", 409)

    new_stock = Stock(name=name, description=data.get('description'))
    db.session.add(new_stock)
    db.session.commit()
    return success_response("Local de armazenamento criado com sucesso.", new_stock.to_dict(), 201)

@stocks_bp.route("/stocks", methods=["GET"])
@auth_utils.token_required
def list_stocks():
    """Lista todos os locais de armazenamento."""
    stocks = Stock.query.all()
    return success_response("Locais de armazenamento listados.", [s.to_dict() for s in stocks])

@stocks_bp.route("/stocks/<int:stock_id>/products/<int:product_id>", methods=["POST"])
@auth_utils.token_required
@auth_utils.privilege_required("STOCK_MODIFIER")
def add_product_to_stock(stock_id, product_id):
    """Adiciona um produto e sua quantidade a um estoque específico."""
    stock = Stock.query.get_or_404(stock_id)
    product = Product.query.get_or_404(product_id)
    data = request.get_json()
    quantity = data.get('quantity')

    if not isinstance(quantity, int) or quantity <= 0:
        return error_response("O campo 'quantity' deve ser um inteiro positivo.", 400)

    # Verifica se a relação já existe
    stmt = db.select(stock_item.c.quantity).where(
        stock_item.c.stock_id == stock_id,
        stock_item.c.product_id == product_id
    )
    existing_quantity = db.session.execute(stmt).scalar_one_or_none()

    if existing_quantity is not None:
        # Se já existe, atualiza a quantidade (soma)
        update_stmt = db.update(stock_item).where(
            stock_item.c.stock_id == stock_id,
            stock_item.c.product_id == product_id
        ).values(quantity=stock_item.c.quantity + quantity)
        db.session.execute(update_stmt)
    else:
        # Se não existe, cria uma nova entrada
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
    
    # Query para pegar produtos e suas quantidades nesta associação
    results = db.session.query(Product, stock_item.c.quantity)\
        .join(stock_item, Product.id == stock_item.c.product_id)\
        .filter(stock_item.c.stock_id == stock_id).all()

    products_list = []
    for product, quantity in results:
        products_list.append({
            "id": product.id,
            "item": product.item,
            "brand": product.brand,
            "sale_value": product.sale_value,
            "quantity": quantity
        })

    return success_response(f"Produtos no estoque '{stock.name}'.", products_list)

@stocks_bp.route("/stocks/<int:stock_id>/products/<int:product_id>/quantity", methods=["PATCH"])
@auth_utils.token_required
@auth_utils.privilege_required("STOCK_MODIFIER")
def set_product_quantity_in_stock(stock_id, product_id):
    """Define uma nova quantidade para um produto em um estoque (sobrescreve o valor)."""
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