"""HTTP API for the MovieLens ALS recommendation demo."""

from __future__ import annotations

import base64
import gzip
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

import numpy as np
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator

PROJECT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACT = PROJECT_DIR / "artifacts" / "recommender-v1" / "serving.json"


def load_artifact(path: Path) -> dict[str, Any]:
    """Read a local JSON artifact or its base64-encoded gzip deployment form."""
    raw = path.read_bytes()
    if path.name.endswith(".b64"):
        raw = gzip.decompress(base64.b64decode(raw, validate=True))
    artifact = json.loads(raw)
    rank = artifact.get("rank")
    factors = artifact.get("item_factors")
    if (
        artifact.get("version") != "recommender-v1"
        or not artifact.get("movies")
        or not factors
        or not isinstance(rank, int)
        or rank < 1
        or any(len(vector) != rank or not np.isfinite(vector).all() for vector in factors.values())
    ):
        raise ValueError(f"Recommendation artifact is incomplete: {path}")
    return artifact


@asynccontextmanager
async def lifespan(app: FastAPI):
    artifact_path = Path(os.getenv("RECOMMENDER_ARTIFACT_PATH", str(DEFAULT_ARTIFACT)))
    app.state.artifact = load_artifact(artifact_path)
    yield


app = FastAPI(title="Movie Recommendation API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[value.strip() for value in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",") if value.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class Rating(BaseModel):
    movie_id: int = Field(ge=1)
    rating: Annotated[float, Field(ge=0.5, le=5.0)]


class RecommendationRequest(BaseModel):
    ratings: list[Rating] = Field(default_factory=list, max_length=50)
    limit: int = Field(default=10, ge=1, le=20)

    @model_validator(mode="after")
    def unique_movies(self) -> "RecommendationRequest":
        movie_ids = [rating.movie_id for rating in self.ratings]
        if len(movie_ids) != len(set(movie_ids)):
            raise ValueError("Rate each movie at most once")
        return self


class Movie(BaseModel):
    movie_id: int
    title: str
    genres: list[str]


class MoviePage(BaseModel):
    items: list[Movie]
    total: int


class Recommendation(BaseModel):
    movie_id: int
    title: str
    genres: list[str]
    estimated_rating: float
    reason: str


def _catalog(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    popularity = artifact.get("popularity", {})
    return [
        {
            "movie_id": int(movie_id),
            "title": movie["title"],
            "genres": movie["genres"],
            "count": int(popularity.get(str(movie_id), {}).get("count", 0)),
            "mean": float(popularity.get(str(movie_id), {}).get("mean", 0.0)),
        }
        for movie_id, movie in artifact["movies"].items()
    ]


@app.get("/health")
def health(request: Request) -> dict[str, str | int]:
    artifact = request.app.state.artifact
    return {
        "status": "ok",
        "model_status": "ready",
        "model_version": artifact["version"],
        "catalog_size": len(artifact["movies"]),
    }


@app.get("/api/v1/genres", response_model=list[str])
def genres(request: Request) -> list[str]:
    all_genres = {genre for movie in request.app.state.artifact["movies"].values() for genre in movie["genres"]}
    return sorted(all_genres)


@app.get("/api/v1/movies", response_model=MoviePage)
def movies(
    request: Request,
    q: Annotated[str, Query(max_length=100)] = "",
    genre: Annotated[str | None, Query(max_length=40)] = None,
    limit: int = Query(default=40, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> MoviePage:
    catalog = _catalog(request.app.state.artifact)
    query = q.strip().casefold()
    found = [
        movie for movie in catalog
        if (not query or query in movie["title"].casefold())
        and (genre is None or genre in movie["genres"])
    ]
    found.sort(key=lambda movie: (-movie["count"], movie["title"].casefold()))
    return MoviePage(items=found[offset : offset + limit], total=len(found))


@app.post("/api/v1/recommendations", response_model=list[Recommendation])
def recommendations(request: Request, payload: RecommendationRequest) -> list[Recommendation]:
    artifact = request.app.state.artifact
    catalog = _catalog(artifact)
    by_id = {movie["movie_id"]: movie for movie in catalog}
    factors: dict[str, list[float]] = artifact["item_factors"]
    rated_ids = {rating.movie_id for rating in payload.ratings}
    unknown = rated_ids - by_id.keys()
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown movie ID(s): {', '.join(map(str, sorted(unknown)))}")

    usable_ratings = [rating for rating in payload.ratings if str(rating.movie_id) in factors]
    user_vector: np.ndarray | None = None
    if usable_ratings:
        matrix = np.asarray([factors[str(rating.movie_id)] for rating in usable_ratings], dtype=np.float64)
        targets = np.asarray([rating.rating for rating in usable_ratings], dtype=np.float64)
        regularization = 0.1 * np.eye(matrix.shape[1])
        user_vector = np.linalg.solve(matrix.T @ matrix + regularization, matrix.T @ targets)

    preferred_genres: dict[str, list[float]] = {}
    high_rated_titles: dict[str, list[str]] = {}
    for rating in payload.ratings:
        movie = by_id[rating.movie_id]
        if rating.rating >= 4:
            for genre_name in movie["genres"]:
                preferred_genres.setdefault(genre_name, []).append(rating.rating)
                high_rated_titles.setdefault(genre_name, []).append(movie["title"])
    genre_preferences = {key: sum(values) / len(values) for key, values in preferred_genres.items()}

    candidates = []
    for movie in catalog:
        movie_id = movie["movie_id"]
        if movie_id in rated_ids:
            continue
        factor = factors.get(str(movie_id))
        if user_vector is not None and factor is not None:
            score = float(np.dot(user_vector, np.asarray(factor, dtype=np.float64)))
            method = "als"
        else:
            genre_scores = [genre_preferences[name] for name in movie["genres"] if name in genre_preferences]
            score = sum(genre_scores) / len(genre_scores) if genre_scores else movie["mean"]
            method = "genre" if genre_scores else "popular"
        candidates.append((score, movie, method))
    candidates.sort(key=lambda row: (-row[0], -row[1]["count"], row[1]["title"].casefold()))

    output = []
    for score, movie, method in candidates[: payload.limit]:
        estimated = min(5.0, max(0.5, score))
        shared = [name for name in movie["genres"] if name in genre_preferences]
        if shared:
            source_titles = sorted({title for name in shared for title in high_rated_titles[name]})
            reason = f"Shares {', '.join(shared)} with movies you rated highly, including {source_titles[0]}."
        elif method == "als":
            reason = "Ranked by rating patterns in the Spark ALS model."
        else:
            reason = "Popular among movies in the MovieLens training data."
        output.append(
            Recommendation(
                movie_id=movie["movie_id"],
                title=movie["title"],
                genres=movie["genres"],
                estimated_rating=round(estimated, 2),
                reason=reason,
            )
        )
    return output
