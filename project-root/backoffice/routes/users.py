from flask import Blueprint, request, jsonify

from app.models import db, User, Role, Branch
from routes.auth import hash_password
from routes.middleware import role_required

users_bp = Blueprint("users", __name__)


def _reject_if_admin(user):
    """
    The single admin account cannot be modified or deactivated through the API.

    There is no endpoint to create another admin, so deactivating this one
    would lock the system out permanently — the database would have to be
    reseeded. The frontend already hides these actions (canManage), but a
    plain curl call would otherwise go straight through: authorization has
    to be enforced here, on the backend, where it actually counts.

    Returns a ready-to-return 403 response, or None when the user is fine
    to operate on.
    """
    if user.role == Role.ADMIN:
        return jsonify({
            "status": "error",
            "message": "The admin account cannot be modified"
        }), 403
    return None


@users_bp.route("/users", methods=["GET"])
@role_required(Role.ADMIN)
def list_users():
    """List every user in the system, including soft-deleted ones."""
    users = User.query.all()

    return jsonify([
        {
            "id": user.id,
            "username": user.username,
            "role": user.role.value,
            "branch_id": user.branch_id,
            "is_active": user.is_active
        }
        for user in users
    ])


@users_bp.route("/users", methods=["POST"])
@role_required(Role.ADMIN)
def create_user():
    """Create a new common user, assigned to a branch."""
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")
    branch_id = data.get("branch_id")

    if not username or not password or not branch_id:
        return jsonify({"status": "error", "message": "username, password and branch_id are required"}), 400

    # Foreign keys are enforced at the SQLite level (see models.py), so an
    # unknown branch_id would raise an IntegrityError and surface as a 500.
    # Check it here instead, to return a clear 400.
    if Branch.query.get(branch_id) is None:
        return jsonify({"status": "error", "message": "Unknown branch_id"}), 400

    if User.query.filter_by(username=username).first() is not None:
        return jsonify({"status": "error", "message": "Username already taken"}), 409

    # Admins are never created through this endpoint — there is only one,
    # created once via the seed script (see architecture.md, section 4).
    new_user = User(
        username=username,
        password_hash=hash_password(password),
        role=Role.COMMON_USER,
        branch_id=branch_id
    )
    db.session.add(new_user)
    db.session.commit()

    return jsonify({
        "status": "success",
        "id": new_user.id,
        "username": new_user.username
    }), 201


@users_bp.route("/users/<int:user_id>", methods=["PATCH"])
@role_required(Role.ADMIN)
def update_user(user_id):
    """Update a user's username, password and/or assigned branch."""
    user = User.query.get(user_id)
    if user is None:
        return jsonify({"status": "error", "message": "User not found"}), 404

    blocked = _reject_if_admin(user)
    if blocked:
        return blocked

    data = request.get_json(silent=True) or {}

    if "username" in data:
        if not data["username"]:
            return jsonify({"status": "error", "message": "username cannot be empty"}), 400
        existing = User.query.filter_by(username=data["username"]).first()
        if existing is not None and existing.id != user.id:
            return jsonify({"status": "error", "message": "Username already taken"}), 409
        user.username = data["username"]

    # data.get() rather than "password" in data: an empty string would
    # otherwise be hashed and silently become the new password.
    if data.get("password"):
        user.password_hash = hash_password(data["password"])

    if "branch_id" in data:
        if Branch.query.get(data["branch_id"]) is None:
            return jsonify({"status": "error", "message": "Unknown branch_id"}), 400
        user.branch_id = data["branch_id"]

    db.session.commit()
    return jsonify({"status": "success", "id": user.id})


@users_bp.route("/users/<int:user_id>", methods=["DELETE"])
@role_required(Role.ADMIN)
def soft_delete_user(user_id):
    """Soft-delete a user: they can no longer log in, but their stock
    history and data stay in the database."""
    user = User.query.get(user_id)
    if user is None:
        return jsonify({"status": "error", "message": "User not found"}), 404

    blocked = _reject_if_admin(user)
    if blocked:
        return blocked

    user.is_active = False
    db.session.commit()

    return jsonify({"status": "success", "message": "User deactivated"})


@users_bp.route("/users/<int:user_id>/reactivate", methods=["PATCH"])
@role_required(Role.ADMIN)
def reactivate_user(user_id):
    """Reactivate a previously soft-deleted user."""
    user = User.query.get(user_id)
    if user is None:
        return jsonify({"status": "error", "message": "User not found"}), 404

    user.is_active = True
    db.session.commit()

    return jsonify({"status": "success", "message": "User reactivated"})


@users_bp.route("/branches", methods=["GET"])
@role_required(Role.ADMIN)
def list_branches():
    """List all branches, for populating the admin's branch selector."""
    branches = Branch.query.all()
    return jsonify([{"id": b.id, "name": b.name} for b in branches])
