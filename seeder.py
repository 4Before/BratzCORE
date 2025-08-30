import uuid
from datetime import datetime
from app import create_app, db
from models.user import User
from models.product import Product
from models.client import Client
from models.finances import Sell, ItemSold

app = create_app()

def seed_database():
    """
    Função principal para popular o banco de dados com dados iniciais.
    Verifica a existência de dados antes de inseri-los para evitar duplicatas.
    """
    with app.app_context():
        print("--- INICIANDO PROCESSO DE SEEDING DO BANCO DE DADOS ---")
        
        # Garante que todas as tabelas estão criadas
        print("--- Verificando e criando tabelas do banco de dados... ---")
        db.create_all()
        print("--- Verificação de tabelas concluída. ---")

        # --- SEEDING DE USUÁRIOS ---
        
        # Usuário OWNER (Admin Principal)
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

        # Usuário CAIXA
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

        # --- SEEDING DE PRODUTOS ---
        
        # Produtos Iniciais
        shampoo_product = Product.query.filter_by(item="Shampoo", brand="Bratz").first()
        if not shampoo_product:
            print("--- Criando produto 'Shampoo Bratz'... ---")
            shampoo_product = Product(
                item="Shampoo",
                brand="Bratz",
                purchase_value=5.50,
                sale_value=12.99,
                quantity_in_stock=100
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
                quantity_in_stock=80
            )
            db.session.add(condicionador_product)
        else:
            print("--- Produto 'Condicionador Bratz' já existe, pulando. ---")

        # --- SEEDING DE CLIENTES ---
        
        # Cliente Inicial
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

        # Venda Inicial (só cria se não houver nenhuma venda no sistema)
        if not Sell.query.first():
            # Garante que temos os objetos necessários para criar a venda
            if cashier_user and shampoo_product:
                print("--- Criando uma venda de exemplo... ---")
                
                # Cria o registro principal da venda
                new_sell = Sell(
                    id=str(uuid.uuid4()),  # ID único para a venda
                    id_caixa=cashier_user.profile.get("register_number", "CX001"),
                    operator=cashier_user.profile.get("name", "Caixa Padrão"),
                    sell_time=datetime.utcnow(),
                    total_value=shampoo_product.sale_value,
                    payment_method="dinheiro",
                    received_value=15.00,
                    change=15.00 - shampoo_product.sale_value
                )
                db.session.add(new_sell)

                # Cria o item vendido associado a essa venda
                item_vendido = ItemSold(
                    sell_id=new_sell.id,
                    product_id=shampoo_product.id,
                    product_name=f"{shampoo_product.item} {shampoo_product.brand}",
                    quantity=1,
                    unit_value=shampoo_product.sale_value,
                    total_value=shampoo_product.sale_value
                )
                db.session.add(item_vendido)

                # Atualiza o estoque do produto
                shampoo_product.quantity_in_stock -= 1
                print("--- Venda de exemplo criada com sucesso! ---")
            else:
                print("--- ERRO: Usuário Caixa ou Produto Shampoo não encontrado para criar a venda. ---")
        else:
            print("--- Tabela de Vendas já contém dados, pulando. ---")

        # Efetua o commit de todas as transações de uma vez
        try:
            db.session.commit()
            print("\n--- SEEDING CONCLUÍDO COM SUCESSO! ---")
        except Exception as e:
            print(f"\n--- ERRO AO FAZER COMMIT NO BANCO DE DADOS: {e} ---")
            db.session.rollback()

if __name__ == "__main__":
    seed_database()