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
from models.supplier import Supplier
from models.finances import Sell, ItemSold
from models.stock import Stock, stock_item
from utils.accounts import DEFAULT_PRIVILEGES, ACCOUNT_CAIXA

# --- Dados Iniciais Centralizados ---

CORE_USERS = [
    {"filters": {"email": "owner@market.com"}, "defaults": {"account_type": "OWNER", "privileges": {"ADMIN": True, "ALL": True}, "password": "StrongPass123!"}},
    {"filters": {"email": "caixa01@market.com"}, "defaults": {"account_type": "CAIXA", "privileges": DEFAULT_PRIVILEGES[ACCOUNT_CAIXA], "profile": {"register_number": "CX001", "operator_name": "Caixa Padrão"}, "password": "CaixaPass123!"}}
]

INITIAL_SUPPLIERS = [
    {"filters": {"name": "Distribuidora Bratz"}, "defaults": {"cnpj": "12.345.678/0001-99", "contact_person": "Maria Bratz", "phone": "48999990000", "email": "contato@bratz.com", "address": "Rua das Flores, 123"}},
    {"filters": {"name": "Schenatto Horses Co."}, "defaults": {"cnpj": "98.765.432/0001-11", "contact_person": "João Schenatto", "phone": "48988887777", "email": "contato@schenatto.com", "address": "Av. Cavalos, 456"}}
]

INITIAL_PRODUCTS = [
    {"filters": {"item": "Shampoo", "brand": "Bratz"}, "defaults": {"purchase_value": 5.50, "sale_value": 12.99, "category": "Higiene"}, "stock_quantity": 100},
    {"filters": {"item": "Condicionador", "brand": "Bratz"}, "defaults": {"purchase_value": 6.00, "sale_value": 13.99, "category": "Higiene"}, "stock_quantity": 80},
    {"filters": {"item": "Chaveiro", "brand": "Schenatto Horses Co."}, "defaults": {"purchase_value": 3.00, "sale_value": 41.99, "category": "Acessórios"}, "stock_quantity": 12},
    {"filters": {"item": "Coca-Cola 2L", "brand": "Coca-Cola"}, "defaults": {"purchase_value": 6.50, "sale_value": 9.99, "category": "Bebidas"}, "stock_quantity": 150, "supplier_name": "Distribuidora Bratz"},
    {"filters": {"item": "Boné Trucker", "brand": "Schenatto Horses Co."}, "defaults": {"purchase_value": 25.00, "sale_value": 89.90, "category": "Acessórios"}, "stock_quantity": 20, "supplier_name": "Schenatto Horses Co."}
]

INITIAL_CLIENTS = [
    {"filters": {"cpf": "12345678900"}, "defaults": {"name": "Daniel Prâmio", "phone": "49999998888", "discounts": {"Acessórios": 10.0}}},
    {"filters": {"cpf": "22345678900"}, "defaults": {"name": "Cecilio Balbinott", "phone": "47999998888", "discounts": {"Higiene": 15.0, "geral": 5.0}}}
]

# --- Funções Auxiliares ---

@contextmanager
def session_scope():
    """Fornece um escopo transacional seguro para as operações de seeding."""
    session = db.session
    try:
        yield session
        session.commit()
    except Exception:
        print("!!! Ocorreu um erro. Revertendo todas as alterações (rollback).")
        session.rollback()
        raise
    finally:
        session.close()

def _find_or_create(session, model, defaults, **filters):
    """Função genérica para encontrar um registro ou criá-lo se não existir."""
    instance = session.query(model).filter_by(**filters).first()
    if instance:
        return instance, False
    else:
        params = {**filters, **defaults}
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
    return session.query(User).filter_by(email="caixa01@market.com").first()

def seed_suppliers(session):
    """Popula os fornecedores iniciais e retorna um dicionário para referência."""
    print("--- Populando fornecedores...")
    suppliers = {}
    for supplier_data in INITIAL_SUPPLIERS:
        supplier, created = _find_or_create(session, Supplier, supplier_data['defaults'], **supplier_data['filters'])
        suppliers[supplier.name] = supplier
        if created:
            print(f"    -> Fornecedor '{supplier.name}' criado.")
        else:
            print(f"    -> Fornecedor '{supplier.name}' já existe.")
    return suppliers

