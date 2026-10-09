# Dataset decision

## Source

Use GroupLens **MovieLens Latest Small** for this educational project. The archive is available at <https://files.grouplens.org/datasets/movielens/ml-latest-small.zip> and contains roughly 100,000 ratings, 9,000 movies, and 600 users. GroupLens describes it as a development dataset, not a fixed research benchmark.

The data is not committed to this repository. Download it locally with:

```bash
python3 scripts/download_data.py
```

The script checks that the archive contains the expected files and CSV columns before saving them under `data/raw/`.

## Files and schema

| File | Columns | Use |
| --- | --- | --- |
| `movies.csv` | `movieId`, `title`, `genres` | Catalog and simple content features |
| `ratings.csv` | `userId`, `movieId`, `rating`, `timestamp` | Training and offline evaluation |
| `tags.csv` | `userId`, `movieId`, `tag`, `timestamp` | Optional movie descriptions |
| `links.csv` | `movieId`, `imdbId`, `tmdbId` | External movie identifiers; do not fetch external metadata without checking its terms |

## Usage terms

GroupLens allows research use under its stated conditions. Do not imply endorsement by the University of Minnesota or GroupLens, acknowledge the dataset when publishing results, and do not use it commercially or for revenue-bearing purposes without permission. The dataset README also says redistribution must retain these conditions. We therefore keep the download out of Git and link to the source rather than bundling it.

Source details and full terms: <https://files.grouplens.org/datasets/movielens/ml-latest-small-README.html>.
