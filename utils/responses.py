"""
Módulo de Respostas Padronizadas da API
---------------------------------------
Este utilitário fornece funções helper para gerar respostas JSON consistentes
em toda a aplicação. Ao utilizar estas funções, garantimos que todos os
clientes da API (como o BratzCAIXA e o futuro BratzADM) receberão respostas
de sucesso e de erro em um formato previsível e fácil de manipular.

A estrutura padrão é:
- Sucesso: {"status": "success", "message": "...", "data": {...}}
- Erro:    {"status": "error", "message": "..."}
"""

from flask import jsonify
from werkzeug.wrappers import Response
from typing import Dict, Any, Optional, Tuple, List

def success_response(
    message: str, 
    data: Optional[Dict[str, Any] | List[Any]] = None, 
    status_code: int = 200
) -> Tuple[Response, int]:
    """
    Gera uma resposta JSON padronizada para operações bem-sucedidas.

    Args:
        message (str): Uma mensagem clara e concisa descrevendo o sucesso da operação.
        data (Optional[Dict | List]): Um dicionário ou lista contendo os dados a 
                                      serem retornados no corpo da resposta. 
                                      Padrão é None.
        status_code (int): O código de status HTTP para a resposta. 
                           Padrão é 200 (OK).

    Returns:
        Tuple[Response, int]: Uma tupla contendo o objeto de resposta Flask 
                              e o código de status, pronta para ser retornada 
                              de um endpoint.
    """
    response_payload = {
        "status": "success",
        "message": message,
    }
    if data is not None:
        response_payload["data"] = data
        
    return jsonify(response_payload), status_code


def error_response(
    message: str, 
    status_code: int = 400
) -> Tuple[Response, int]:
    """
    Gera uma resposta JSON padronizada para erros.

    Args:
        message (str): Uma mensagem clara descrevendo o erro ocorrido.
        status_code (int): O código de status HTTP apropriado para o erro.
                           Padrão é 400 (Bad Request).

    Returns:
        Tuple[Response, int]: Uma tupla contendo o objeto de resposta Flask 
                              e o código de status.
    """
    return jsonify({
        "status": "error",
        "message": message
    }), status_code

# Define o que é "público" neste módulo
__all__ = ["success_response", "error_response"]