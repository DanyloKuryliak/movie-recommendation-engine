"""Small, readable helpers for the offline recommendation experiment."""

from __future__ import annotations

import csv
import math
from collections import Counter, defaultdict
from pathlib import Path


def load_dataset(data_dir: Path) -> tuple[dict[int, dict[str, object]], list[dict[str, float | int]]]:
    with (data_dir / "movies.csv").open(encoding="utf-8-sig", newline="") as file:
        movies = {
            int(row["movieId"]): {
                "title": row["title"],
                "genres": [] if row["genres"] == "(no genres listed)" else row["genres"].split("|"),
            }
            for row in csv.DictReader(file)
        }

    with (data_dir / "ratings.csv").open(encoding="utf-8-sig", newline="") as file:
        ratings = [
            {
                "user_id": int(row["userId"]),
                "movie_id": int(row["movieId"]),
                "rating": float(row["rating"]),
                "timestamp": int(row["timestamp"]),
            }
            for row in csv.DictReader(file)
        ]
    return movies, ratings


def chronological_split(
    ratings: list[dict[str, float | int]], holdout_fraction: float = 0.2
) -> tuple[list[dict[str, float | int]], list[dict[str, float | int]]]:
    """Keep each user's latest ratings for testing and earlier ratings for training."""
    by_user: dict[int, list[dict[str, float | int]]] = defaultdict(list)
    for row in ratings:
        by_user[int(row["user_id"])].append(row)

    train, test = [], []
    for user_ratings in by_user.values():
        if len(user_ratings) < 5:
            continue
        user_ratings.sort(key=lambda row: (int(row["timestamp"]), int(row["movie_id"])))
        split_at = min(max(1, math.floor(len(user_ratings) * (1 - holdout_fraction))), len(user_ratings) - 1)
        train.extend(user_ratings[:split_at])
        test.extend(user_ratings[split_at:])
    if not train or not test:
        raise ValueError("The dataset did not produce non-empty train and test splits")
    return train, test


def genre_recommendations(
    movies: dict[int, dict[str, object]],
    train: list[dict[str, float | int]],
    users: list[int],
    limit: int = 10,
) -> dict[int, list[int]]:
    """Rank unseen titles by the user's average training rating for their genres."""
    user_genre_ratings: dict[int, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    positive_popularity: Counter[int] = Counter()
    rated_by_user: dict[int, set[int]] = defaultdict(set)

    for row in train:
        user_id = int(row["user_id"])
        movie_id = int(row["movie_id"])
        rating = float(row["rating"])
        rated_by_user[user_id].add(movie_id)
        if rating >= 4.0:
            positive_popularity[movie_id] += 1
        for genre in movies[movie_id]["genres"]:
            user_genre_ratings[user_id][genre].append(rating)

    profiles = {
        user_id: {genre: sum(values) / len(values) for genre, values in genre_values.items()}
        for user_id, genre_values in user_genre_ratings.items()
    }

    rankings = {}
    for user_id in users:
        profile = profiles.get(user_id, {})
        candidates = []
        for movie_id, movie in movies.items():
            if movie_id in rated_by_user[user_id]:
                continue
            known_preferences = [profile[g] for g in movie["genres"] if g in profile]
            genre_score = sum(known_preferences) / len(known_preferences) if known_preferences else 0.0
            candidates.append((genre_score, positive_popularity[movie_id], movie_id))
        candidates.sort(key=lambda item: (-item[0], -item[1], item[2]))
        rankings[user_id] = [movie_id for _, _, movie_id in candidates[:limit]]
    return rankings


def evaluate_rankings(
    recommendations: dict[int, list[int]],
    test: list[dict[str, float | int]],
    limit: int = 10,
) -> dict[str, float | int]:
    """Calculate macro top-k precision, recall, and binary NDCG."""
    relevant_by_user: dict[int, set[int]] = defaultdict(set)
    for row in test:
        if float(row["rating"]) >= 4.0:
            relevant_by_user[int(row["user_id"])].add(int(row["movie_id"]))

    evaluated_users = [user_id for user_id in recommendations if relevant_by_user[user_id]]
    if not evaluated_users:
        raise ValueError("No users have a relevant held-out rating (rating >= 4.0)")

    precisions, recalls, ndcgs = [], [], []
    short_lists = 0
    for user_id in evaluated_users:
        ranked = recommendations[user_id][:limit]
        relevant = relevant_by_user[user_id]
        hits = [1 if movie_id in relevant else 0 for movie_id in ranked]
        precisions.append(sum(hits) / limit)
        recalls.append(sum(hits) / len(relevant))
        dcg = sum(hit / math.log2(position + 2) for position, hit in enumerate(hits))
        ideal_hits = min(len(relevant), limit)
        ideal_dcg = sum(1 / math.log2(position + 2) for position in range(ideal_hits))
        ndcgs.append(dcg / ideal_dcg if ideal_dcg else 0.0)
        short_lists += len(ranked) < limit

    return {
        "precision_at_10": sum(precisions) / len(precisions),
        "recall_at_10": sum(recalls) / len(recalls),
        "ndcg_at_10": sum(ndcgs) / len(ndcgs),
        "evaluated_users": len(evaluated_users),
        "users_with_short_lists": short_lists,
    }
