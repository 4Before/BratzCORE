"""
Módulo de Autenticação e Autorização
------------------------------------
Este arquivo contém os decoradores Python utilizados para proteger os endpoints da API.
Ele fornece mecanismos para verificar a presença e validade de tokens JWT, bem como
para checar se o usuário autenticado possui os privilégios necessários para
acessar uma determinada rota.

A ordem de aplicação dos decoradores em uma rota é importante:
1. Decorador da rota (ex: @app.route)
2. Decoradores de autorização (ex: @privilege_required, @admin_required)
3. Decorador de autenticação (@token_required) - Este deve ser o último (mais interno).
"""

from functools import wraps
from flask import request, g
from typing import Callable
from models.user import User
from utils.jwt_manager import decode_token
from utils.responses import error_response


def token_required(f: Callable) -> Callable:
    """
    Decorador de Autenticação.

    Verifica se o cabeçalho 'Authorization' contém um Bearer Token JWT válido.
    Se o token for válido, decodifica, busca o usuário correspondente no banco de dados
    e o anexa ao objeto global `g` da requisição como `g.current_user`.

    Este decorador é o alicerce para os outros de autorização.

    Retorna:
        - 401 Unauthorized: Se o token estiver ausente, mal formatado, inválido,
          expirado, ou se o usuário não for encontrado.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return error_response("Cabeçalho de autorização ausente.", 401)

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return error_response("Formato do cabeçalho de autorização inválido. Use 'Bearer <token>'.", 401)

        token = parts[1]
        payload = decode_token(token)
        if not payload:
            return error_response("Token inválido ou expirado.", 401)

        # Busca o usuário no banco de dados com base no ID contido no token
        user = User.query.get(payload.get("user_id"))
        if not user:
            return error_response("Usuário associado ao token não existe mais.", 401)

        # Anexa o objeto do usuário à requisição atual para uso posterior
        g.current_user = user
        return f(*args, **kwargs)
    return decorated


def admin_required(f: Callable) -> Callable:
    """
    Decorador de Autorização - Nível Administrador.

    Verifica se o usuário atual (previamente autenticado por `token_required`)
    possui o privilégio "ADMIN" ou o super privilégio "ALL".

    IMPORTANTE: Este decorador deve ser aplicado ANTES do `token_required`.
    Exemplo de uso:
    @minha_rota.route('/admin')
    @admin_required
    @token_required
    def rota_de_admin():
        ...
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Confia que `token_required` já foi executado e `g.current_user` existe
        user = getattr(g, "current_user", None)
        if not user:
            # Fallback caso token_required não tenha sido usado
            return error_response("Autenticação necessária.", 401)

        if not isinstance(user.privileges, dict):
             return error_response("Formato de privilégios inválido para o usuário.", 403)
             
        has_admin_privilege = user.privileges.get("ADMIN", False)
        has_all_privilege = user.privileges.get("ALL", False)
        
        if not (has_admin_privilege or has_all_privilege):
            return error_response("Acesso negado. Privilégios de administrador necessários.", 403)

        return f(*args, **kwargs)
    return decorated


def privilege_required(privilege_key: str) -> Callable:
    """
    Decorador de Autorização - Parametrizado por Privilégio.

    Cria um decorador que verifica se o usuário atual possui um privilégio específico.
    O acesso também é concedido se o usuário tiver o super privilégio "ALL".

    IMPORTANTE: Assim como `admin_required`, deve ser aplicado ANTES de `token_required`.

    Args:
        privilege_key (str): A chave do privilégio a ser verificada (ex: "CLIENT_CREATOR").
    
    Exemplo de uso:
    @minha_rota.route('/clients')
    @privilege_required("CLIENT_CREATOR")
    @token_required
    def criar_cliente():
        ...
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = getattr(g, "current_user", None)
            if not user:
                return error_response("Autenticação necessária.", 401)
            
            if not isinstance(user.privileges, dict):
                return error_response("Formato de privilégios inválido para o usuário.", 403)

            has_specific_privilege = user.privileges.get(privilege_key, False)
            has_all_privilege = user.privileges.get("ALL", False)

            if not (has_specific_privilege or has_all_privilege):
                return error_response(f"Acesso negado. Requer privilégio: '{privilege_key}'", 403)

            return f(*args, **kwargs)
        return decorated_function
    return decorator


# Define quais funções são exportadas quando se faz 'from utils.auth import *'
__all__ = ["token_required", "admin_required", "privilege_required"]