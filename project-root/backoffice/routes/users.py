from flask import Blueprint, request, jsonify

from app.models import db, User, Role
from routes.auth import hash_password
from routes.middleware import role_required

users_bp = Blueprint("users", __name__)


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
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    branch_id = data.get("branch_id")

    if not username or not password or not branch_id:
        return jsonify({"status": "error", "message": "username, password and branch_id are required"}), 400

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
    """Update a user's password and/or assigned branch."""
    user = User.query.get(user_id)
    if user is None:
        return jsonify({"status": "error", "message": "User not found"}), 404

    data = request.get_json()

    if "password" in data:
        user.password_hash = hash_password(data["password"])

    if "branch_id" in data:
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

    user.is_active = False
    db.session.commit()

    return jsonify({"status": "success", "message": "User deactivated"})
