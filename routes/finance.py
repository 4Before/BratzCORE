from flask import Blueprint, request, g
from models.finances import Sell, ItemSold 
from models.product import Product
from utils.extensions import db
import utils.auth as auth_utils
from utils.responses import success_response, error_response
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional

finances_bp = Blueprint('finances', __name__)

# --- Models de Validação com Pydantic ---

class ItemSoldPayload(BaseModel):
    """Modelo de validação para um item dentro da lista de uma venda."""
    product_id: int
    product_name: str = Field(min_length=1)
    quantity: int = Field(gt=0) # Quantidade deve ser maior que zero
    unit_value: float = Field(ge=0)
    total_value_item: float = Field(ge=0)

class RegisterSellPayload(BaseModel):
    """Modelo de validação para o corpo da requisição de registrar venda."""
    sell_id: str
    id_caixa: str
    operator: str
    total_value: float
    payment_method: str
    received_value: Optional[float] = None
    change: Optional[float] = None
    items: List[ItemSoldPayload] = Field(min_length=1) # Deve ter pelo menos 1 item

# ============================================
# ==== POST - /BRATZ/FINANCES/REGISTER-SELL ====
# ============================================
@finances_bp.route('/finances/register-sell', methods=['POST'])
@auth_utils.token_required
@auth_utils.privilege_required("DOWN_STORAGE")
def register_sell():
    """
    Registra uma nova venda e dá baixa no estoque.
    Requer privilégio 'DOWN_STORAGE'.
    """
    data = request.get_json(silent=True) or {}
    
    try:
        # Validação do payload com Pydantic
        payload = RegisterSellPayload(**data)
    except ValidationError as e:
        return error_response(f"Validation Error: {e.errors()}", 400)

    try:
        new_sell = Sell(
            id=payload.sell_id,
            id_caixa=payload.id_caixa,
            operator=payload.operator,
            sell_time=datetime.utcnow(),
            total_value=payload.total_value,
            payment_method=payload.payment_method,
            received_value=payload.received_value,
            change=payload.change
        )
        db.session.add(new_sell)

        for item_data in payload.items:
            product = Product.query.get(item_data.product_id)
            
            if not product:
                raise ValueError(f"Produto com ID {item_data.product_id} não encontrado.")

            if product.quantity_in_stock < item_data.quantity:
                raise ValueError(f"Estoque insuficiente para o produto '{product.item}'. Disponível: {product.quantity_in_stock}")

            product.quantity_in_stock -= item_data.quantity

            new_sold_item = ItemSold(
                sell_id=new_sell.id,
                product_id=item_data.product_id,
                product_name=item_data.product_name,
                quantity=item_data.quantity,
                unit_value=item_data.unit_value,
                total_value=item_data.total_value_item
            )
            db.session.add(new_sold_item)
            
        db.session.commit()

        return success_response(
            "Venda registrada com sucesso!",
            {'sell_id': new_sell.id},
            201
        )

    except (ValueError, Exception) as e:
        db.session.rollback()
        return error_response(str(e), 500)

# ====================================
# ==== GET - /BRATZ/FINANCES/SELLS ====
# ====================================
@finances_bp.route('/finances/sells', methods=['GET'])
@auth_utils.token_required
@auth_utils.admin_required
def get_all_sells():
    """
    Retorna todas as vendas com paginação.
    Apenas para usuários administradores.
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    try:
        sells_pagination = Sell.query.order_by(Sell.sell_time.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        sells_data = [sell.to_dict() for sell in sells_pagination.items]

        return success_response("Sells retrieved successfully", {
            'sells': sells_data,
            'total': sells_pagination.total,
            'pages': sells_pagination.pages,
            'current_page': sells_pagination.page
        })

    except Exception as e:
        return error_response(str(e), 500)
    
# =========================================================
# ==== GET - /BRATZ/FINANCES/SPECIFIC/<ID>/SELLS ====
# =========================================================
@finances_bp.route('/finances/specific/<string:cashier_id>/sells', methods=['GET'])
@auth_utils.token_required
def get_specific_sells(cashier_id):
    """
    Retorna as vendas de um caixa específico, com lógica de permissão.
    - Admins: Veem todas as vendas do caixa.
    - Caixas: Veem apenas suas próprias vendas da última semana.
    """
    current_user = g.current_user
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    is_admin = current_user.privileges.get('ALL', False) or current_user.privileges.get('ADMIN', False)
    is_caixa = current_user.account_type == 'CAIXA'
    
    user_cashier_id = None
    if is_caixa and isinstance(current_user.profile, dict):
        user_cashier_id = str(current_user.profile.get("register_number", None))

    if not is_admin and (not is_caixa or user_cashier_id != cashier_id):
        return error_response('Acesso negado. Permissão insuficiente.', 403)

    try:
        query = Sell.query.filter_by(id_caixa=cashier_id)

        if not is_admin:
            one_week_ago = datetime.utcnow() - timedelta(days=7)
            query = query.filter(Sell.sell_time >= one_week_ago)
        
        sells_pagination = query.order_by(Sell.sell_time.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        sells_data = [sell.to_dict() for sell in sells_pagination.items]

        return success_response("Sells for cashier retrieved successfully", {
            'sells': sells_data,
            'total': sells_pagination.total,
            'pages': sells_pagination.pages,
            'current_page': sells_pagination.page
        })

    except Exception as e:
        return error_response(f'Ocorreu um erro interno: {str(e)}', 500)