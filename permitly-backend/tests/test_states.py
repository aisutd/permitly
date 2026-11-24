
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from main import app


client = TestClient(app)


def test_list_states():
    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.order.return_value.execute.return_value.data = [
        {"code": "TX", "name": "Texas"},
        {"code": "CA", "name": "California"},
    ]

    with patch("main.db.get_client", return_value=mock_db):
        response = client.get("/states")

    assert response.status_code == 200
    assert len(response.json()["states"]) == 2


def test_get_state():
    mock_db = MagicMock()

    state_result = MagicMock()
    state_result.data = [{"code": "TX", "name": "Texas"}]

    requirements_result = MagicMock()
    requirements_result.data = [
        {"field_name": "license_required", "value": True}
    ]

    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value = state_result

    mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = requirements_result

    with patch("main.db.get_client", return_value=mock_db):
        response = client.get("/states/TX")

    assert response.status_code == 200
    assert response.json()["state"]["code"] == "TX"
    assert len(response.json()["requirements"]) == 1


def test_unknown_state():
    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

    with patch("main.db.get_client", return_value=mock_db):
        response = client.get("/states/ZZ")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "state_not_found"