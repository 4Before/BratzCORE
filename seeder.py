"""
Script de Seeding para o Banco de Dados Bratz
---------------------------------------------
Este script popula o banco de dados com dados iniciais essenciais para o
ambiente de desenvolvimento e teste.

Ele é projetado para ser IDEMPOTENTE, o que significa que pode ser executado
múltiplas vezes sem criar dados duplicados.

IMPORTANTE:
Este script deve ser executado APÓS a criação e atualização do esquema do
banco de dados através dos comandos do Flask-Migrate:
1. flask db upgrade
2. python seeder.py
"""

import uuid
from datetime import datetime
from contextlib import contextmanager
from app import create_app, db
from models.user import User
from models.product import Product
from models.client import Client
from models.finances import Sell, ItemSold
from models.stock import Stock, stock_item
from models.supplier import Supplier

# --- Dados Iniciais Centralizados ---
# Manter os dados aqui facilita a visualização e modificação.

CORE_USERS = [
    {
        "filters": {"email": "owner@market.com"},
        "defaults": {
            "account_type": "OWNER",
            "privileges": {"ADMIN": True, "ALL": True},
            "password": "StrongPass123!"
        }
    },
    {
        "filters": {"email": "caixa01@market.com"},
        "defaults": {
            "account_type": "CAIXA",
            "privileges": {},
            "profile": {"register_number": "CX001", "operator_name": "Caixa Padrão"},
            "password": "CaixaPass123!"
        }
    }
]

INITIAL_PRODUCTS = [
    {
        "filters": {"item": "Shampoo", "brand": "Bratz"},
        "defaults": {
            "purchase_value": 5.50, "sale_value": 12.99, "category": "Higiene"
        },
        "stock_quantity": 100
    },
    {
        "filters": {"item": "Condicionador", "brand": "Bratz"},
        "defaults": {
            "purchase_value": 6.00, "sale_value": 13.99, "category": "Higiene"
        },
        "stock_quantity": 80
    },
    {
        "filters": {"item": "Chaveiro", "brand": "Schenatto Horses Co."},
        "defaults": {
            "purchase_value": 3.00, "sale_value": 41.99, "category": "Horses"
        },
        "stock_quantity": 12
    }
]

INITIAL_CLIENTS = [
    {
        "filters": {"cpf": "12345678900"},
        "defaults": {
            "name": "Daniel Prâmio", "phone": "49999998888", "discounts": {"Horses": 0.1}, 
        }
    },
        {
        "filters": {"cpf": "22345678900"},
        "defaults": {
            "name": "Cecilio Balbinott", "phone": "47999998888", "discounts": {"Higiene": 0.1}, 
        }
    }
]

INITIAL_SUPPLIERS = [
    {
        "filters": {"name": "Distribuidora Bratz"},
        "defaults": {
            "cnpj": "12.345.678/0001-99",
            "contact_person": "Maria Bratz",
            "phone": "48999990000",
            "email": "contato@bratz.com",
            "address": "Rua das Flores, 123, Centro, Cidade/UF"
        }
    },
    {
        "filters": {"name": "Schenatto Horses Co."},
        "defaults": {
            "cnpj": "98.765.432/0001-11",
            "contact_person": "João Schenatto",
            "phone": "48988887777",
            "email": "contato@schenatto.com",
            "address": "Av. Cavalos, 456, Bairro Rural, Cidade/UF"
        }
    }
]


# --- Funções Auxiliares ---

@contextmanager
def session_scope():
    """Fornece um escopo transacional para uma série de operações."""
    session = db.session
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _find_or_create(session, model, defaults, **filters):
    """
    Função auxiliar genérica para encontrar um registro ou criá-lo se não existir.
    Retorna a instância do objeto e um booleano indicando se foi criado.
    """
    instance = session.query(model).filter_by(**filters).first()
    if instance:
        return instance, False
    else:
        # Mescla os filtros com os valores padrão para criar a nova instância
        params = {**filters, **defaults}
        # A senha é tratada de forma especial
        password = params.pop('password', None)
        instance = model(**params)
        if password and hasattr(instance, 'set_password'):
            instance.set_password(password)
        session.add(instance)
        return instance, True


# --- Funções de Seeding por Módulo ---

def seed_users(session):
    """Popula as contas de usuário essenciais."""
    print("--- Populando usuários...")
    for user_data in CORE_USERS:
        user, created = _find_or_create(session, User, user_data['defaults'], **user_data['filters'])
        if created:
            print(f"    -> Usuário '{user.email}' criado.")
        else:
            print(f"    -> Usuário '{user.email}' já existe.")
    return User.query.filter_by(email="caixa01@market.com").first()


