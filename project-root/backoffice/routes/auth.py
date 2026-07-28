from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required
import bcrypt

from app.models import db, User, Role

auth_bp = Blueprint("auth", __name__)


def hash_password(password):
    """Hash a plain-text password using bcrypt (salted automatically)."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode("utf-8")


def verify_password(password, hashed):
    """Check a plain-text password against a bcrypt hash."""
    return bcrypt.checkpw(password.encode(), hashed.encode("utf-8"))


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required
import bcrypt

from app.models import db, User, Role

auth_bp = Blueprint("auth", __name__)


def hash_password(password):
    """Hash a plain-text password using bcrypt (salted automatically)."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode("utf-8")


def verify_password(password, hashed):
    """Check a plain-text password against a bcrypt hash."""
    return bcrypt.checkpw(password.encode(), hashed.encode("utf-8"))


@auth_bp.route("/login", methods=["POST"])
def login():
    # silent=True keeps a malformed or missing JSON body from raising a raw
    # 400/500 out of Flask before we get a chance to answer properly.
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")

    # Missing fields are answered exactly like bad credentials, on purpose:
    # the caller learns nothing about which part was wrong. Without this,
    # verify_password() would call .encode() on None and raise a 500.
    if not username or not password:
        return jsonify({"status": "error", "message": "Invalid credentials"}), 401

    user = User.query.filter_by(username=username).first()

    # Reject unknown users and soft-deleted accounts
    if user is None or not user.is_active:
        return jsonify({"status": "error", "message": "Invalid credentials"}), 401

    # Reject wrong password
    if not verify_password(password, user.password_hash):
        return jsonify({"status": "error", "message": "Invalid credentials"}), 401

    # Everything checks out, create the session
    login_user(user)
    return jsonify({
        "status": "success",
        "username": user.username,
        "role": user.role.value,
        "branch_id": user.branch_id
    })


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"status": "success", "message": "Logged out"})
    password = data.get("password")

    user = User.query.filter_by(username=username).first()

    # Reject unknown users and soft-deleted accounts
    if user is None or not user.is_active:
        return jsonify({"status": "error", "message": "Invalid credentials"}), 401

    # Reject wrong password
    if not verify_password(password, user.password_hash):
        return jsonify({"status": "error", "message": "Invalid credentials"}), 401

    # Everything checks out, create the session
    login_user(user)
    return jsonify({
        "status": "success",
        "username": user.username,
        "role": user.role.value,
        "branch_id": user.branch_id
    })


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"status": "success", "message": "Logged out"})
