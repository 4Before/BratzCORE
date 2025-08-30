"""
Ponto de Entrada Principal da Aplicação (Application Factory)
--------------------------------------------------------------
Este módulo é o coração da API Bratz. Ele contém a "Application Factory",
um padrão de design do Flask que permite a criação de múltiplas instâncias
da aplicação com diferentes configurações, o que é essencial para testes e
escalabilidade.

A função `create_app` é responsável por:
1. Instanciar o objeto principal do Flask.
2. Carregar as configurações a partir do `config.py`.
3. Inicializar as extensões (como SQLAlchemy e Migrate).
4. Registrar todos os Blueprints (módulos de rotas) da aplicação.
5. Anexar os manipuladores de erro centralizados.
"""

from flask import Flask
from config import Config
from utils.extensions import db, migrate
from utils.error_handling import register_error_handlers
from routes import (
    accounts_bp, products_bp, clients_bp, 
    finances_bp, auth_bp, stocks_bp, suppliers_bp
)

# Uma lista centralizada de todos os blueprints da aplicação.
# Facilita o registro em massa e a organização.
ALL_BLUEPRINTS = [
    accounts_bp,
    products_bp,
    clients_bp,
    finances_bp,
    auth_bp,
    stocks_bp,
    suppliers_bp
]

def create_app() -> Flask:
    """
    Cria e configura uma instância da aplicação Flask.

    Esta função segue o padrão Application Factory, o que permite criar
    a aplicação dinamicamente, facilitando testes e diferentes configurações
    de implantação.

    Returns:
        Flask: A instância da aplicação Flask configurada e pronta para rodar.
    """
    # Cria a instância principal da aplicação
    app = Flask(__name__)
    
    # Carrega as configurações a partir da classe Config definida em config.py
    app.config.from_object(Config)

    # Inicializa as extensões, vinculando-as à instância da aplicação
    db.init_app(app)
    migrate.init_app(app, db)

    # Registra todos os blueprints definidos na lista ALL_BLUEPRINTS
    # O url_prefix garante que todas as rotas destes módulos comecem com /bratz
    for blueprint in ALL_BLUEPRINTS:
        app.register_blueprint(blueprint, url_prefix="/bratz")

    # Anexa os manipuladores de erro customizados à aplicação
    register_error_handlers(app)

    return app

# Este bloco só é executado quando o script é chamado diretamente (ex: `python app.py`)
# Não é executado quando a aplicação é servida por um servidor de produção como Gunicorn.
if __name__ == "__main__":
    app = create_app()
    # Inicia o servidor de desenvolvimento do Flask com o modo de depuração ativado
    app.run(debug=True)