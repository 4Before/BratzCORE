"""
Módulo Utilitário para Contas de Usuário
---------------------------------------
Este arquivo centraliza as constantes, regras de negócio e funções de validação
relacionadas aos diferentes tipos de contas e seus perfis específicos.
"""

from models.user import User

# --- Constantes de Tipos de Conta ---
ACCOUNT_OWNER = "OWNER"
ACCOUNT_FULL = "FULL_MANAGEMENT"
ACCOUNT_CAIXA = "CAIXA"
ACCOUNT_STORAGE = "STORAGE"
ACCOUNT_SUPERVISOR = "SUPERVISOR"
ACCOUNT_CUSTOM = "CUSTOM"

SUPPORTED_ACCOUNT_TYPES = {
    ACCOUNT_OWNER, 
    ACCOUNT_FULL, 
    ACCOUNT_CAIXA,
    ACCOUNT_STORAGE, 
    ACCOUNT_SUPERVISOR, 
    ACCOUNT_CUSTOM
}

# --- Conjunto de Chaves de Privilégio Válidas ---
# Usado para validar contas do tipo CUSTOM.
ALLOWED_PRIVILEGE_KEYS = {
    "ALL", "ADMIN", "STAT_VIEWER", "ACCOUNT_CREATOR", "MICRO_ACCOUNT_CREATOR",
    "CLIENT_CREATOR", "NF", "FINANCE", "STOCK_MODIFIER", "STORAGE_MODIFIER",
    "UNDO", "REDO", "DOWN_STORAGE", "BINDING", "PANEL_MODIFIER"
}

# --- Dicionário de Privilégios Padrão ---
# Define as permissões padrão para cada tipo de conta pré-definido.
DEFAULT_PRIVILEGES = {
    ACCOUNT_OWNER: {"ALL": True},
    ACCOUNT_FULL: {
        "ADMIN": True, "STAT_VIEWER": False, "ACCOUNT_CREATOR": False,
        "MICRO_ACCOUNT_CREATOR": True, "CLIENT_CREATOR": True, "NF": True,
        "FINANCE": False, "STOCK_MODIFIER": True, "STORAGE_MODIFIER": True,
        "UNDO": True, "REDO": True, "DOWN_STORAGE": False,
        "BINDING": False, "PANEL_MODIFIER": False,
    },
    ACCOUNT_CAIXA: {
        "ADMIN": False, "STAT_VIEWER": False, "ACCOUNT_CREATOR": False,
        "MICRO_ACCOUNT_CREATOR": False, "CLIENT_CREATOR": True, "NF": True,
        "FINANCE": False, "STOCK_MODIFIER": False, "STORAGE_MODIFIER": False,
        "UNDO": False, "REDO": False, "DOWN_STORAGE": True,
        "BINDING": True, "PANEL_MODIFIER": False,
    },
    ACCOUNT_STORAGE: {
        "ADMIN": False, "STAT_VIEWER": False, "ACCOUNT_CREATOR": False,
        "MICRO_ACCOUNT_CREATOR": False, "CLIENT_CREATOR": False, "NF": False,
        "FINANCE": False, "STOCK_MODIFIER": False, "STORAGE_MODIFIER": True,
        "UNDO": True, "REDO": True, "DOWN_STORAGE": True,
        "BINDING": True, "PANEL_MODIFIER": False,
    },
    ACCOUNT_SUPERVISOR: {
        "ADMIN": False, "STAT_VIEWER": False, "ACCOUNT_CREATOR": False,
        "MICRO_ACCOUNT_CREATOR": True, "CLIENT_CREATOR": True, "NF": False,
        "FINANCE": False, "STOCK_MODIFIER": False, "STORAGE_MODIFIER": False,
        "UNDO": True, "REDO": True, "DOWN_STORAGE": False,
        "BINDING": False, "PANEL_MODIFIER": False,
    },
}

# --- Funções de Validação de Perfis ---

