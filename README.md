# Reel Good — Movie Recommendation Engine

A small interactive movie discovery demo built with MovieLens, Spark ALS, MLflow, FastAPI, and Next.js. Search the catalog, rate films in the current browser session, and get a ranked watchlist from a trained model.

This is an educational, non-commercial demo. Recommendations and estimated ratings are examples, not guarantees. MovieLens Latest Small is a development dataset, not a research benchmark. The public app serves a compact model export; Spark training and MLflow tracking run locally.

## How it works

The browser sends films and ratings to the API. FastAPI estimates a temporary user vector from the selected ratings and the ALS model's learned movie vectors, then ranks unseen movies. With no ratings, the app shows popular films from the training data. Ratings stay in browser memory and are not stored in an account or database.

The API provides a short explanation for each suggestion. Genre overlap is shown when a recommended film shares a genre with a highly rated film; otherwise, the explanation describes the ALS ranking. Estimated ratings are rough model outputs, not confidence scores.

## Run locally

### Download data and train the model

The data, MLflow database, and generated model files stay local and are ignored by Git. Docker Compose supplies Java, Spark, and the pinned Python environment:

```bash
python3 scripts/download_data.py
make mlflow-ui
make train-compose
```

Open MLflow at <http://127.0.0.1:5001>. The API reads the exported model from `artifacts/recommender-v1/serving.json`.

### Start the API

```bash
make api-install
make api-test
make api-run
```

The API is at <http://localhost:8000>; interactive API documentation is at <http://localhost:8000/docs>.

### Start the web app

In another terminal:

```bash
cd web
npm ci
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev
```

Open <http://localhost:3000>, search or filter the catalog, rate films from 1 to 5, and select **Find my next film**. Ratings last only while the page is open.

Web checks: `npm run typecheck`, `npm run test:ui`, and `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run build` (run from `web/`). The browser smoke test stubs the API, so CI does not need MovieLens data or a trained model.

## Project map

```text
api/       FastAPI catalog and recommendation endpoints, contract tests
ml/        genre baseline, chronological evaluation, Spark ALS, MLflow logging
web/       Next.js movie discovery, rating, and recommendation interface
scripts/   MovieLens downloader and compact deployment artifact packager
infra/     local Docker Compose services and Spark training image
docs/      dataset, evaluation, results, training, and publishing notes
```

See [docs/DATASET.md](docs/DATASET.md) for the data source and its terms, [docs/EVALUATION.md](docs/EVALUATION.md) and [docs/EXPERIMENT_RESULTS.md](docs/EXPERIMENT_RESULTS.md) for methodology and results, and [docs/DOCKER_TRAINING.md](docs/DOCKER_TRAINING.md) for the training workflow.

## Publish

The repository includes a Render Blueprint for a lightweight API and static web app. The Blueprint has not been deployed. Read [docs/PUBLISHING.md](docs/PUBLISHING.md) before deployment; it explains how to prepare the model as a secret file without committing it.

MovieLens use conditions are documented in [docs/DATASET.md](docs/DATASET.md). Acknowledge GroupLens when sharing results, do not imply endorsement, and obtain permission before any commercial or revenue-bearing use.
