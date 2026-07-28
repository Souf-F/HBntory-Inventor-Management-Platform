from flask import Blueprint, request, jsonify
from flask_login import current_user

from app.models import db, Stock, Branch, Role
from app.product_api import (
    _get,
    get_product,
    get_product_names,
    list_products,
    ProductAPIError,
)
from routes.middleware import role_required, branch_required

stock_bp = Blueprint("stock", __name__)


@stock_bp.route("/branches/<int:branch_id>/stock", methods=["POST"])
@role_required(Role.COMMON_USER)
@branch_required
def add_stock(branch_id):
    """Add a given quantity of a product to the current user's branch."""
    data = request.get_json(silent=True) or {}
    product_id = data.get("product_id")
    quantity = data.get("quantity")

    if not product_id:
        return jsonify({"status": "error", "message": "product_id is required"}), 400

    # Reject anything that is not a positive integer
    if not isinstance(quantity, int) or quantity <= 0:
        return jsonify({"status": "error", "message": "Quantity must be a positive integer"}), 400

    # Confirm this product actually exists in the external catalog before
    # letting it into our stock table (see architecture.md, section 5).
    #
    # We call _get directly rather than get_product() here: get_product()
    # deliberately swallows every ProductAPIError and returns None, which
    # would make an unreachable API indistinguishable from an unknown SKU.
    # On a write operation that distinction matters — the user must be told
    # "the catalog is down, try again" instead of "this product does not
    # exist" (see the API's README: an external service is not always
    # available or always fast).
    try:
        _get(f"/api/v1/products/{product_id}")
    except ProductAPIError as exc:
        if "not found" in str(exc).lower():
            return jsonify({"status": "error", "message": "Unknown product_id"}), 404
        return jsonify({"status": "error", "message": "Product API is currently unreachable"}), 503

    stock_item = Stock.query.filter_by(branch_id=branch_id, product_id=product_id).first()

    if stock_item is None:
        # First time this product is stocked in this branch
        stock_item = Stock(branch_id=branch_id, product_id=product_id, quantity=quantity)
        db.session.add(stock_item)
    else:
        stock_item.quantity += quantity

    db.session.commit()
    return jsonify({
        "status": "success",
        "product_id": product_id,
        "quantity": stock_item.quantity
    })


@stock_bp.route("/branches/<int:branch_id>/stock/remove", methods=["POST"])
@role_required(Role.COMMON_USER)
@branch_required
def remove_stock(branch_id):
    """Remove a given quantity of a product from the current user's branch."""
    data = request.get_json(silent=True) or {}
    product_id = data.get("product_id")
    quantity = data.get("quantity")

    if not product_id:
        return jsonify({"status": "error", "message": "product_id is required"}), 400

    if not isinstance(quantity, int) or quantity <= 0:
        return jsonify({"status": "error", "message": "Quantity must be a positive integer"}), 400

    stock_item = Stock.query.filter_by(branch_id=branch_id, product_id=product_id).first()

    if stock_item is None:
        return jsonify({"status": "error", "message": "Product not found in this branch"}), 404

    # Never let the quantity go negative — checked here in addition to the
    # DB-level CheckConstraint, so we can return a clear error instead of
    # a raw SQL exception.
    if quantity > stock_item.quantity:
        return jsonify({"status": "error", "message": "Not enough stock available"}), 400

    stock_item.quantity -= quantity
    db.session.commit()

    return jsonify({
        "status": "success",
        "product_id": product_id,
        "quantity": stock_item.quantity
    })


@stock_bp.route("/branches/<int:branch_id>/stock/<product_id>", methods=["GET"])
@role_required(Role.COMMON_USER)
@branch_required
def check_stock(branch_id, product_id):
    """Check the available quantity of one product in the current user's branch.

    The product name is resolved on the fly from the external catalog and is
    never persisted — only the SKU lives in our database. If the catalog is
    unreachable, product_name comes back as null and the caller falls back
    to displaying the raw SKU.
    """
    stock_item = Stock.query.filter_by(branch_id=branch_id, product_id=product_id).first()

    if stock_item is None:
        return jsonify({"status": "error", "message": "Product not found in this branch"}), 404

    product = get_product(stock_item.product_id)

    return jsonify({
        "product_id": stock_item.product_id,
        "product_name": product.get("name") if product else None,
        "quantity": stock_item.quantity
    })


@stock_bp.route("/branches/<int:branch_id>/stock", methods=["GET"])
@role_required(Role.COMMON_USER)
@branch_required
def list_stock(branch_id):
    """List every product currently in stock for the current user's branch.

    Product names are resolved on the fly from the external catalog, in a
    single call, and are never persisted — only the SKU lives in our
    database (see architecture.md, section 3). If the Product API is
    unavailable the page still works: product_name is null and the client
    falls back to the raw SKU.
    """
    stock_items = Stock.query.filter_by(branch_id=branch_id).all()
    names = get_product_names(item.product_id for item in stock_items)

    return jsonify([
        {
            "product_id": item.product_id,
            "product_name": names.get(item.product_id),
            "quantity": item.quantity,
        }
        for item in stock_items
    ])


@stock_bp.route("/products", methods=["GET"])
@role_required(Role.COMMON_USER)
def available_products():
    """
    List products from the external catalog, used to populate the product
    selector on the stock-add form. Read-only — nothing here is stored
    locally (see architecture.md, section 3).
    """
    try:
        products = list_products()
    except ProductAPIError:
        return jsonify({"status": "error", "message": "Product API is currently unreachable"}), 503

    return jsonify(products)


@stock_bp.route("/stock", methods=["GET"])
@role_required(Role.ADMIN)
def list_all_stock():
    """
    Read-only overview of stock across every branch, for the admin.

    Admins never manage stock (add/remove), but this view lets them
    see the full picture across branches without breaking that rule —
    no write operation exists on this route.
    """
    items = (
        db.session.query(Stock, Branch.name)
        .join(Branch, Stock.branch_id == Branch.id)
        .all()
    )

    names = get_product_names(stock.product_id for stock, _ in items)

    return jsonify([
        {
            "branch_id": stock.branch_id,
            "branch_name": branch_name,
            "product_id": stock.product_id,
            "product_name": names.get(stock.product_id),
            "quantity": stock.quantity
        }
        for stock, branch_name in items
    ])
