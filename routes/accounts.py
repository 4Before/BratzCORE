from flask import Blueprint, request
from models.user import User, db
from utils.responses import success_response, error_response
import utils.auth as auth_utils

accounts_bp = Blueprint("accounts", __name__)

# --- Account type constants ---
ACCOUNT_OWNER = "OWNER"
ACCOUNT_FULL = "FULL_MANAGEMENT"
ACCOUNT_CAIXA = "CAIXA"
ACCOUNT_STORAGE = "STORAGE"
ACCOUNT_SUPERVISOR = "SUPERVISOR"
ACCOUNT_CUSTOM = "CUSTOM"
# to do: support modifying an existing account type and be able to give it an name. Custom should be able to give an name too

SUPPORTED_ACCOUNT_TYPES = {ACCOUNT_OWNER, ACCOUNT_FULL, ACCOUNT_CAIXA, ACCOUNT_STORAGE, ACCOUNT_SUPERVISOR, ACCOUNT_CUSTOM}

# --- Allowed privilege keys ---
ALLOWED_PRIVILEGE_KEYS = {
    "ALL", # all true
    "ADMIN", # high previleges
    "STAT_VIEWER", # view statistics
    "ACCOUNT_CREATOR", # creates accounts
    "MICRO_ACCOUNT_CREATOR" # creates accounts low level accounts
    "CLIENT_CREATOR", # creates clients
    "NF", # crate nf
    "FINANCE", # can export things to csv, excel, view monetary info
    "STOCK_MODIFIER", # can create the stocks
    "STORAGE_MODIFIER", # can modify the items in stocks
    "UNDO", # for caixa - undo the last action
    "REDO", # for caixa - redo the last action
    "DOWN_STORAGE", # for caixa - downs one item after the buy
    "BINDING", # for caixa - can change the key bindings of the system
    "PANEL_MODIFIER" # for admin panel - can change the view or bindings for the admin panel
},

# --- Default privileges for fixed account types ---
DEFAULT_PRIVILEGES = {
    ACCOUNT_OWNER: {"ALL": True},
    ACCOUNT_FULL: {
        "ADMIN": True,
        "STAT_VIEWER": False,
        "ACCOUNT_CREATOR": False,
        "MICRO_ACCOUNT_CREATOR": True,
        "CLIENT_CREATOR": True,
        "NF": True,
        "FINANCE": False,
        "STOCK_MODIFIER": True,
        "STORAGE_MODIFIER": True,
        "UNDO": True,
        "REDO": True,
        "DOWN_STORAGE": False,
        "BINDING": False,
        "PANEL_MODIFIER": False,
    },
    ACCOUNT_CAIXA: {
        "ADMIN": False,
        "STAT_VIEWER": False,
        "ACCOUNT_CREATOR": False,
        "MICRO_ACCOUNT_CREATOR": False,
        "CLIENT_CREATOR": True,
        "NF": True,
        "FINANCE": False,
        "STOCK_MODIFIER": False,
        "STORAGE_MODIFIER": False,
        "UNDO": False,
        "REDO": False,
        "DOWN_STORAGE": True,
        "BINDING": True,
        "PANEL_MODIFIER": False,
    },
    ACCOUNT_STORAGE: {
        "ADMIN": False,
        "STAT_VIEWER": False,
        "ACCOUNT_CREATOR": False,
        "MICRO_ACCOUNT_CREATOR": False,
        "CLIENT_CREATOR": False,
        "NF": False,
        "FINANCE": False,
        "STOCK_MODIFIER": False,
        "STORAGE_MODIFIER": True,
        "UNDO": True,
        "REDO": True,
        "DOWN_STORAGE": True,
        "BINDING": True,
        "PANEL_MODIFIER": False,
    },
    ACCOUNT_SUPERVISOR: {
        "ADMIN": False,
        "STAT_VIEWER": False,
        "ACCOUNT_CREATOR": False,
        "MICRO_ACCOUNT_CREATOR": True,
        "CLIENT_CREATOR": True,
        "NF": False,
        "FINANCE": False,
        "STOCK_MODIFIER": False,
        "STORAGE_MODIFIER": False,
        "UNDO": True,
        "REDO": True,
        "DOWN_STORAGE": False,
        "BINDING": False,
        "PANEL_MODIFIER": False,
    },
}

