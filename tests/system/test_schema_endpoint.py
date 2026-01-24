"""TEST-SYS-011: Parameter schema endpoint
Traceability: SYS-REQ-019
"""


def test_schema_endpoint_returns_parameter_docs(client):
    response = client.get("/v1/schema", headers={"X-API-Key": "test-key"})

    assert response.status_code == 200
    body = response.json()

    generate = body.get("generate", {})
    request = generate.get("request", {})
    parameters = request.get("parameters", {}).get("properties", {})

    assert "temperature" in parameters
    assert "max_tokens" in parameters
    assert "format" in parameters
    assert "stream" in request

    model_field = request.get("model", {})
    assert model_field.get("description")
