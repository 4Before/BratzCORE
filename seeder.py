from app import create_app, db
from models.user import User
from models.product import Product

app = create_app()

with app.app_context():
    print("--- Verificando e criando tabelas do banco de dados... ---")
    db.create_all()
    print("--- Tabelas criadas com sucesso! ---")
    owner_email = "owner@market.com"
    owner_user = User.query.filter_by(email=owner_email).first()

    if not owner_user:
        print(f"--- Usuário OWNER '{owner_email}' não encontrado, criando... ---")
        
        u = User(
            email=owner_email, 
            account_type="OWNER", 
            privileges={"ADMIN": True, "ALL": True}
        )

        u.set_password("StrongPass123!")

        db.session.add(u)
        db.session.commit()
        
        print(f"--- OWNER criado com sucesso: {owner_email} / StrongPass123! ---")
    else:
        print(f"--- Usuário OWNER '{owner_email}' já existe, pulando seeding. ---")
    print("--- Inicialização do banco de dados concluída. ---")