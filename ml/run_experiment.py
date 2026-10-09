"""Compare a genre profile with Spark ALS and record one MLflow run."""

from __future__ import annotations

import csv
import json
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import mlflow
import numpy as np
from pyspark.ml.recommendation import ALS
from pyspark.sql import SparkSession
from pyspark.sql.types import FloatType, IntegerType, StructField, StructType

from recommendation import chronological_split, evaluate_rankings, genre_recommendations, load_dataset

PROJECT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_DIR / "data" / "raw"
EXPERIMENT_DIR = PROJECT_DIR / "data" / "experiments"
SERVING_DIR = PROJECT_DIR / "artifacts" / "recommender-v1"
SPARK_MODEL_DIR = EXPERIMENT_DIR / "spark_als_model"
RANK = 16
MAX_ITER = 10
REG_PARAM = 0.1
SEED = 42
TOP_K = 10


def als_recommendations(model, train_rows, users: list[int], limit: int = TOP_K) -> tuple[dict[int, list[int]], dict[str, list[float]]]:
    """Score catalog movies from Spark's learned factors, excluding seen titles."""
    user_rows = model.userFactors.collect()
    item_rows = model.itemFactors.collect()
    user_ids = [int(row.id) for row in user_rows]
    item_ids = [int(row.id) for row in item_rows]
    user_matrix = np.asarray([row.features for row in user_rows], dtype=np.float32)
    item_matrix = np.asarray([row.features for row in item_rows], dtype=np.float32)
    scores = user_matrix @ item_matrix.T

    seen: dict[int, set[int]] = {user_id: set() for user_id in users}
    for row in train_rows:
        seen[int(row["user_id"])].add(int(row["movie_id"]))
    user_positions = {user_id: index for index, user_id in enumerate(user_ids)}

    rankings = {user_id: [] for user_id in users}
    for user_id in users:
        if user_id not in user_positions:
            continue
        row_scores = scores[user_positions[user_id]].copy()
        for index, movie_id in enumerate(item_ids):
            if movie_id in seen[user_id]:
                row_scores[index] = -np.inf
        order = np.lexsort((np.asarray(item_ids), -row_scores))[:limit]
        rankings[user_id] = [item_ids[index] for index in order if np.isfinite(row_scores[index])]

    exported_factors = {str(movie_id): item_matrix[index].astype(float).tolist() for index, movie_id in enumerate(item_ids)}
    return rankings, exported_factors


def main() -> None:
    movies, ratings = load_dataset(DATA_DIR)
    train_rows, test_rows = chronological_split(ratings)
    users = sorted({int(row["user_id"]) for row in train_rows})
    print(f"Loaded {len(movies):,} movies and {len(ratings):,} ratings")
    print(f"Time split: {len(train_rows):,} training ratings, {len(test_rows):,} held-out ratings, {len(users):,} users")

    genre_rankings = genre_recommendations(movies, train_rows, users, TOP_K)
    genre_metrics = evaluate_rankings(genre_rankings, test_rows, TOP_K)
    print(f"Genre baseline: {json.dumps(genre_metrics, sort_keys=True)}")
    EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)

    spark = (
        SparkSession.builder.appName("movie-recommendation-als")
        .master("local[2]")
        .config("spark.ui.enabled", "false")
        .config("spark.pyspark.python", sys.executable)
        .config("spark.pyspark.driver.python", sys.executable)
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    try:
        schema = StructType(
            [
                StructField("user_id", IntegerType(), nullable=False),
                StructField("movie_id", IntegerType(), nullable=False),
                StructField("rating", FloatType(), nullable=False),
            ]
        )
        with tempfile.TemporaryDirectory(prefix="ratings-", dir=EXPERIMENT_DIR) as temp_dir:
            training_csv = Path(temp_dir) / "training.csv"
            with training_csv.open("w", encoding="utf-8", newline="") as file:
                writer = csv.writer(file)
                writer.writerows(
                    (int(row["user_id"]), int(row["movie_id"]), float(row["rating"])) for row in train_rows
                )
            training_data = spark.read.schema(schema).csv(str(training_csv))
            als = ALS(
                userCol="user_id",
                itemCol="movie_id",
                ratingCol="rating",
                rank=RANK,
                maxIter=MAX_ITER,
                regParam=REG_PARAM,
                seed=SEED,
                coldStartStrategy="nan",
            )
            model = als.fit(training_data)
            als_rankings, item_factors = als_recommendations(model, train_rows, users, TOP_K)
            als_metrics = evaluate_rankings(als_rankings, test_rows, TOP_K)
            model.write().overwrite().save(str(SPARK_MODEL_DIR))
    finally:
        spark.stop()

    print(f"Spark ALS: {json.dumps(als_metrics, sort_keys=True)}")
    SERVING_DIR.mkdir(parents=True, exist_ok=True)
    serving_artifact = {
        "version": "recommender-v1",
        "model": "Spark ALS",
        "rank": RANK,
        "item_factors": item_factors,
        "movies": {str(movie_id): movie for movie_id, movie in movies.items()},
        "popularity": {
            str(movie_id): {
                "count": len(values),
                "mean": sum(values) / len(values),
            }
            for movie_id, values in _training_ratings_by_movie(train_rows).items()
        },
    }
    serving_path = SERVING_DIR / "serving.json"
    serving_path.write_text(json.dumps(serving_artifact, separators=(",", ":")), encoding="utf-8")

    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI")
    if not tracking_uri:
        tracking_uri = f"sqlite:///{(EXPERIMENT_DIR / 'mlflow.db').resolve()}"
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("movie-recommendation")
    with mlflow.start_run(run_name="genre-vs-spark-als") as run:
        mlflow.set_tags({"dataset": "MovieLens Latest Small", "split": "per-user chronological 80/20"})
        mlflow.log_params(
            {
                "als_rank": RANK,
                "als_max_iter": MAX_ITER,
                "als_reg_param": REG_PARAM,
                "seed": SEED,
                "holdout_fraction": 0.2,
                "relevance_threshold": 4.0,
                "top_k": TOP_K,
                "training_ratings": len(train_rows),
                "heldout_ratings": len(test_rows),
            }
        )
        mlflow.log_metrics({f"genre_{key}": value for key, value in genre_metrics.items()})
        mlflow.log_metrics({f"als_{key}": value for key, value in als_metrics.items()})
        mlflow.log_artifact(str(serving_path), artifact_path="serving")

        mlflow.log_artifacts(str(SPARK_MODEL_DIR), artifact_path="spark_als_model")

        results = {
            "run_id": run.info.run_id,
            "created_at_utc": datetime.now(UTC).isoformat(),
            "dataset": "MovieLens Latest Small",
            "split": "per-user chronological 80/20; relevant means rating >= 4.0",
            "training_ratings": len(train_rows),
            "heldout_ratings": len(test_rows),
            "genre_baseline": genre_metrics,
            "spark_als": als_metrics,
            "serving_artifact": str(serving_path.relative_to(PROJECT_DIR)),
        }
        results_path = EXPERIMENT_DIR / "latest_results.json"
        results_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
        mlflow.log_artifact(str(results_path), artifact_path="evaluation")

    print(f"MLflow run: {run.info.run_id}")
    print(f"Serving artifact: {serving_path}")
    print(f"Results: {EXPERIMENT_DIR / 'latest_results.json'}")


def _training_ratings_by_movie(rows: list[dict[str, float | int]]) -> dict[int, list[float]]:
    grouped: dict[int, list[float]] = {}
    for row in rows:
        grouped.setdefault(int(row["movie_id"]), []).append(float(row["rating"]))
    return grouped


if __name__ == "__main__":
    main()