def _validate_profile_for_caixa(profile: dict | None) -> tuple[dict, list[str]]:
    """
    CAIXA required profile:
      - register_number: int
      - operator_name: str
      - fast_lane: bool
      - preferential: bool
    Also enforces unique register_number among CAIXA accounts (in-Python check).
    """
    errors: list[str] = []
    if not isinstance(profile, dict):
        return {}, ["Field 'profile' must be an object for CAIXA"]

    register_number = profile.get("register_number")
    operator_name = profile.get("operator_name")
    fast_lane = profile.get("fast_lane")
    preferential = profile.get("preferential")

    # type checks
    if not isinstance(register_number, int):
        errors.append("profile.register_number must be an integer")
    if not isinstance(operator_name, str) or not operator_name.strip():
        errors.append("profile.operator_name must be a non-empty string")
    if not isinstance(fast_lane, bool):
        errors.append("profile.fast_lane must be boolean")
    if not isinstance(preferential, bool):
        errors.append("profile.preferential must be boolean")

    if isinstance(register_number, int):
        existing = User.query.filter_by(account_type=ACCOUNT_CAIXA).all()
        for u in existing:
            try:
                if isinstance(u.profile, dict) and u.profile.get("register_number") == register_number:
                    errors.append(f"register_number '{register_number}' is already in use")
                    break
            except Exception:
                pass

    if errors:
        return {}, errors

    # normalized profile
    normalized = {
        "register_number": register_number,
        "operator_name": (operator_name or "").strip(),
        "fast_lane": fast_lane,
        "preferential": preferential,
    }
    return normalized, []


def _validate_profile_for_storage(profile: dict | None) -> tuple[dict, list[str]]:
    """
    STORAGE required profile:
      - operator_name: str
      - sector_id: int|str (optional)
      - restrict_to_sector: bool (auto True if sector_id provided)
    """
    errors: list[str] = []
    if not isinstance(profile, dict):
        return {}, ["Field 'profile' must be an object for STORAGE"]

    operator_name = profile.get("operator_name")
    sector_id = profile.get("sector_id")  # optional
    restrict_to_sector = profile.get("restrict_to_sector")

    if not isinstance(operator_name, str) or not operator_name.strip():
        errors.append("profile.operator_name must be a non-empty string")

    if sector_id is not None and not isinstance(sector_id, (int, str)):
        errors.append("profile.sector_id must be an integer or string when provided")

    if restrict_to_sector is None:
        restrict_to_sector = sector_id is not None
    elif not isinstance(restrict_to_sector, bool):
        errors.append("profile.restrict_to_sector must be boolean")

    if errors:
        return {}, errors

    normalized = {
        "operator_name": (operator_name or "").strip(),
        "sector_id": sector_id,
        "restrict_to_sector": restrict_to_sector,
    }
    return normalized, []


def _validate_profile_for_supervisor(profile: dict | None) -> tuple[dict, list[str]]:
    """
    SUPERVISOR required profile:
      - operator_name: str
      - cash_register_range: {start:int, end:int} (optional, start <= end)
      - restrict_to_range: bool (auto True if cash_register_range provided)
    """
    errors: list[str] = []
    if not isinstance(profile, dict):
        return {}, ["Field 'profile' must be an object for SUPERVISOR"]

    operator_name = profile.get("operator_name")
    cash_range = profile.get("cash_register_range")  # optional
    restrict_to_range = profile.get("restrict_to_range")

    if not isinstance(operator_name, str) or not operator_name.strip():
        errors.append("profile.operator_name must be a non-empty string")

    if cash_range is not None:
        if not isinstance(cash_range, dict):
            errors.append("profile.cash_register_range must be an object with 'start' and 'end'")
        else:
            start = cash_range.get("start")
            end = cash_range.get("end")
            if not isinstance(start, int) or not isinstance(end, int):
                errors.append("profile.cash_register_range.start and .end must be integers")
            elif start > end:
                errors.append("profile.cash_register_range.start must be <= end")
    else:
        start = end = None

    if restrict_to_range is None:
        restrict_to_range = cash_range is not None
    elif not isinstance(restrict_to_range, bool):
        errors.append("profile.restrict_to_range must be boolean")

    if errors:
        return {}, errors

    normalized = {
        "operator_name": (operator_name or "").strip(),
        "cash_register_range": (
            {"start": cash_range.get("start", None), "end": cash_range.get("end", None)}
            if cash_range is not None else None
        ),
        "restrict_to_range": restrict_to_range,
    }
    return normalized, []

