import json
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app.main import app


CLIENT = TestClient(app)
TEXT = "From the library to ILC without stairs"


def model_response(suggestion):
    return json.dumps({"message": {"content": json.dumps(suggestion)}}).encode()


def fake_connection(body, status=200):
    response = Mock(status=status, length=len(body))
    response.getheader.side_effect = lambda key, default="": "application/json" if key == "Content-Type" else default
    response.read.return_value = body
    connection = Mock()
    connection.getresponse.return_value = response
    return connection


def test_ai_off_never_calls_ollama_and_route_stays_unavailable():
    with patch("app.ai.HTTPConnection") as call:
        response = CLIENT.post("/api/interpret", json={"text": TEXT, "use_local_ai": False})
    call.assert_not_called()
    assert response.json() == {"status": "fallback", "suggestion": None}
    route = CLIENT.post("/api/route", json={"itinerary": ["Student Union", "Integrative Learning Center"]})
    assert route.json()["status"] == "unavailable"


def test_valid_local_suggestion_uses_catalog_ids_only():
    suggestion = {"origin_id": "du-bois", "destination_id": "ilc", "next_class": False,
                  "step_free": True, "avoid_steep": True}
    connection = fake_connection(model_response(suggestion))
    with patch("app.ai.HTTPConnection", return_value=connection) as call:
        response = CLIENT.post("/api/interpret", json={"text": TEXT, "use_local_ai": True})
    assert response.json() == {"status": "ai", "suggestion": {**suggestion, "avoid_steep": False}}
    assert call.call_args.args[:2] == ("127.0.0.1", 11434)
    assert connection.request.call_args.args[:2] == ("POST", "/api/chat")
    payload = json.loads(connection.request.call_args.kwargs["body"])
    assert payload["stream"] is False and payload["format"]["type"] == "object"
    assert payload["messages"][1]["content"] == TEXT


def test_malformed_or_unavailable_model_falls_back_without_route_claim():
    invalid = {"origin_id": "made-up-path", "destination_id": "ilc", "next_class": False,
               "step_free": True, "avoid_steep": False}
    unrelated = {**invalid, "origin_id": "student-union"}
    for result in (fake_connection(model_response(invalid)), fake_connection(model_response(unrelated)),
                   fake_connection(b"not json"), OSError("offline")):
        with patch("app.ai.HTTPConnection", side_effect=result if isinstance(result, Exception) else None,
                   return_value=None if isinstance(result, Exception) else result):
            response = CLIENT.post("/api/interpret", json={"text": TEXT, "use_local_ai": True})
        assert response.json() == {"status": "fallback", "suggestion": None}
    route = CLIENT.post("/api/route", json={"itinerary": ["Student Union", "Integrative Learning Center"]})
    assert route.json()["status"] == "unavailable"
