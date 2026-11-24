
from unittest.mock import patch

from fastapi.testclient import TestClient
from main import app


client = TestClient(app)


def test_ask_rejects_fabricated_citations():
    passages = [
        (
            "A money transmission licensee must maintain a surety bond.",
            {
                "state": "Texas",
                "section": "Sec. 152.352.",
                "url": "https://example.com/statute",
            },
        )
    ]

    with (
        patch("main.get_rag_model"),
        patch("chromadb.PersistentClient") as mock_db,
        patch("main.retrieve", return_value=(passages, None)),
        patch("llm.chat", return_value="A bond is required [99]."),
    ):
        mock_db.return_value.get_collection.return_value = object()

        response = client.post(
            "/ask",
            json={
                "question": "What bond is required?",
                "state": "TX",
            },
        )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "citation_verification_failed"