import pytest


def _assert_combo_shape(combo: dict) -> None:
    assert set(combo) >= {
        "numbers",
        "score",
        "odd_even_ratio",
        "section_distribution",
    }
    assert isinstance(combo["numbers"], list)
    assert len(combo["numbers"]) == 6
    assert all(isinstance(number, int) for number in combo["numbers"])


def test_recommend_returns_contract_shape(app_client, valid_query):
    response = app_client.get("/api/recommend", params=valid_query)

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) >= {"generated_at", "source", "draws_used", "combos"}
    assert payload["draws_used"] == int(valid_query["draws"])
    assert isinstance(payload["generated_at"], str)
    assert isinstance(payload["source"], str)
    assert isinstance(payload["combos"], list)
    assert len(payload["combos"]) == int(valid_query["n"])

    for combo in payload["combos"]:
        _assert_combo_shape(combo)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("n", "0"),
        ("n", "11"),
        ("n", "abc"),
        ("draws", "99"),
        ("draws", "501"),
        ("draws", "abc"),
        ("offline", "not-a-bool"),
    ],
)
def test_recommend_rejects_invalid_query(app_client, valid_query, field, value):
    invalid_query = dict(valid_query)
    invalid_query[field] = value

    response = app_client.get("/api/recommend", params=invalid_query)

    assert response.status_code == 422


def test_recommend_matches_requested_combo_count(app_client, valid_query):
    query = dict(valid_query)
    query["n"] = 2

    response = app_client.get("/api/recommend", params=query)

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["combos"]) == 2


def test_recommend_uses_offline_source_when_requested(app_client, valid_query):
    query = dict(valid_query)
    query["offline"] = "true"

    response = app_client.get("/api/recommend", params=query)

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "offline"
