"""
Blueprint para Gerenciamento Financeiro
---------------------------------------
Este módulo contém todas as rotas da API relacionadas a operações financeiras,
incluindo o registro de vendas e a geração de relatórios e resumos analíticos
para o BratzADM.
"""

from flask import Blueprint, request, g
from pydantic import BaseModel, Field, ValidationError
from typing import List
from models.finances import Sell, ItemSold 
from models.product import Product
from models.stock import Stock, stock_item 
from utils.extensions import db
import utils.auth as auth_utils
from utils.responses import success_response, error_response
from datetime import datetime, date, timedelta
from sqlalchemy import func, extract

finances_bp = Blueprint("finances", __name__)


# --- Modelos de Validação (Pydantic) ---

class ItemPayload(BaseModel):
    """Valida os dados de um item dentro de uma venda."""
    product_id: int
    product_name: str
    quantity: int = Field(gt=0)
    unit_value: float = Field(ge=0)
    # O nome do campo agora é 'total_value' para ser consistente com o modelo do BD
    total_value: float = Field(ge=0)

class SellPayload(BaseModel):
    """Valida o payload completo para o registro de uma nova venda."""
    # O nome do campo agora é 'id' para ser consistente com o modelo do BD
    id: str
    id_caixa: str
    operator: str
    total_value: float
    payment_method: str
    items: List[ItemPayload] = Field(min_length=1)
    received_value: float | None = None
    change: float | None = None
    client_id: int | None = None


# --- Funções Auxiliares ---

def _parse_date_or_default(date_str: str | None, default_date: date) -> date:
    """Converte uma string YYYY-MM-DD para um objeto date, com um fallback seguro."""
    if not date_str:
        return default_date
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return default_date

# ==================================
# ==== OPERAÇÕES BÁSICAS DE VENDA ====
# ==================================

@finances_bp.route('/finances/register-sell', methods=['POST'])
@auth_utils.token_required
@auth_utils.privilege_required("DOWN_STORAGE") # Apenas caixas podem registrar vendas
def register_sell():
    """Registra uma nova venda, debitando os itens do estoque 'Geral'."""
    data = request.get_json(silent=True) or {}
    try:
        # A validação do Pydantic agora espera 'id' e 'total_value'
        payload = SellPayload(**data)
    except ValidationError as e:
        return error_response(f"Validation Error: {e.errors()}", 400)

    try:
        # Garante que a operação ocorra dentro de uma transação atômica
        with db.session.begin_nested():
            geral_stock = db.session.query(Stock).filter_by(name="Geral").with_for_update().one_or_none()
            if not geral_stock:
                raise Exception("Estoque 'Geral' não foi encontrado. A operação de venda está bloqueada.")

            # O construtor de Sell espera 'id', não 'sell_id'
            new_sell = Sell(**payload.model_dump(exclude={'items'}))
            new_sell.sell_time = datetime.utcnow()
            db.session.add(new_sell)

            for item_data in payload.items:
                update_stmt = db.update(stock_item).where(
                    stock_item.c.stock_id == geral_stock.id,
                    stock_item.c.product_id == item_data.product_id,
                    stock_item.c.quantity >= item_data.quantity
                ).values(quantity=stock_item.c.quantity - item_data.quantity)
                
                result = db.session.execute(update_stmt)

                if result.rowcount == 0:
                    product = db.session.get(Product, item_data.product_id)
                    raise Exception(f"Estoque insuficiente para o produto '{product.item if product else 'ID desconhecido'}'.")
                
                # O construtor de ItemSold espera 'total_value', não 'total_value_item'
                new_sold_item = ItemSold(**item_data.model_dump(), sell_id=new_sell.id)
                db.session.add(new_sold_item)
        
        db.session.commit()
        return success_response('Venda registrada com sucesso!', {'sell_id': new_sell.id}, 201)
    except Exception as e:
        db.session.rollback()
        return error_response(str(e), 500)

@finances_bp.route('/finances/sells', methods=['GET'])
@auth_utils.token_required
@auth_utils.admin_required
def get_all_sells():
    """Retorna todas as vendas. Requer privilégio de Administrador."""
    sells = Sell.query.order_by(Sell.sell_time.desc()).all()
    sells_data = [s.to_dict() for s in sells]
    return success_response("Vendas recuperadas com sucesso.", {'sells': sells_data})

@finances_bp.route('/finances/specific/<string:cashier_id>/sells', methods=['GET'])
@auth_utils.token_required
def get_specific_sells(cashier_id: str):
    """Retorna as vendas de um caixa específico."""
    user = g.current_user
    is_admin = user.privileges.get('ALL', False) or user.privileges.get('ADMIN', False)
    
    if not is_admin:
        if user.account_type != 'CAIXA' or user.profile.get("register_number") != cashier_id:
            return error_response('Acesso negado.', 403)

    query = Sell.query.filter_by(id_caixa=cashier_id)
    if not is_admin:
        query = query.filter(Sell.sell_time >= datetime.utcnow() - timedelta(days=7))
    
    sells = query.order_by(Sell.sell_time.desc()).all()
    sells_data = [s.to_dict() for s in sells]
    return success_response(f"Vendas para o caixa {cashier_id} recuperadas.", {'sells': sells_data})

# ==================================
# ==== RESUMOS E RELATÓRIOS ====
# ==================================

