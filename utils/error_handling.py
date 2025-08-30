"""
Módulo de Manipulação Centralizada de Erros
-------------------------------------------
Este arquivo define um sistema robusto para tratamento de exceções na API.
Ele provê uma classe base `APIError` e diversas subclasses para erros semânticos
comuns (ex: Recurso Não Encontrado, Acesso Proibido).

A função `register_error_handlers` conecta essas exceções customizadas e as exceções
padrão do Flask/Werkzeug ao aplicativo, garantindo que qualquer erro gerado pela
aplicação resulte em uma resposta JSON padronizada e informativa.
"""

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException
from typing import Dict, List, Optional

# ==================================
# ==== CLASSES DE EXCEÇÃO API ====
# ==================================

class APIError(Exception):
    """
    Classe base para todas as exceções customizadas da API.
    Permite a definição de uma mensagem padrão, um status code HTTP e um
    dicionário opcional para detalhar erros de validação.
    """
    status_code: int = 500
    message: str = "Ocorreu um erro inesperado no servidor."
    
    def __init__(
        self, 
        message: Optional[str] = None, 
        status_code: Optional[int] = None, 
        errors: Optional[Dict | List] = None
    ):
        super().__init__(message)
        if message is not None:
            self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.errors = errors

class InvalidInputError(APIError):
    """
    Exceção para erros de validação de entrada (400 Bad Request).
    Deve ser levantada quando os dados enviados pelo cliente falham na validação
    (ex: campos ausentes, formatos incorretos).
    """
    status_code = 400
    def __init__(self, message: str = "A validação dos dados falhou.", errors: Optional[Dict | List] = None):
        super().__init__(message, status_code=400, errors=errors)

class ResourceNotFoundError(APIError):
    """
    Exceção para recursos não encontrados (404 Not Found).
    Deve ser levantada quando uma busca por um recurso específico (ex: um cliente por ID)
    não retorna resultados. O `get_or_404()` do Flask-SQLAlchemy levanta uma
    HTTPException, que é capturada por outro handler.
    """
    status_code = 404
    message = "O recurso solicitado não foi encontrado."
    
class ConflictError(APIError):
    """
    Exceção para conflitos de recursos (409 Conflict).
    Deve ser levantada ao tentar criar um recurso que viola uma restrição
    de unicidade (ex: cadastrar um e-mail ou CPF que já existe).
    """
    status_code = 409
    message = "Conflito com um recurso existente."

class ForbiddenError(APIError):
    """
    Exceção para acesso não autorizado (403 Forbidden).
    Deve ser levantada quando um usuário autenticado tenta realizar uma ação
    para a qual ele não possui o privilégio necessário.
    """
    status_code = 403
    message = "Acesso proibido. Você não tem permissão para realizar esta ação."

class UnauthorizedError(APIError):
    """
    Exceção para falhas de autenticação (401 Unauthorized).
    Deve ser levantada quando uma requisição exige autenticação, mas o token
    é ausente, inválido ou expirado.
    """
    status_code = 401
    message = "Autenticação necessária."


# ==================================
# ==== REGISTRO DOS HANDLERS ====
# ==================================

def register_error_handlers(app: Flask) -> None:
    """
    Registra os manipuladores de erro centralizados no aplicativo Flask.

    Esta função deve ser chamada dentro da factory `create_app` em `app.py`
    para que os handlers sejam ativados para toda a aplicação.

    Args:
        app (Flask): A instância do aplicativo Flask.
    """

    @app.errorhandler(APIError)
    def handle_api_error(error: APIError):
        """
        Captura e formata qualquer exceção que herde de `APIError`.
        Isso garante que todos os nossos erros customizados tenham a mesma
        estrutura de resposta JSON.
        """
        response = {
            "status": "error",
            "message": error.message
        }
        # Se for um erro de validação com detalhes, anexa os detalhes.
        if isinstance(error, InvalidInputError) and error.errors:
            response["errors"] = error.errors
            
        return jsonify(response), error.status_code
        
    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        """
        Captura exceções HTTP padrão do Werkzeug/Flask (ex: 404, 500, 405).
        Isso garante que mesmo erros não previstos pela nossa lógica customizada
        ainda retornem um JSON padronizado, em vez de uma página HTML de erro.
        """
        return jsonify({
            "status": "error",
            "message": error.description or str(error) # .description geralmente tem a melhor mensagem
        }), error.code

# Define o que é "público" neste módulo
__all__ = [
    "APIError", "InvalidInputError", "ResourceNotFoundError", "ConflictError",
    "ForbiddenError", "UnauthorizedError", "register_error_handlers"
]