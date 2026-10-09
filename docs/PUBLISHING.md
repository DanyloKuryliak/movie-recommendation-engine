# Publish the Movie Recommendation demo

## What gets published

Render serves a static Next.js site and a lightweight FastAPI process. Spark and MLflow are used locally to train and evaluate the model; neither is part of the public runtime. The public API loads a compact model file on startup. It does not use PostgreSQL, Redis, user accounts, or a rating database.

The MovieLens data and model file are ignored by Git. Before deploying, add the compact model as a Render secret file rather than committing it.

## Prepare the model file

From the repository root, train or refresh the model and create its deployment package:

```bash
make train-compose
make package-public-model
```

This creates:

```text
artifacts/recommender-v1/serving.json.gz.b64
```

The package contains the movie catalog and rounded ALS movie factors. It is gzip-compressed and base64-encoded so the deployment file stays below Render's current 1 MB combined secret-file limit. It remains ignored by Git.

## Create the Render services

1. Push the project to a Git provider and connect that repository to Render.
2. Create a Blueprint and select `render.yaml` as its Blueprint path.
3. Review the two planned resources: `movie-recommendation-api` and `movie-recommendation-web`.
4. Before the first deploy, open the API service's **Environment → Secret Files** and upload the generated file with the exact name `recommender-artifact.json.gz.b64`.
5. Deploy the Blueprint. The API's health check loads the model; the static site is built with the API URL configured in the Blueprint.
6. Open the public web URL, rate several films, request recommendations, and check the API's `/health` and `/docs` endpoints.

Render makes secret files available at `/etc/secrets/<filename>`. The API Blueprint is configured to load `/etc/secrets/recommender-artifact.json.gz.b64`. Render secret files have a 1 MB combined limit, so regenerate and check the packaged model size before replacing it. See [Render's secret-file instructions](https://render.com/docs/configure-environment-variables#secret-files) and [Blueprint reference](https://render.com/docs/blueprint-spec).

## Acceptance checklist

- API tests pass, including model-backed ranking, unknown/duplicate rating validation, catalog search, and CORS.
- The Next.js type check and static production build pass.
- The exported artifact loads and can return both popularity-based and personalized recommendations.
- The generated deployment artifact and raw MovieLens data remain untracked and ignored.
- After deployment, record both public URLs, the deployed commit SHA, and smoke-check results here.

## Dataset use

This is an educational, non-commercial demo. GroupLens describes MovieLens Latest Small as a development dataset and sets conditions for acknowledgement, redistribution, and commercial or revenue-bearing use. Read [the recorded dataset decision](DATASET.md) and the [GroupLens terms](https://files.grouplens.org/datasets/movielens/ml-latest-small-README.html) before publishing or changing how the project is used. Do not imply that GroupLens or the University of Minnesota endorses this app.

## Deployment record

Not deployed yet. Add the service URLs, deployed commit, and live smoke-check evidence after the Blueprint is reviewed and deployed.

## Local pre-publish check record — 2026-10-09

- `make train-compose` completed; latest run `961b078b5588450d9865d6cb3445773e` logged in MLflow.
- `make package-public-model` produced a 733,196-byte model package.
- `make api-test`: 10 passed. FastAPI's test client printed a Starlette/httpx deprecation warning; it did not affect the checks.
- `npm ci`, `npm run typecheck`, `npm run test:ui`, and `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run build` completed successfully.
- The production static build was served locally and exercised against the real API and model; search, rating, and recommendation succeeded. A 375-pixel viewport had no horizontal overflow.
- The compressed deployment artifact loaded through the API, and the catalog contained 9,742 movies.
- Docker Compose and Render YAML syntax parsed. Render's own Blueprint validator and the public deployment have not been run.

## Standalone repository checks — 2026-10-09

- From the repository root, `make api-test` passed (10 tests).
- From `web/`, typecheck, the Playwright UI smoke test (1 test), and the static production build passed.
- `docker compose --env-file .env.example -f infra/compose.local.yaml --profile training config -q` passed.
- GitHub Actions has been configured, but its first hosted run will happen after publication.