@finances_bp.route('/finances/summary/daily', methods=['GET'])
@auth_utils.token_required
@auth_utils.privilege_required("FINANCE")
def get_daily_summary():
    """Retorna um resumo financeiro para um dia específico."""
    target_date = _parse_date_or_default(request.args.get('date'), date.today())
    
    summary = db.session.query(
        func.sum(Sell.total_value).label('total_revenue'),
        func.count(Sell.id).label('total_sales_count'),
        func.sum(ItemSold.quantity).label('total_items_sold')
    ).join(ItemSold, Sell.id == ItemSold.sell_id)\
     .filter(func.date(Sell.sell_time) == target_date).one()

    total_revenue = float(summary.total_revenue or 0)
    total_sales_count = summary.total_sales_count or 0
    
    response_data = {
        "date": target_date.isoformat(),
        "total_revenue": total_revenue,
        "total_sales_count": total_sales_count,
        "total_items_sold": int(summary.total_items_sold or 0),
        "average_ticket": total_revenue / total_sales_count if total_sales_count > 0 else 0
    }
    return success_response(f"Resumo para a data {target_date.strftime('%d/%m/%Y')}.", response_data)

@finances_bp.route('/finances/summary/monthly', methods=['GET'])
@auth_utils.token_required
@auth_utils.privilege_required("FINANCE")
def get_monthly_summary():
    """Retorna um resumo financeiro para um mês e ano específicos."""
    today = date.today()
    year = request.args.get('year', today.year, type=int)
    month = request.args.get('month', today.month, type=int)

    summary = db.session.query(
        func.sum(Sell.total_value).label('total_revenue'),
        func.count(Sell.id).label('total_sales_count'),
        func.sum(ItemSold.quantity).label('total_items_sold')
    ).join(ItemSold, Sell.id == ItemSold.sell_id)\
     .filter(extract('year', Sell.sell_time) == year, extract('month', Sell.sell_time) == month).one()
    
    total_revenue = float(summary.total_revenue or 0)
    total_sales_count = summary.total_sales_count or 0

    response_data = {
        "month": f"{str(month).zfill(2)}/{year}",
        "total_revenue": total_revenue,
        "total_sales_count": total_sales_count,
        "total_items_sold": int(summary.total_items_sold or 0),
        "average_ticket": total_revenue / total_sales_count if total_sales_count > 0 else 0
    }
    return success_response(f"Resumo para o mês {month}/{year}.", response_data)

@finances_bp.route('/finances/reports/sales-flow', methods=['GET'])
@auth_utils.token_required
@auth_utils.privilege_required("FINANCE")
def get_sales_flow_report():
    """Retorna o faturamento diário em um período, ideal para gráficos."""
    start_date = _parse_date_or_default(request.args.get('start_date'), date.today() - timedelta(days=30))
    end_date = _parse_date_or_default(request.args.get('end_date'), date.today())

    results = db.session.query(
        func.date(Sell.sell_time).label('sale_date'),
        func.sum(Sell.total_value).label('daily_revenue')
    ).filter(Sell.sell_time.between(start_date, end_date + timedelta(days=1)))\
     .group_by('sale_date').order_by('sale_date').all()
    
    sales_flow = [{"date": r.sale_date.isoformat(), "revenue": float(r.daily_revenue)} for r in results]
    
    response_data = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "sales_flow": sales_flow
    }
    return success_response("Fluxo de vendas recuperado.", response_data)

@finances_bp.route('/finances/reports/payment-methods', methods=['GET'])
@auth_utils.token_required
@auth_utils.privilege_required("FINANCE")
def get_payment_methods_report():
    """Agrupa o faturamento por método de pagamento em um período."""
    start_date = _parse_date_or_default(request.args.get('start_date'), date.today() - timedelta(days=30))
    end_date = _parse_date_or_default(request.args.get('end_date'), date.today())

    results = db.session.query(
        Sell.payment_method,
        func.sum(Sell.total_value).label('total_revenue'),
        func.count(Sell.id).label('sales_count')
    ).filter(Sell.sell_time.between(start_date, end_date + timedelta(days=1)))\
     .group_by(Sell.payment_method).order_by(func.sum(Sell.total_value).desc()).all()

    payment_summary = [{
        "method": r.payment_method,
        "total_revenue": float(r.total_revenue),
        "sales_count": r.sales_count
    } for r in results]

    response_data = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "payment_summary": payment_summary
    }
    return success_response("Relatório por método de pagamento gerado.", response_data)

@finances_bp.route('/finances/reports/profit-margin', methods=['GET'])
@auth_utils.token_required
@auth_utils.privilege_required("FINANCE")
def get_profit_margin_report():
    """Calcula o lucro bruto e a margem de lucro para um período."""
    start_date = _parse_date_or_default(request.args.get('start_date'), date.today() - timedelta(days=30))
    end_date = _parse_date_or_default(request.args.get('end_date'), date.today())
    
    report = db.session.query(
        func.sum(ItemSold.total_value).label('total_revenue'),
        func.sum(ItemSold.quantity * Product.purchase_value).label('total_cost_of_goods')
    ).join(Sell, ItemSold.sell_id == Sell.id)\
     .join(Product, ItemSold.product_id == Product.id)\
     .filter(Product.purchase_value.isnot(None))\
     .filter(Sell.sell_time.between(start_date, end_date + timedelta(days=1))).one()

    total_revenue = float(report.total_revenue or 0)
    total_cost = float(report.total_cost_of_goods or 0)
    gross_profit = total_revenue - total_cost

    response_data = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_revenue": total_revenue,
        "total_cost_of_goods": total_cost,
        "gross_profit": gross_profit,
        "profit_margin_percent": (gross_profit / total_revenue * 100) if total_revenue > 0 else 0
    }
    return success_response("Relatório de margem de lucro gerado.", response_data)