def _normalize_account_type(value: str) -> str:
    """
    Normalize and map account_type aliases.
    """
    if not value:
        return ""
    v = value.strip().upper()
    return v


def _validate_and_build_privileges(payload_privs: dict | None) -> tuple[dict, list[str]]:
    """
    Validate privilege dictionary for CUSTOM accounts.
    - Only ALLOWED_PRIVILEGE_KEYS are accepted.
    - Values must be booleans.
    - Missing keys default to False.
    Returns (privileges_dict, errors_list).
    """
    errors: list[str] = []
    if payload_privs is None:
        return {}, ["Field 'privileges' is required for CUSTOM accounts"]

    if not isinstance(payload_privs, dict):
        return {}, ["Field 'privileges' must be an object (key: bool)"]

    # start with all False
    result = {k: False for k in ALLOWED_PRIVILEGE_KEYS}

    for key, value in payload_privs.items():
        key_up = str(key).strip().upper()
        if key_up not in ALLOWED_PRIVILEGE_KEYS:
            errors.append(f"Unknown privilege key: '{key}'. Allowed: {sorted(ALLOWED_PRIVILEGE_KEYS)}")
            continue
        if not isinstance(value, bool):
            errors.append(f"Privilege '{key}' must be boolean (true/false)")
            continue
        result[key_up] = value

    return result, errors


@accounts_bp.route("/accounts", methods=["POST"])
@auth_utils.token_required
@auth_utils.admin_required
def create_account():
    """
    Create an account:
      - OWNER / FULL_MANAGEMENT: uses default privileges
      - CAIXA / STORAGE / SUPERVISOR: requires profile fields (validated below)
      - CUSTOM: requires 'privileges' object
    """
    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip().lower()
    password = data.get("password")
    confirm_password = data.get("confirm_password")
    account_type = (data.get("account_type") or "").strip().upper()

    if not email or not password or not confirm_password or not account_type:
        return error_response("Missing required fields: email, password, confirm_password, account_type", 400)

    if account_type not in SUPPORTED_ACCOUNT_TYPES:
        return error_response(
            "Invalid account_type. Allowed: OWNER, FULL_MANAGEMENT, CAIXA, STORAGE, SUPERVISOR, CUSTOM", 400
        )

    if password != confirm_password:
        return error_response("Passwords do not match", 400)

    if User.query.filter_by(email=email).first():
        return error_response("Email is already registered", 409)

    # Resolve privileges and profile
    privileges = None
    profile = {}

    if account_type in (ACCOUNT_OWNER, ACCOUNT_FULL, ACCOUNT_CAIXA, ACCOUNT_STORAGE, ACCOUNT_SUPERVISOR):
        privileges = DEFAULT_PRIVILEGES[account_type].copy()

        if account_type == ACCOUNT_CAIXA:
            profile_payload = data.get("profile")
            profile, pf_errors = _validate_profile_for_caixa(profile_payload)
            if pf_errors:
                return error_response("; ".join(pf_errors), 400)

        elif account_type == ACCOUNT_STORAGE:
            profile_payload = data.get("profile")
            profile, pf_errors = _validate_profile_for_storage(profile_payload)
            if pf_errors:
                return error_response("; ".join(pf_errors), 400)

        elif account_type == ACCOUNT_SUPERVISOR:
            profile_payload = data.get("profile")
            profile, pf_errors = _validate_profile_for_supervisor(profile_payload)
            if pf_errors:
                return error_response("; ".join(pf_errors), 400)

    else:
        # CUSTOM
        payload_privs = data.get("privileges")
        privileges, priv_errors = _validate_and_build_privileges(payload_privs)
        if priv_errors:
            return error_response("; ".join(priv_errors), 400)

    # Create and persist
    new_user = User(email=email, account_type=account_type, privileges=privileges, profile=profile)
    new_user.set_password(password)

    try:
        db.session.add(new_user)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return error_response("Failed to create account", 500)

    return success_response("Account created successfully", {
        "id": new_user.id,
        "email": new_user.email,
        "account_type": new_user.account_type,
        "privileges": new_user.privileges,
        "profile": new_user.profile
    }, 201)

