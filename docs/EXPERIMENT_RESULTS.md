# First model comparison

Initial host run: `608f9449ca8b46f68c1f3eceef13540a`
Latest Docker Compose run: `961b078b5588450d9865d6cb3445773e`
Dataset: MovieLens Latest Small
Split: each user's earlier 80% of ratings for training and latest 20% for testing; a held-out rating of 4.0 or higher counts as relevant.
Users scored: 592, out of 610 users with training history.

Spark ALS used explicit rating values with rank 16, 10 training iterations, regularization 0.1, and seed 42. Its learned movie vectors are exported in `artifacts/recommender-v1/serving.json`; the API can use those vectors later without starting Spark. The full Spark model and all settings are also stored in MLflow.

| Recommender | Precision@10 | Recall@10 | NDCG@10 |
| --- | ---: | ---: | ---: |
| Genre preference baseline | 0.0041 | 0.0037 | 0.0057 |
| Spark ALS | 0.0071 | 0.0055 | 0.0073 |

ALS ranked relevant held-out movies somewhat better than the genre baseline in this run. The absolute precision difference is about 0.003, or roughly 0.03 additional relevant movies per user's ten suggestions on average. Both scores are low, so this is an initial learning result, not evidence that the recommendations are useful in practice.

The result is one chronological split on GroupLens's development dataset. It is not a fixed research benchmark and should not be generalized to other users or future movie catalogs. The raw data, MLflow database, native Spark model, and compact `recommender-v1` serving artifact are local ignored files. MLflow records the run settings, metrics, Spark model files, evaluation JSON, and serving artifact.

The Docker Compose run used the same split and produced the same rounded metrics. Spark ran inside the one-off `trainer` container; MLflow stayed up as a separate `mlflow` container at `http://127.0.0.1:5001`.
