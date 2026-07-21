from functools import wraps
from flask import jsonify
from flask_login import current_user

from app.models import Role


def role_required(*allowed_roles):
    """
    Decorator that blocks access to a route if the logged-in user
    does not have one of the allowed roles.
    Usage: @role_required(Role.ADMIN)
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # No session at all -> not logged in
            if not current_user.is_authenticated:
                return jsonify({"status": "error", "message": "Not logged in"}), 401

            # Logged in, but wrong role for this route
            if current_user.role not in allowed_roles:
                return jsonify({"status": "error", "message": "Access denied"}), 403

            return f(*args, **kwargs)
        return wrapped
    return decorator


def branch_required(f):
    """
    Decorator that prevents a common user from acting on a branch
    that is not their own. The wrapped route must receive branch_id
    as a parameter (from the URL or JSON body).
    """
    @wraps(f)
    def wrapped(*args, **kwargs):
        target_branch_id = kwargs.get("branch_id")

        # Admins have no branch and are not restricted by this check
        if current_user.role == Role.COMMON_USER:
            if current_user.branch_id != target_branch_id:
                return jsonify({"status": "error", "message": "Branch not allowed"}), 403

        return f(*args, **kwargs)
    return wrapped
