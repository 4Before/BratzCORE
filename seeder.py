# seeder.py
import uuid
from datetime import datetime
from app import create_app, db
from models.user import User
from models.product import Product
from models.client import Client
from models.finances import Sell, ItemSold
from models.stock import Stock, stock_item

app = create_app()

def seed_database():
    """
    Função principal para popular o banco de dados com dados iniciais.
    Verifica a existência de dados antes de inseri-los para evitar duplicatas.
    """
    with app.app_context():
        print("--- INICIANDO PROCESSO DE SEEDING DO BANCO DE DADOS ---")
        
        # 1. Garante que todas as tabelas estão criadas
        print("--- Verificando e criando tabelas do banco de dados... ---")
        db.create_all()
        print("--- Verificação de tabelas concluída. ---")

        # --- SEEDING DE USUÁRIOS ---
        
        # 2. Usuário OWNER (Admin Principal)
        owner_email = "owner@market.com"
        if not User.query.filter_by(email=owner_email).first():
            print(f"--- Usuário OWNER '{owner_email}' não encontrado, criando... ---")
            owner_user = User(
                email=owner_email, 
                account_type="OWNER", 
                privileges={"ADMIN": True, "ALL": True}
            )
            owner_user.set_password("StrongPass123!")
            db.session.add(owner_user)
            print(f"--- OWNER criado com sucesso: {owner_email} / StrongPass123! ---")
        else:
            print(f"--- Usuário OWNER '{owner_email}' já existe, pulando. ---")

        # 3. Usuário CAIXA
        cashier_email = "caixa01@market.com"
        cashier_user = User.query.filter_by(email=cashier_email).first()
        if not cashier_user:
            print(f"--- Usuário CAIXA '{cashier_email}' não encontrado, criando... ---")
            cashier_user = User(
                email=cashier_email, 
                account_type="CAIXA", 
                privileges={},
                profile={"register_number": "CX001", "name": "Caixa Padrão"}
            )
            cashier_user.set_password("CaixaPass123!")
            db.session.add(cashier_user)
            print(f"--- CAIXA criado com sucesso: {cashier_email} / CaixaPass123! ---")
        else:
            print(f"--- Usuário CAIXA '{cashier_email}' já existe, pulando. ---")


        # --- SEEDING DE ESTOQUE (LOCAL) ---
        geral_stock = Stock.query.filter_by(name="Geral").first()
        if not geral_stock:
            print("--- Criando estoque padrão 'Geral'... ---")
            geral_stock = Stock(name="Geral", description="Estoque principal da loja")
            db.session.add(geral_stock)
        else:
            print("--- Estoque 'Geral' já existe, pulando. ---")

        # --- SEEDING DE PRODUTOS ---
        shampoo_product = Product.query.filter_by(item="Shampoo", brand="Bratz").first()
        if not shampoo_product:
            print("--- Criando produto 'Shampoo Bratz'... ---")
            shampoo_product = Product(
                item="Shampoo",
                brand="Bratz",
                purchase_value=5.50,
                sale_value=12.99
            )
            db.session.add(shampoo_product)
        else:
            print("--- Produto 'Shampoo Bratz' já existe, pulando. ---")

        condicionador_product = Product.query.filter_by(item="Condicionador", brand="Bratz").first()
        if not condicionador_product:
            print("--- Criando produto 'Condicionador Bratz'... ---")
            condicionador_product = Product(
                item="Condicionador",
                brand="Bratz",
                purchase_value=6.00,
                sale_value=13.99,
            )
            db.session.add(condicionador_product)
        else:
            print("--- Produto 'Condicionador Bratz' já existe, pulando. ---")
            
        # Força o commit para garantir que os IDs de produto e estoque estejam disponíveis
        db.session.commit()
        
        # Refresh nos objetos para garantir que eles tenham IDs
        geral_stock = Stock.query.filter_by(name="Geral").first()
        shampoo_product = Product.query.filter_by(item="Shampoo").first()
        condicionador_product = Product.query.filter_by(item="Condicionador").first()


        # --- ASSOCIANDO PRODUTOS AO ESTOQUE 'GERAL' ---
        stmt_shampoo = db.select(stock_item).where(stock_item.c.stock_id == geral_stock.id, stock_item.c.product_id == shampoo_product.id)
        if not db.session.execute(stmt_shampoo).first():
            print(f"--- Adicionando '{shampoo_product.item}' ao estoque '{geral_stock.name}'... ---")
            insert_stmt = db.insert(stock_item).values(stock_id=geral_stock.id, product_id=shampoo_product.id, quantity=100)
            db.session.execute(insert_stmt)

        stmt_condicionador = db.select(stock_item).where(stock_item.c.stock_id == geral_stock.id, stock_item.c.product_id == condicionador_product.id)
        if not db.session.execute(stmt_condicionador).first():
            print(f"--- Adicionando '{condicionador_product.item}' ao estoque '{geral_stock.name}'... ---")
            insert_stmt = db.insert(stock_item).values(stock_id=geral_stock.id, product_id=condicionador_product.id, quantity=80)
            db.session.execute(insert_stmt)
        

        # --- SEEDING DE CLIENTES ---
        client_cpf = "12345678900"
        if not Client.query.filter_by(cpf=client_cpf).first():
            print("--- Criando cliente 'Daniel Prâmio'... ---")
            new_client = Client(
                cpf=client_cpf,
                name="Daniel Prâmio",
                phone="49999998888"
            )
            db.session.add(new_client)
        else:
            print("--- Cliente 'Daniel Prâmio' já existe, pulando. ---")


        # --- SEEDING DE VENDAS ---
        if not Sell.query.first():
            cashier_user = User.query.filter_by(email=cashier_email).first()
            if cashier_user and shampoo_product:
                print("--- Criando uma venda de exemplo... ---")
                
                new_sell = Sell(
                    id=str(uuid.uuid4()),
                    id_caixa=cashier_user.profile.get("register_number", "CX001"),
                    operator=cashier_user.profile.get("name", "Caixa Padrão"),
                    sell_time=datetime.utcnow(),
                    total_value=shampoo_product.sale_value,
                    payment_method="dinheiro",
                    received_value=15.00,
                    change=15.00 - shampoo_product.sale_value
                )
                db.session.add(new_sell)

                item_vendido = ItemSold(
                    sell_id=new_sell.id,
                    product_id=shampoo_product.id,
                    product_name=f"{shampoo_product.item} {shampoo_product.brand}",
                    quantity=1,
                    unit_value=shampoo_product.sale_value,
                    total_value=shampoo_product.sale_value
                )
                db.session.add(item_vendido)

                print(f"--- Debitando 1 unidade de '{shampoo_product.item}' do estoque '{geral_stock.name}'... ---")
                update_stock_stmt = db.update(stock_item).where(
                    stock_item.c.stock_id == geral_stock.id,
                    stock_item.c.product_id == shampoo_product.id
                ).values(quantity=stock_item.c.quantity - 1)
                db.session.execute(update_stock_stmt)
                
                print("--- Venda de exemplo criada com sucesso! ---")
        else:
            print("--- Tabela de Vendas já contém dados, pulando. ---")

        try:
            db.session.commit()
            print("\n--- SEEDING CONCLUÍDO COM SUCESSO! ---")
        except Exception as e:
            db.session.rollback()
            print(f"\n--- ERRO AO FAZER COMMIT NO BANCO DE DADOS: {e} ---")

if __name__ == "__main__":
    seed_database()