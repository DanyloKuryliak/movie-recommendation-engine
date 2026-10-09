import base64
import gzip
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app, load_artifact


@pytest.fixture
def client(tmp_path, monkeypatch):
    artifact = {
        "version": "recommender-v1",
        "rank": 2,
        "movies": {
            "1": {"title": "Liked Space Film", "genres": ["Sci-Fi"]},
            "2": {"title": "Space Sequel", "genres": ["Sci-Fi", "Adventure"]},
            "3": {"title": "Quiet Drama", "genres": ["Drama"]},
            "4": {"title": "Popular Comedy", "genres": ["Comedy"]},
        },
        "item_factors": {"1": [1.0, 0.0], "2": [0.9, 0.0], "3": [-0.9, 0.0], "4": [-1.0, 0.0]},
        "popularity": {
            "1": {"count": 2, "mean": 4.0},
            "2": {"count": 10, "mean": 4.2},
            "3": {"count": 3, "mean": 3.2},
            "4": {"count": 20, "mean": 4.4},
        },
    }
    path = tmp_path / "serving.json"
    path.write_text(json.dumps(artifact), encoding="utf-8")
    monkeypatch.setenv("RECOMMENDER_ARTIFACT_PATH", str(path))
    with TestClient(app) as test_client:
        yield test_client


def test_health_reports_loaded_model(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "model_status": "ready",
        "model_version": "recommender-v1",
        "catalog_size": 4,
    }


def test_loader_accepts_compressed_deployment_secret(tmp_path):
    artifact = {
        "version": "recommender-v1",
        "rank": 1,
        "movies": {"1": {"title": "A film", "genres": []}},
        "item_factors": {"1": [1.0]},
    }
    path = tmp_path / "serving.json.gz.b64"
    path.write_bytes(base64.b64encode(gzip.compress(json.dumps(artifact).encode())))

    assert load_artifact(path)["version"] == "recommender-v1"


def test_catalog_search_and_genre_filter(client):
    response = client.get("/api/v1/movies", params={"q": "space", "genre": "Sci-Fi"})

    assert response.status_code == 200
    assert [movie["title"] for movie in response.json()["items"]] == ["Space Sequel", "Liked Space Film"]
    assert response.json()["total"] == 2
    assert "Sci-Fi" in client.get("/api/v1/genres").json()

    page = client.get("/api/v1/movies", params={"genre": "Sci-Fi", "limit": 1, "offset": 1})
    assert len(page.json()["items"]) == 1
    assert page.json()["total"] == 2


def test_ratings_personalize_results_and_exclude_seen_titles(client):
    response = client.post(
        "/api/v1/recommendations",
        json={"ratings": [{"movie_id": 1, "rating": 5}], "limit": 2},
    )

    assert response.status_code == 200
    recommendations = response.json()
    assert recommendations[0]["movie_id"] == 2
    assert all(item["movie_id"] != 1 for item in recommendations)
    assert recommendations[0]["estimated_rating"] == 4.09
    assert "Sci-Fi" in recommendations[0]["reason"]


def test_no_ratings_uses_training_popularity(client):
    response = client.post("/api/v1/recommendations", json={"limit": 2})

    assert response.status_code == 200
    assert [movie["movie_id"] for movie in response.json()] == [4, 2]
    assert "Popular" in response.json()[0]["reason"]


@pytest.mark.parametrize(
    "payload",
    [
        {"ratings": [{"movie_id": 1, "rating": 5}, {"movie_id": 1, "rating": 4}]},
        {"ratings": [{"movie_id": 999, "rating": 5}]},
        {"ratings": [{"movie_id": 1, "rating": 6}]},
        {"limit": 21},
    ],
)
def test_invalid_recommendation_requests_are_rejected(client, payload):
    response = client.post("/api/v1/recommendations", json=payload)

    assert response.status_code == 422


def test_local_web_origin_can_make_api_request(client):
    response = client.options(
        "/api/v1/recommendations",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
