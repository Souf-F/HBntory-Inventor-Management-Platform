"""
Live tests for agent.py: real calls to the Product API, the MCP server,
and Groq. These consume real quota, so they are opt-in only (see
pytest.ini: the default `pytest` run excludes them).

Run explicitly, sparingly, once you have enough Groq quota for the day:
    pytest -m live

Prerequisites, same as manual_test.py:
    1. The Product API is running (see product_mcp_server/README.md).
    2. The MCP server is running: cd product_mcp_server && python server.py
    3. GROQ_API_KEY is set in ai_service/.env

Assertions are intentionally loose (substring checks, not exact match),
since the model's exact phrasing varies between runs. What matters is
that grounded facts are present and nothing invented slips through.
"""

import pytest

from agent import ask

pytestmark = pytest.mark.live

NOT_FOUND_MARKERS = [
    "not found",
    "n'a pas été trouvé",
    "n'existe pas",
    "pas trouvé",
    "n'a pas pu",
    "no branch found",
    "no product found",
    "does not exist",
    "n'y a pas de branche",
    "n'y ait pas de branche",
    "aucune branche",
    "pas de branche avec",
]


def _says_not_found(answer: str) -> bool:
    lowered = answer.lower()
    return any(marker in lowered for marker in NOT_FOUND_MARKERS)


@pytest.mark.asyncio
async def test_product_details_question():
    answer = await ask("Quel est le prix du 24 inch Compact Monitor ?")
    assert "169.99" in answer or "169,99" in answer


@pytest.mark.asyncio
async def test_product_not_in_catalog():
    answer = await ask("Où puis-je trouver du café en grains 1kg ?")
    assert _says_not_found(answer)
    # Must not invent a price for a product that doesn't exist.
    assert "€" not in answer and "$" not in answer


@pytest.mark.asyncio
async def test_where_is_product_available():
    answer = await ask("Où puis-je trouver le 24 inch Compact Monitor en stock ?")
    assert "paris" in answer.lower()


@pytest.mark.asyncio
async def test_whats_in_one_branch():
    answer = await ask("Quels produits sont disponibles dans la branche HBntory Paris ?")
    # At least one real product_id from the seeded catalog must be named.
    assert "HB-" in answer


@pytest.mark.asyncio
async def test_unknown_branch():
    answer = await ask("Quels produits sont disponibles dans la branche de Bordeaux ?")
    assert _says_not_found(answer)


@pytest.mark.asyncio
async def test_shopping_list_feasibility():
    answer = await ask(
        "Si j'ai besoin de 5 24 inch Compact Monitor, quelle branche peut me les fournir ?"
    )
    assert "paris" in answer.lower()


@pytest.mark.asyncio
async def test_out_of_scope_question_is_declined():
    answer = await ask("Raconte-moi une blague.")
    assert not _says_not_found(answer)
    assert "169.99" not in answer


# --- Rephrasings of the 4 core question types, to check the agent isn't ---
# --- relying on the exact wording used in the tests above.               ---


@pytest.mark.asyncio
async def test_product_details_rephrased():
    answer = await ask("C'est combien le 24 inch Compact Monitor ?")
    assert "169.99" in answer or "169,99" in answer


@pytest.mark.asyncio
async def test_where_available_rephrased():
    answer = await ask("Dans quelles branches puis-je acheter le 24 inch Compact Monitor ?")
    assert "paris" in answer.lower()


@pytest.mark.asyncio
async def test_whats_in_branch_rephrased():
    answer = await ask("Que vendez-vous à HBntory Paris ?")
    assert "HB-" in answer


# --- Edge cases beyond the 4 canonical examples. ---


@pytest.mark.asyncio
async def test_product_exists_but_has_no_stock_anywhere():
    # 8-Port Managed Switch is a real Product API catalog entry, but it was
    # never given a stock row in seed.py: it exists as a product, it's just
    # not stocked anywhere. The agent must not confuse the two.
    answer = await ask("Où puis-je trouver le 8-Port Managed Switch en stock ?")
    assert _says_not_found(answer)


@pytest.mark.asyncio
async def test_shopping_list_no_single_branch_can_cover_it():
    # HBntory Paris has 40 units of this product, no branch has 100.
    answer = await ask(
        "J'ai besoin de 100 24 inch Compact Monitor, quelle branche peut me les fournir ?"
    )
    assert _says_not_found(answer)


@pytest.mark.asyncio
async def test_branch_name_case_insensitivity():
    answer = await ask("Quels produits sont disponibles dans la branche hbntory paris ?")
    # Whatever the answer, it must not silently invent a product list for a
    # branch name it wasn't sure matched: either it finds the real branch
    # (case-insensitive match) and names real products, or it says it
    # can't find it. It must not do neither (e.g. a vague non-answer).
    assert "HB-" in answer or _says_not_found(answer)