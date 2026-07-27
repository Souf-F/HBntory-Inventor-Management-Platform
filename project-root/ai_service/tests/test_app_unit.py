"""
Mocked tests for app.py's REST endpoint: agent.ask is patched out, so
these never call Groq or the MCP server. Validates input handling and
response shape only.
"""

import pytest

import app


@pytest.fixture
def client():
    return app.app.test_client()


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_ask_missing_question_field(client):
    response = client.post("/ask", json={})
    assert response.status_code == 400
    assert "question" in response.get_json()["error"]


def test_ask_blank_question(client):
    response = client.post("/ask", json={"question": "   "})
    assert response.status_code == 400


def test_ask_non_string_question(client):
    response = client.post("/ask", json={"question": 42})
    assert response.status_code == 400


def test_ask_valid_question_returns_answer(client, monkeypatch):
    async def fake_ask(question):
        assert question == "Where is the monitor?"
        return "It's in Paris."

    monkeypatch.setattr(app, "ask", fake_ask)

    response = client.post("/ask", json={"question": "  Where is the monitor?  "})

    assert response.status_code == 200
    assert response.get_json() == {"answer": "It's in Paris."}