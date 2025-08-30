"""
Módulo de Configuração da Aplicação Flask
-----------------------------------------
Este arquivo centraliza a configuração da aplicação. Ele utiliza a biblioteca
python-dotenv para carregar variáveis de ambiente de um arquivo .env,
permitindo uma separação segura entre o código e os segredos da aplicação
(como chaves de API e strings de conexão de banco de dados).

A classe `Config` agrupa todas as variáveis de configuração que serão
carregadas pelo Flask na inicialização da aplicação.
"""

import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env localizado na raiz do projeto.
# Isso torna as variáveis definidas no .env acessíveis através de os.getenv().
load_dotenv()

class Config:
    """
    Classe de configuração que contém todas as variáveis utilizadas pelo Flask e suas extensões.
    """
    
    # Chave secreta usada pelo Flask para assinar dados, como cookies de sessão.
    # É crucial para a segurança contra ataques de CSRF.
    # O valor é lido do ambiente, com um fallback para um valor simples de desenvolvimento.
    # NUNCA use o valor padrão em produção.
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-should-be-more-secure")

    # Chave secreta usada especificamente pela biblioteca PyJWT para assinar os tokens de acesso.
    # É uma boa prática que esta chave seja diferente da SECRET_KEY principal do Flask.
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-key-is-different")

    # Desativa o sistema de eventos do SQLAlchemy, que não é necessário para a aplicação
    # e consome recursos. É a configuração recomendada.
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Configuração da String de Conexão com o Banco de Dados ---

    # 1. Lê a URL do banco de dados a partir do arquivo .env.
    #    Esta é a forma segura de armazenar credenciais de banco de dados.
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")

    # 2. Lógica de robustez para garantir a compatibilidade com o SQLAlchemy e o driver psycopg (v3).
    #    As strings de conexão do Neon vêm como "postgresql://...", que é a forma correta.
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgres"):
        
        # O SQLAlchemy pode usar o alias 'postgres://', mas 'postgresql://' é o nome oficial do dialeto.
        # Esta linha normaliza a URI caso ela venha no formato mais curto.
        if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
            SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)
        
        # O SQLAlchemy, por padrão, tenta usar o driver 'psycopg2'. Como estamos usando a versão 3 ('psycopg'),
        # precisamos especificar isso explicitamente no dialeto da conexão.
        # Esta linha adiciona o driver '+psycopg' se ele ainda não estiver presente na URI.
        if "postgresql+psycopg://" not in SQLALCHEMY_DATABASE_URI:
            SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgresql://", "postgresql+psycopg://", 1)