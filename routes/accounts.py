"""
Blueprint para Gerenciamento de Contas de Usuário
-------------------------------------------------
Este módulo expõe os endpoints da API para o CRUD (Create, Read, Update, Delete)
de contas de usuário. A lógica de negócio e validação é importada de 'utils.accounts'.
"""

from flask import Blueprint, request, g
from models.user import User, db
from utils.responses import success_response, error_response
import utils.auth as auth_utils
from sqlalchemy.orm.attributes import flag_modified

# Importa as constantes e funções de validação do novo módulo utilitário
import utils.accounts as account_utils

accounts_bp = Blueprint("accounts", __name__)


# ==================================
# ==== CRUD DE CONTAS DE USUÁRIO ====
# ==================================

@accounts_bp.route("/accounts", methods=["GET"])
@auth_utils.token_required
@auth_utils.privilege_required("ADMIN")
def list_accounts():
    """Lista todas as contas de usuário registradas."""
    users = User.query.order_by(User.id.asc()).all()
    # Supondo que seu modelo User tenha um método to_dict(), que é uma boa prática
    accounts = [user.to_dict() for user in users]
    return success_response("Contas recuperadas com sucesso", {"accounts": accounts})


@accounts_bp.route("/accounts/<int:user_id>", methods=["GET"])
@auth_utils.token_required
@auth_utils.privilege_required("ADMIN")
def get_account(user_id):
    """Retorna os dados de uma conta específica por ID."""
    user = User.query.get_or_404(user_id)
    return success_response("Conta recuperada com sucesso", user.to_dict())


@accounts_bp.route("/accounts", methods=["POST"])
@auth_utils.token_required
@auth_utils.privilege_required("ACCOUNT_CREATOR")
def create_account():
    """
    Cria uma nova conta de usuário com tipo e privilégios específicos.
    A lógica de validação complexa é delegada para o módulo `utils.accounts`.
    """
    data = request.get_json(silent=True) or {}
    
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")
    account_type = (data.get("account_type") or "").strip().upper()
    if not all([email, password, account_type]):
        return error_response("Campos 'email', 'password' e 'account_type' são obrigatórios.", 400)

    if account_type not in account_utils.SUPPORTED_ACCOUNT_TYPES:
        return error_response(f"Tipo de conta inválido: {account_type}", 400)

    if User.query.filter_by(email=email).first():
        return error_response("O e-mail informado já está registrado.", 409)

    privileges, profile = {}, {}
    errors = []

    if account_type == account_utils.ACCOUNT_CUSTOM:
        privileges, errors = account_utils.validate_and_build_privileges(data.get("privileges"))
    else:
        privileges = account_utils.DEFAULT_PRIVILEGES.get(account_type, {}).copy()
        profile_payload = data.get("profile")

        if account_type == account_utils.ACCOUNT_CAIXA:
            profile, errors = account_utils.validate_profile_for_caixa(profile_payload)
        elif account_type == account_utils.ACCOUNT_STORAGE:
            profile, errors = account_utils.validate_profile_for_storage(profile_payload)
        elif account_type == account_utils.ACCOUNT_SUPERVISOR:
            profile, errors = account_utils.validate_profile_for_supervisor(profile_payload)

    if errors:
        return error_response("; ".join(errors), 400)

    new_user = User(email=email, account_type=account_type, privileges=privileges, profile=profile)
    new_user.set_password(password)

    try:
        db.session.add(new_user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return error_response(f"Falha ao criar conta: {str(e)}", 500)

    return success_response("Conta criada com sucesso", new_user.to_dict(), 201)


@accounts_bp.route("/accounts/<int:user_id>/profile", methods=["PATCH"])
@auth_utils.token_required
@auth_utils.privilege_required("ADMIN")
def update_account_profile(user_id):
    """
    Atualiza o JSON de perfil de uma conta que suporte perfis
    (CAIXA, STORAGE, SUPERVISOR).
    """
    user = User.query.get_or_404(user_id)
    profile_data = request.get_json(silent=True) or {}
    profile, errors = {}, []

    # Mapeia o tipo de conta para a função de validação correta
    validators = {
        account_utils.ACCOUNT_CAIXA: account_utils.validate_profile_for_caixa,
        account_utils.ACCOUNT_STORAGE: account_utils.validate_profile_for_storage,
        account_utils.ACCOUNT_SUPERVISOR: account_utils.validate_profile_for_supervisor,
    }

    validator_func = validators.get(user.account_type)
    if not validator_func:
        return error_response(f"Contas do tipo '{user.account_type}' não possuem um perfil editável.", 400)

    profile, errors = validator_func(profile_data)
    if errors:
        return error_response("; ".join(errors), 400)

    user.profile = profile
    # Avisa o SQLAlchemy que um campo JSON mutável foi alterado
    flag_modified(user, "profile")

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return error_response(f"Falha ao atualizar o perfil: {str(e)}", 500)

    return success_response("Perfil da conta atualizado com sucesso.", {"profile": user.profile})


@accounts_bp.route("/accounts/<int:user_id>/privileges", methods=["PATCH"])
@auth_utils.token_required
@auth_utils.privilege_required("ADMIN")
def update_account_privileges(user_id):
    """
    Atualiza o JSON de privilégios de uma conta do tipo CUSTOM.
    """
    user = User.query.get_or_404(user_id)
    
    if user.account_type != account_utils.ACCOUNT_CUSTOM:
        return error_response("Apenas contas do tipo CUSTOM podem ter seus privilégios modificados.", 400)

    privileges_data = request.get_json(silent=True)
    privileges, errors = account_utils.validate_and_build_privileges(privileges_data)

    if errors:
        return error_response("; ".join(errors), 400)

    user.privileges = privileges
    # Avisa o SQLAlchemy que um campo JSON mutável foi alterado
    flag_modified(user, "privileges")

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return error_response(f"Falha ao atualizar privilégios: {str(e)}", 500)

    return success_response("Privilégios da conta atualizados com sucesso.", {"privileges": user.privileges})


@accounts_bp.route("/accounts/<int:user_id>", methods=["DELETE"])
@auth_utils.token_required
@auth_utils.privilege_required("ADMIN")
def delete_account(user_id):
    """
    Deleta uma conta de usuário pelo ID.
    Impede que um usuário delete a si mesmo.
    """
    # g.current_user é injetado pelo decorador @token_required
    if g.current_user.id == user_id:
        return error_response("Você não pode deletar sua própria conta.", 403)

    user = User.query.get_or_404(user_id)
    
    # Adicional: Regra de negócio para não permitir deletar o OWNER principal
    if user.account_type == account_utils.ACCOUNT_OWNER:
        return error_response("A conta principal do sistema (OWNER) não pode ser deletada.", 403)

    try:
        db.session.delete(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return error_response(f"Falha ao deletar a conta: {str(e)}", 500)

    return success_response("Conta deletada com sucesso.")