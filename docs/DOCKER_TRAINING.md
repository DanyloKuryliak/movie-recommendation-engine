# Run Spark training and MLflow with Docker Compose

## Goal

The trainer and MLflow server run in separate containers. The trainer reads the existing MovieLens files from a read-only host mount, runs Spark locally inside its container, and sends experiment data to MLflow over the Compose network. MLflow stores its database and artifacts in the project's ignored `data/experiments/` directory; the small serving artifact is written to the ignored `artifacts/` directory.

## Run it

```bash
make mlflow-ui
make train-compose
```

Open `http://127.0.0.1:5001` to see the new `genre-vs-spark-als` run. Stop the MLflow container with `make mlflow-ui-down`.

The first command builds the shared training image, starts MLflow, and waits for its health check. The second runs a one-time trainer container; Compose waits for MLflow to become healthy, then the trainer connects to it by service name (`mlflow`) and exits after logging the run. The two services share the same image so their Python, Spark, and MLflow versions match.

## Acceptance check

- Compose validates the service definitions.
- The MLflow container becomes healthy and its local-only page returns HTTP 200.
- The trainer exits successfully and a new run with metrics and model artifacts appears in the MLflow page.
- The MovieLens input mount remains read-only; generated experiment and serving files remain local and ignored by Git.

The Compose MLflow database is `data/experiments/mlflow-compose.db`, separate from the earlier host-run database. Java is installed in the training image, so this workflow does not depend on Java installed on the host.
