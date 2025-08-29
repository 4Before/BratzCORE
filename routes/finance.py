from flask import Blueprint, request, jsonify
from models.finances import Sell, ItemSold 
from models.product import Product
from utils.extensions import db
import utils.auth as auth_utils
from datetime import datetime

finances_bp = Blueprint('finances_bp', __name__, url_prefix='/bratz/finances')

@finances_bp.route('/register-sell', methods=['POST'])
@auth_utils.token_required
def register_sell(current_user):
    data = request.get_json()

    required_fields = ['sell_id', 'id_caixa', 'operator', 'total_value', 'payment_method', 'items']
    if not all(field in data for field in required_fields):
        return jsonify({'status': 'error', 'message': 'Dados incompletos enviados.'}), 400

    if not data['items']:
        return jsonify({'status': 'error', 'message': 'A venda deve conter pelo menos um item.'}), 400

    try:
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

            if product.quantity_in_stock < item_data['quantity']:
                raise Exception(f"Estoque insuficiente para o produto '{product.item}'. Disponível: {product.quantity_in_stock}")

            product.quantity_in_stock -= item_data['quantity']

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