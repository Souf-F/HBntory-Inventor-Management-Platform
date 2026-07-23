from fastmcp.exceptions import ToolError
from pydantic import BaseModel

from db import Branch, Session, Stock
from mcp_instance import mcp


class BranchStockLevel(BaseModel):
    """Quantity of one product in one branch."""

    branch_name: str
    quantity: int


class BranchProduct(BaseModel):
    """One product's quantity, within a single branch's stock listing."""

    product_id: str
    quantity: int


class ShoppingListItem(BaseModel):
    """One line of a requested shopping list."""

    product_id: str
    quantity: int


class BranchFeasibility(BaseModel):
    """Whether one branch, alone, can fulfill a full shopping list."""

    branch_name: str
    can_fulfill: bool
    missing_product_ids: list[str]


def _get_branch_by_name(session, branch_name: str) -> Branch:
    branch = session.query(Branch).filter_by(name=branch_name).first()
    if branch is None:
        raise ToolError(f"No branch found with name '{branch_name}'.")
    return branch


@mcp.tool()
def check_stock(
    product_id: str, branch_name: str | None = None
) -> list[BranchStockLevel]:
    """
    Check how much of one product is in stock, across all branches or in
    one named branch.

    Args:
        product_id: the product's external identifier.
        branch_name: optional, restrict to one branch.

    Returns an empty list if the product has no stock anywhere (or in that
    branch), which is a normal case, not an error.
    """
    with Session() as session:
        query = (
            session.query(Stock, Branch.name)
            .join(Branch, Stock.branch_id == Branch.id)
            .filter(Stock.product_id == product_id)
        )
        if branch_name:
            _get_branch_by_name(session, branch_name)
            query = query.filter(Branch.name == branch_name)

        rows = query.all()

    return [
        BranchStockLevel(branch_name=name, quantity=stock.quantity)
        for stock, name in rows
    ]


@mcp.tool()
def list_branch_stock(branch_name: str) -> list[BranchProduct]:
    """
    List every product currently in stock in one branch, with quantities.

    Args:
        branch_name: the branch to list stock for.

    Raises a tool error if the branch doesn't exist. Returns an empty list
    if the branch exists but has no stock, which is a normal case.
    """
    with Session() as session:
        branch = _get_branch_by_name(session, branch_name)
        rows = session.query(Stock).filter_by(branch_id=branch.id).all()

    return [
        BranchProduct(product_id=row.product_id, quantity=row.quantity)
        for row in rows
    ]


@mcp.tool()
def check_shopping_list(items: list[ShoppingListItem]) -> list[BranchFeasibility]:
    """
    For each branch, check whether that branch alone holds enough stock to
    fulfill every item on the list (no aggregation across branches).

    Args:
        items: the requested products and quantities.

    Returns one entry per branch, with can_fulfill and the product_ids
    that branch is short on (empty if it can fulfill the whole list).
    """
    with Session() as session:
        branches = session.query(Branch).all()

        results = []
        for branch in branches:
            missing = []
            for item in items:
                stock_row = (
                    session.query(Stock)
                    .filter_by(branch_id=branch.id, product_id=item.product_id)
                    .first()
                )
                available = stock_row.quantity if stock_row else 0
                if available < item.quantity:
                    missing.append(item.product_id)

            results.append(
                BranchFeasibility(
                    branch_name=branch.name,
                    can_fulfill=not missing,
                    missing_product_ids=missing,
                )
            )

    return results
