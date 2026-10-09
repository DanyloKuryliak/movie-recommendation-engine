# Recommendation experiment rules

We compare the genre baseline and Spark ALS on the same users, training rows, candidate movies, and held-out ratings.

## Split

- Sort each user's ratings by `timestamp`, then `movieId` to break ties consistently.
- Keep users with at least five ratings. For each, use the latest 20% of ratings as holdout and the earlier ratings for training.
- Use only training rows to build recommendations. A movie is relevant in the holdout when its rating is at least 4.0.
- Exclude every movie already rated in training from both recommenders' candidates.

This tests whether the system can recommend something a known user later liked. It does not test recommendations for brand-new users.

## Measures

We report macro-averaged top-10 metrics across users:

- **Precision@10:** share of the ten suggestions that the user later rated at least 4.0.
- **Recall@10:** share of the user's relevant held-out movies that appear in the ten suggestions.
- **NDCG@10:** rewards relevant movies more when they appear nearer the top.

We also report how many users had at least one relevant held-out movie and how many users received fewer than ten unseen candidates. That makes small denominators or incomplete lists visible.

The genre baseline learns each user's genre preferences from training ratings and falls back to training-set popularity when the user has no usable genre signal. Spark ALS learns user and movie factors from training ratings. Both use a fixed seed and the exact same holdout and ranking measures.