def seed_products_and_stock(session, suppliers: dict):
    """Popula os produtos, vincula fornecedores e associa ao estoque 'Geral'."""
    print("--- Populando produtos e estoque...")
    geral_stock, created = _find_or_create(session, Stock, {"description": "Estoque principal da loja"}, name="Geral")
    if created:
        print("    -> Estoque 'Geral' criado.")
    else:
        print("    -> Estoque 'Geral' já existe.")
    
    session.flush() # Garante que geral_stock.id esteja disponível

    products_map = {}
    for product_data in INITIAL_PRODUCTS:
        # Vincula o fornecedor ao produto se especificado
        supplier_name = product_data.get("supplier_name")
        if supplier_name and supplier_name in suppliers:
            product_data["defaults"]["supplier_id"] = suppliers[supplier_name].id

        product, created = _find_or_create(session, Product, product_data['defaults'], **product_data['filters'])
        products_map[product.item] = product # Salva no mapa para referência
        
        if created:
            print(f"    -> Produto '{product.item}' criado.")
            session.flush() # Garante que product.id esteja disponível
            
            print(f"       + Adicionando {product_data['stock_quantity']} unidades ao estoque '{geral_stock.name}'.")
            insert_stmt = db.insert(stock_item).values(
                stock_id=geral_stock.id,
                product_id=product.id,
                quantity=product_data['stock_quantity']
            )
            session.execute(insert_stmt)
        else:
            print(f"    -> Produto '{product.item}' já existe.")
    
    return products_map

def seed_clients(session):
    """Popula os clientes iniciais."""
    print("--- Populando clientes...")
    for client_data in INITIAL_CLIENTS:
        client, created = _find_or_create(session, Client, client_data['defaults'], **client_data['filters'])
        if created:
            print(f"    -> Cliente '{client.name}' criado.")
        else:
            print(f"    -> Cliente '{client.name}' já existe.")

def seed_sales(session, cashier_user, products_map: dict):
    """Popula uma venda de exemplo, se nenhuma existir."""
    print("--- Populando vendas de exemplo...")
    if session.query(Sell).first():
        print("    -> Vendas já existem no banco. Pulando.")
        return

    shampoo = products_map.get("Shampoo")
    if not cashier_user or not shampoo:
        print("    -> Usuário caixa ou produto 'Shampoo' não encontrado. Pulando venda.")
        return
        
    print("    -> Criando uma venda de exemplo...")
    geral_stock = session.query(Stock).filter_by(name="Geral").one()

    new_sell = Sell(
        id=str(uuid.uuid4()),
        id_caixa=cashier_user.profile.get("register_number"),
        operator=cashier_user.profile.get("operator_name"),
        total_value=shampoo.sale_value,
        payment_method="dinheiro",
        received_value=15.00,
        change=15.00 - shampoo.sale_value
    )
    session.add(new_sell)

    item_vendido = ItemSold(
        sell_id=new_sell.id,
        product_id=shampoo.id,
        product_name=f"{shampoo.item} {shampoo.brand}",
        quantity=1,
        unit_value=shampoo.sale_value,
        total_value=shampoo.sale_value
    )
    session.add(item_vendido)

    print(f"       - Debitando 1 unidade de '{shampoo.item}' do estoque 'Geral'.")
    update_stock_stmt = db.update(stock_item).where(
        stock_item.c.stock_id == geral_stock.id,
        stock_item.c.product_id == shampoo.id
    ).values(quantity=stock_item.c.quantity - 1)
    session.execute(update_stock_stmt)

def main_seeder():
    """Função principal que orquestra todo o processo de seeding."""
    app = create_app()
    with app.app_context():
        print("--- INICIANDO PROCESSO DE SEEDING DO BANCO DE DADOS ---")
        try:
            with session_scope() as session:
                cashier = seed_users(session)
                suppliers = seed_suppliers(session)
                products = seed_products_and_stock(session, suppliers)
                seed_clients(session)
                seed_sales(session, cashier_user=cashier, products_map=products)
            print("\n--- SEEDING CONCLUÍDO COM SUCESSO! ---")
        except Exception as e:
            print(f"\n--- OCORREU UM ERRO DURANTE O SEEDING: {e} ---")

if __name__ == "__main__":
    main_seeder()