"""Download the MovieLens Latest Small development dataset."""

from __future__ import annotations

import csv
import io
import urllib.request
import zipfile
from pathlib import Path

URL = "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip"
DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
REQUIRED_COLUMNS = {
    "movies.csv": {"movieId", "title", "genres"},
    "ratings.csv": {"userId", "movieId", "rating", "timestamp"},
    "tags.csv": {"userId", "movieId", "tag", "timestamp"},
    "links.csv": {"movieId", "imdbId", "tmdbId"},
}


def main() -> None:
    request = urllib.request.Request(URL, headers={"User-Agent": "movie-recommendation-learning-project"})
    with urllib.request.urlopen(request, timeout=60) as response:
        archive_bytes = response.read()

    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        names = {Path(name).name: name for name in archive.namelist()}
        missing = REQUIRED_COLUMNS.keys() - names.keys()
        if missing:
            raise ValueError(f"MovieLens archive is missing expected files: {', '.join(sorted(missing))}")

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        for filename, columns in REQUIRED_COLUMNS.items():
            contents = archive.read(names[filename])
            header = next(csv.reader(io.StringIO(contents.decode("utf-8-sig"))), [])
            if not columns.issubset(header):
                raise ValueError(f"Unexpected {filename} schema: {header}")
            (DATA_DIR / filename).write_bytes(contents)
            print(f"Saved {DATA_DIR / filename}")


if __name__ == "__main__":
    main()
