from flask import Blueprint, request, jsonify, g
from models.finances import Sell, ItemSold 
from models.product import Product
from models.stock import Stock, stock_item 
from utils.extensions import db
import utils.auth as auth_utils
from datetime import datetime, timedelta

finances_bp = Blueprint('finances_bp', __name__)

@finances_bp.route('/finances/register-sell', methods=['POST'])
@auth_utils.token_required
def register_sell():
    """
    Registra uma nova venda, debitando os itens do estoque padrão "Geral".
    """
    data = request.get_json()

    required_fields = ['sell_id', 'id_caixa', 'operator', 'total_value', 'payment_method', 'items']
    if not all(field in data for field in required_fields):
        return jsonify({'status': 'error', 'message': 'Dados incompletos enviados.'}), 400

    if not data['items']:
        return jsonify({'status': 'error', 'message': 'A venda deve conter pelo menos um item.'}), 400

    try:
        # Pega o estoque "Geral". Se não existir, a venda não pode continuar.
        geral_stock = Stock.query.filter_by(name="Geral").one_or_none()
        if not geral_stock:
            raise Exception("Estoque 'Geral' não foi encontrado. A operação de venda está bloqueada.")

        new_sell = Sell(
            id=data['sell_id'],
            id_caixa=data['id_caixa'],
            operator=data['operator'],
            sell_time=datetime.utcnow(),
            total_value=data['total_value'],
            payment_method=data['payment_method'],
            received_value=data.get('received_value'),
            change=data.get('change')
        )
        db.session.add(new_sell)

        for item_data in data['items']:
            product = Product.query.get(item_data['product_id'])
            
            if not product:
                raise Exception(f"Produto com ID {item_data['product_id']} não encontrado.")

            # --- LÓGICA DE ESTOQUE ATUALIZADA ---
            # 1. Busca a quantidade atual do produto no estoque 'Geral'
            stmt = db.select(stock_item.c.quantity).where(
                stock_item.c.stock_id == geral_stock.id,
                stock_item.c.product_id == product.id
            )
            current_quantity = db.session.execute(stmt).scalar_one_or_none()

            # 2. Verifica se há estoque suficiente
            if current_quantity is None or current_quantity < item_data['quantity']:
                raise Exception(f"Estoque insuficiente para '{product.item}' no estoque '{geral_stock.name}'. Disponível: {current_quantity or 0}")

            # 3. Debita a quantidade vendida do estoque 'Geral'
            update_stmt = db.update(stock_item).where(
                stock_item.c.stock_id == geral_stock.id,
                stock_item.c.product_id == product.id
            ).values(quantity=stock_item.c.quantity - item_data['quantity'])
            db.session.execute(update_stmt)
            
            # Cria o registro do item que foi vendido
            new_sold_item = ItemSold(
                sell_id=new_sell.id,
                product_id=item_data['product_id'],
                product_name=item_data['product_name'],
                quantity=item_data['quantity'],
                unit_value=item_data['unit_value'],
                total_value=item_data['total_value_item']
            )
            db.session.add(new_sold_item)
            
        db.session.commit()

        return jsonify({
            'status': 'success',
            'message': 'Venda registrada com sucesso!',
            'data': {'sell_id': new_sell.id}
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
@finances_bp.route('/finances/sells', methods=['GET'])
@auth_utils.token_required
def get_all_sells():
    """
    Retorna todas as vendas. Apenas para usuários administradores.
    """
    current_user = g.current_user
    is_admin = current_user.privileges.get('ALL', False) or current_user.privileges.get('ADMIN', False)
    if not is_admin:
        return jsonify({
            'status': 'error',
            'message': 'Acesso negado. Permissão de administrador necessária.'
        }), 403

    try:
        sells = Sell.query.order_by(Sell.sell_time.desc()).all()
        sells_data = [sell.to_dict() for sell in sells]
        return jsonify({
            'status': 'success',
            'data': {
                'sells': sells_data
            }
        }), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
@finances_bp.route('/finances/specific/<string:cashier_id>/sells', methods=['GET'])
@auth_utils.token_required
def get_specific_sells(cashier_id):
    """
    Retorna as vendas de um caixa específico.
    """
    current_user = g.current_user
    is_admin = current_user.privileges.get('ALL', False) or current_user.privileges.get('ADMIN', False)
    is_caixa = current_user.account_type == 'CAIXA'
    
    user_cashier_id = None
    if is_caixa and isinstance(current_user.profile, dict):
        user_cashier_id = str(current_user.profile.get("register_number", None))

    if not is_admin and (not is_caixa or user_cashier_id != cashier_id):
        return jsonify({
            'status': 'error',
            'message': 'Acesso negado. Permissão insuficiente para ver as vendas deste caixa.'
        }), 403

    try:
        query = Sell.query.filter_by(id_caixa=cashier_id)

        if not is_admin:
            one_week_ago = datetime.utcnow() - timedelta(days=7)
            query = query.filter(Sell.sell_time >= one_week_ago)
        
        sells = query.order_by(Sell.sell_time.desc()).all()

        if not sells:
            return jsonify({
                'status': 'success',
                'message': f'Nenhuma venda encontrada para o caixa {cashier_id} no período especificado.',
                'data': {'sells': []}
            }), 200

        sells_data = [sell.to_dict() for sell in sells]

        return jsonify({
            'status': 'success',
            'data': {'sells': sells_data}
        }), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': 'Ocorreu um erro interno ao processar a solicitação.'}), 500