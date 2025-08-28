from flask import jsonify
from werkzeug.exceptions import HTTPException

class APIError(Exception):
    """Classe base para exceções customizadas da API."""
    status_code = 500
    message = "An unexpected error occurred."
    
    def __init__(self, message=None, status_code=None, errors=None):
        if message:
            self.message = message
        if status_code:
            self.status_code = status_code
        self.errors = errors
        super().__init__(self.message)

class InvalidInputError(APIError):
    """Erro de validação de entrada (código 400)."""
    status_code = 400
    def __init__(self, message="Validation failed.", errors=None):
        super().__init__(message, status_code=400, errors=errors)

class ResourceNotFoundError(APIError):
    """Erro para recursos não encontrados (código 404)."""
    status_code = 404
    message = "Resource not found."
    
class ConflictError(APIError):
    """Erro para conflitos, como a tentativa de criar um recurso que já existe (código 409)."""
    status_code = 409
    message = "Conflict with existing resource."

class ForbiddenError(APIError):
    """Erro para quando um usuário não tem as permissões necessárias (código 403)."""
    status_code = 403
    message = "Forbidden. You do not have permission to perform this action."

class UnauthorizedError(APIError):
    """Erro para falhas de autenticação (código 401)."""
    status_code = 401
    message = "Authentication required."


def register_error_handlers(app):
    """
    Registra os manipuladores de erro centralizados no aplicativo Flask.
    """
    @app.errorhandler(APIError)
    def handle_api_error(error):
        """Captura todas as exceções personalizadas da nossa API."""
        response = {
            "status": "error",
            "message": error.message
        }
        # Se for um erro de validação, inclua os detalhes
        if isinstance(error, InvalidInputError) and error.errors:
            response["errors"] = error.errors
            
        return jsonify(response), error.status_code
        
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """Captura exceções padrão do Werkzeug (Flask), como 404 e 500."""
        return jsonify({
            "status": "error",
            "message": str(error)
        }), error.code