def seed_products_and_stock(session):
    """Popula os produtos iniciais e os associa ao estoque 'Geral'."""
    print("--- Populando produtos e estoque...")
    geral_stock, created = _find_or_create(session, Stock, {"description": "Estoque principal da loja"}, name="Geral")
    if created:
        print("    -> Estoque 'Geral' criado.")
    else:
        print("    -> Estoque 'Geral' já existe.")
    
    # É necessário dar um flush para que geral_stock.id seja populado antes de usá-lo
    session.flush()

    products = []
    for product_data in INITIAL_PRODUCTS:
        product, created = _find_or_create(session, Product, product_data['defaults'], **product_data['filters'])
        products.append(product)
        if created:
            print(f"    -> Produto '{product.item}' criado.")
            # Associa o produto recém-criado ao estoque 'Geral'
            session.flush() # Garante que product.id esteja disponível
            print(f"       + Adicionando {product_data['stock_quantity']} unidades ao estoque 'Geral'.")
            insert_stmt = db.insert(stock_item).values(
                stock_id=geral_stock.id,
                product_id=product.id,
                quantity=product_data['stock_quantity']
            )
            session.execute(insert_stmt)
        else:
            print(f"    -> Produto '{product.item}' já existe.")
    
    return products[0] # Retorna o shampoo para a criação da venda


def seed_clients(session):
    """Popula os clientes iniciais."""
    print("--- Populando clientes...")
    for client_data in INITIAL_CLIENTS:
        client, created = _find_or_create(session, Client, client_data['defaults'], **client_data['filters'])
        if created:
            print(f"    -> Cliente '{client.name}' criado.")
        else:
            print(f"    -> Cliente '{client.name}' já existe.")

def seed_suppliers(session):
    """Popula os fornecedores iniciais."""
    print("--- Populando fornecedores...")
    for supplier_data in INITIAL_SUPPLIERS:
        supplier, created = _find_or_create(session, Supplier, supplier_data['defaults'], **supplier_data['filters'])
        if created:
            print(f"    -> Fornecedor '{supplier.name}' criado.")
        else:
            print(f"    -> Fornecedor '{supplier.name}' já existe.")

def seed_sales(session, cashier_user, product_to_sell):
    """Popula uma venda de exemplo, se nenhuma existir."""
    print("--- Populando vendas de exemplo...")
    if session.query(Sell).first():
        print("    -> Vendas já existem no banco. Pulando.")
        return

    if not cashier_user or not product_to_sell:
        print("    -> Usuário caixa ou produto de exemplo não encontrado. Pulando.")
        return
        
    print("    -> Criando uma venda de exemplo...")
    geral_stock = session.query(Stock).filter_by(name="Geral").one()

    new_sell = Sell(
        id=str(uuid.uuid4()),
        id_caixa=cashier_user.profile.get("register_number"),
        operator=cashier_user.profile.get("operator_name"),
        sell_time=datetime.utcnow(),
        total_value=product_to_sell.sale_value,
        payment_method="dinheiro",
        received_value=15.00,
        change=15.00 - product_to_sell.sale_value
    )
    session.add(new_sell)

    item_vendido = ItemSold(
        sell_id=new_sell.id,
        product_id=product_to_sell.id,
        product_name=f"{product_to_sell.item} {product_to_sell.brand}",
        quantity=1,
        unit_value=product_to_sell.sale_value,
        total_value=product_to_sell.sale_value
    )
    session.add(item_vendido)

    print(f"       - Debitando 1 unidade de '{product_to_sell.item}' do estoque 'Geral'.")
    update_stock_stmt = db.update(stock_item).where(
        stock_item.c.stock_id == geral_stock.id,
        stock_item.c.product_id == product_to_sell.id
    ).values(quantity=stock_item.c.quantity - 1)
    session.execute(update_stock_stmt)


def seed_database():
    """Função principal que orquestra todo o processo de seeding."""
    app = create_app()
    with app.app_context():
        print("--- INICIANDO PROCESSO DE SEEDING DO BANCO DE DADOS ---")
        try:
            with session_scope() as session:
                cashier = seed_users(session)
                seed_suppliers(session)
                shampoo = seed_products_and_stock(session)
                seed_clients(session)
                seed_sales(session, cashier_user=cashier, product_to_sell=shampoo)
            print("\n--- SEEDING CONCLUÍDO COM SUCESSO! ---")
        except Exception as e:
            print(f"\n--- OCORREU UM ERRO DURANTE O SEEDING: {e} ---")
            print("--- NENHUMA ALTERAÇÃO FOI SALVA NO BANCO DE DADOS. ---")


if __name__ == "__main__":
    seed_database()