def validate_profile_for_caixa(profile: dict | None) -> tuple[dict, list[str]]:
    """Valida e normaliza o perfil para contas do tipo CAIXA."""
    errors: list[str] = []
    if not isinstance(profile, dict):
        return {}, ["O campo 'profile' deve ser um objeto para contas CAIXA"]

    register_number = profile.get("register_number")
    operator_name = profile.get("operator_name")
    fast_lane = profile.get("fast_lane", False)
    preferential = profile.get("preferential", False)

    if not isinstance(register_number, int):
        errors.append("profile.register_number deve ser um número inteiro.")
    if not isinstance(operator_name, str) or not operator_name.strip():
        errors.append("profile.operator_name deve ser um texto não vazio.")
    if not isinstance(fast_lane, bool):
        errors.append("profile.fast_lane deve ser um booleano (true/false).")
    if not isinstance(preferential, bool):
        errors.append("profile.preferential deve ser um booleano (true/false).")

    if isinstance(register_number, int):
        existing_user = User.query.filter(User.profile['register_number'].astext == str(register_number)).first()
        if existing_user:
            errors.append(f"O número de registro '{register_number}' já está em uso.")

    if errors:
        return {}, errors

    normalized = {
        "register_number": register_number,
        "operator_name": (operator_name or "").strip(),
        "fast_lane": fast_lane,
        "preferential": preferential,
    }
    return normalized, []


def validate_profile_for_storage(profile: dict | None) -> tuple[dict, list[str]]:
    """Valida e normaliza o perfil para contas do tipo STORAGE."""
    errors: list[str] = []
    if not isinstance(profile, dict):
        return {}, ["O campo 'profile' deve ser um objeto para contas STORAGE"]

    operator_name = profile.get("operator_name")
    sector_id = profile.get("sector_id")
    restrict_to_sector = profile.get("restrict_to_sector")

    if not isinstance(operator_name, str) or not operator_name.strip():
        errors.append("profile.operator_name deve ser um texto não vazio.")
    if sector_id is not None and not isinstance(sector_id, (int, str)):
        errors.append("profile.sector_id deve ser um inteiro ou texto.")
    if restrict_to_sector is None:
        restrict_to_sector = sector_id is not None
    elif not isinstance(restrict_to_sector, bool):
        errors.append("profile.restrict_to_sector deve ser um booleano.")

    if errors:
        return {}, errors

    normalized = {
        "operator_name": (operator_name or "").strip(),
        "sector_id": sector_id,
        "restrict_to_sector": restrict_to_sector,
    }
    return normalized, []


def validate_profile_for_supervisor(profile: dict | None) -> tuple[dict, list[str]]:
    """Valida e normaliza o perfil para contas do tipo SUPERVISOR."""
    errors: list[str] = []
    if not isinstance(profile, dict):
        return {}, ["O campo 'profile' deve ser um objeto para contas SUPERVISOR"]

    operator_name = profile.get("operator_name")
    cash_range = profile.get("cash_register_range")
    restrict_to_range = profile.get("restrict_to_range")

    if not isinstance(operator_name, str) or not operator_name.strip():
        errors.append("profile.operator_name deve ser um texto não vazio.")

    if cash_range is not None:
        if not isinstance(cash_range, dict):
            errors.append("profile.cash_register_range deve ser um objeto com 'start' e 'end'.")
        else:
            start = cash_range.get("start")
            end = cash_range.get("end")
            if not isinstance(start, int) or not isinstance(end, int):
                errors.append("profile.cash_register_range.start e .end devem ser inteiros.")
            elif start > end:
                errors.append("profile.cash_register_range.start não pode ser maior que .end.")

    if restrict_to_range is None:
        restrict_to_range = cash_range is not None
    elif not isinstance(restrict_to_range, bool):
        errors.append("profile.restrict_to_range deve ser um booleano.")

    if errors:
        return {}, errors

    normalized = {
        "operator_name": (operator_name or "").strip(),
        "cash_register_range": cash_range,
        "restrict_to_range": restrict_to_range,
    }
    return normalized, []

def validate_and_build_privileges(payload_privs: dict | None) -> tuple[dict, list[str]]:
    """Valida o dicionário de privilégios para contas do tipo CUSTOM."""
    errors: list[str] = []
    if not isinstance(payload_privs, dict):
        return {}, ["O campo 'privileges' deve ser um objeto (dicionário)."]

    result = {key: False for key in ALLOWED_PRIVILEGE_KEYS}
    
    for key, value in payload_privs.items():
        key_up = str(key).strip().upper()
        if key_up not in ALLOWED_PRIVILEGE_KEYS:
            errors.append(f"Chave de privilégio desconhecida: '{key}'.")
            continue
        if not isinstance(value, bool):
            errors.append(f"O valor para o privilégio '{key}' deve ser um booleano (true/false).")
            continue
        result[key_up] = value
        
    # Lógica especial para 'ALL' e 'ADMIN'
    if result.get("ALL"):
        result = {key: True for key in ALLOWED_PRIVILEGE_KEYS}
    elif result.get("ADMIN"):
        for key in result:
            result[key] = True # Exemplo: admin ativa tudo, personalize se necessário

    return result, errors