"""
Módulo Gerenciador de JSON Web Tokens (JWT)
-------------------------------------------
Este utilitário abstrai a complexidade da criação e decodificação de JWTs,
fornecendo duas funções simples e seguras para serem usadas em toda a aplicação.

Ele é responsável por:
- Gerar tokens para usuários autenticados, incluindo as 'claims' (informações)
  necessárias e uma data de expiração.
- Decodificar e validar tokens recebidos, tratando de forma segura os erros
  comuns como tokens expirados ou com assinatura inválida.
"""

import jwt
from flask import current_app
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from models.user import User


def generate_token(user: User) -> str:
    """
    Gera um novo token JWT para um usuário específico.

    O payload do token é construído com informações essenciais para identificar
    o usuário em requisições futuras e com uma data de expiração para segurança.

    Args:
        user (User): O objeto do modelo SQLAlchemy do usuário para o qual o
                     token será gerado.

    Returns:
        str: O token JWT codificado como uma string.
    """
    payload = {
        "user_id": user.id,
        "email": user.email,
        # 'exp' (Expiration Time) é uma claim padrão do JWT.
        # Define o tempo de vida do token para aumentar a segurança.
        "exp": datetime.utcnow() + timedelta(days=1)  # TODO: Tornar o tempo de expiração configurável
    }
    
    secret_key = current_app.config["JWT_SECRET_KEY"]
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    
    return token


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decodifica um token JWT e retorna seu payload.

    Esta função atua como um wrapper seguro para `jwt.decode`, tratando os erros
    mais comuns de invalidação de token.

    Args:
        token (str): A string do token JWT a ser decodificado.

    Returns:
        Optional[Dict[str, Any]]: Um dicionário contendo o payload do token se
                                  a validação for bem-sucedida, ou None se o
                                  token estiver expirado ou for inválido.
    """
    try:
        secret_key = current_app.config["JWT_SECRET_KEY"]
        # A validação da assinatura e da expiração é feita automaticamente pela biblioteca
        return jwt.decode(token, secret_key, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        # O token é válido, mas já expirou.
        return None
    except jwt.InvalidTokenError:
        # O token é mal formado, a assinatura não bate, etc.
        return None


# Define o que é "público" neste módulo
__all__ = ["generate_token", "decode_token"]