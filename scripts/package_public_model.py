"""Create a compact base64/gzip artifact suitable for a deployment secret file."""

from __future__ import annotations

import base64
import gzip
import json
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
SOURCE = PROJECT_DIR / "artifacts" / "recommender-v1" / "serving.json"
DESTINATION = PROJECT_DIR / "artifacts" / "recommender-v1" / "serving.json.gz.b64"


def main() -> None:
    artifact = json.loads(SOURCE.read_text(encoding="utf-8"))
    artifact["item_factors"] = {
        movie_id: [round(value, 4) for value in factors]
        for movie_id, factors in artifact["item_factors"].items()
    }
    compact = json.dumps(artifact, separators=(",", ":")).encode("utf-8")
    encoded = base64.b64encode(gzip.compress(compact, compresslevel=9, mtime=0))
    DESTINATION.write_bytes(encoded)
    print(f"Wrote {DESTINATION.relative_to(PROJECT_DIR)} ({len(encoded):,} bytes)")


if __name__ == "__main__":
    main()
