from __future__ import annotations

from sqlalchemy import delete

from llm_api.db.database import get_db_session
from llm_api.db.models import ModelRecord


def test_list_models_reseeds_missing_defaults(client_factory):
    expected_defaults = [
        "local-text",
        "stabilityai/sdxl-turbo",
        "openai/shap-e",
    ]

    with get_db_session() as db:
        db.execute(
            delete(ModelRecord).where(
                ModelRecord.id.in_(expected_defaults)
            )
        )

    client = client_factory()
    response = client.get("/v1/models", headers={"X-Api-Key": "test-key"})

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["models"]}
    assert "local-text" in ids
    assert "stabilityai/sdxl-turbo" in ids
    assert "openai/shap-e" in ids
