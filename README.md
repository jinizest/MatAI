# MatAI: Local AI Prediction Viewer for Materials R&D

MatAI is an open-source, privacy-conscious platform for turning machine-learning prediction tables into searchable candidate-review workflows for advanced materials R&D.

It is designed for scientists and engineers who need to inspect, rank, and operationalize ML prediction outputs locally without deploying a heavy data warehouse or sending sensitive experimental data to external services.

The initial use case focuses on advanced semiconductor materials such as EUV photoresists and metal oxide resist candidate screening, but the architecture is general enough for chemistry, materials informatics, and industrial R&D prediction workflows.

## Why MatAI?

Modern materials R&D increasingly uses machine learning to screen large candidate spaces. However, many industrial teams face a practical gap:

* ML predictions are often produced as CSV, Excel, or other table outputs.
* Sensitive experimental data cannot be freely uploaded to external services.
* Researchers need a lightweight way to filter, rank, and review candidates.
* Full data warehouse or MLOps platforms are often too heavy for small internal tools.
* Domain experts need readable workflows, not only notebooks.

MatAI addresses this gap by providing a small, local-first application pattern:

```text
S3 prediction table
        ↓
local raw snapshot
        ↓
canonical Parquet conversion
        ↓
DuckDB analytical query layer
        ↓
Flask API and candidate-review UI
```

## Core Features

* Download the latest prediction table from S3.
* Store the raw prediction table locally for traceability.
* Convert raw CSV, Excel, JSON, or Parquet inputs into a canonical Parquet snapshot.
* Query prediction outputs locally with DuckDB.
* Provide a lightweight Flask API and web UI for candidate screening.
* Filter candidates by target thresholds such as EOP, IPU, and process margin.
* Keep all query serving local and privacy-conscious.
* Use dummy sample data for open-source demonstration.

## Current Example Workflow

The current demo includes a dummy prediction table for a materials-screening workflow.

```text
data/raw/latest_prediction.csv
        ↓
data/processed/mor_predictions_latest.parquet
        ↓
DuckDB read_parquet()
        ↓
Flask web page and API
```

The sample data is synthetic and does not contain confidential experimental or company data.

## Repository Structure

```text
MatAI/
  app.py
  db.py
  updater.py
  refresh_once.py
  rebuild_local_once.py
  make_sample_data.py
  requirements.txt
  .env.example
  README.md
  templates/
    index.html
  data/
    raw/
      latest_prediction.csv
    processed/
      mor_predictions_latest.parquet
      mor_predictions_meta.json
```

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app app run --debug --no-reload
```

For Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
flask --app app run --debug --no-reload
```

Open the local web UI:

```text
http://127.0.0.1:5000
```

## Regenerate Local Sample Data

```bash
python make_sample_data.py
```

## Rebuild Local Parquet Snapshot

```bash
python rebuild_local_once.py
```

You can also rebuild the local Parquet snapshot from the web UI.

## Configure S3 Ingestion

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env`:

```bash
AWS_REGION=ap-northeast-2
AWS_PROFILE=your-profile
S3_BUCKET=your-bucket-name
S3_KEY=ml-output/latest_prediction.csv

RAW_DIR=data/raw
PROCESSED_PARQUET_PATH=data/processed/mor_predictions_latest.parquet
LOCAL_META_PATH=data/processed/mor_predictions_meta.json

ENABLE_SCHEDULER=1
SCHEDULER_TIMEZONE=Asia/Seoul
```

Run a one-time S3 refresh:

```bash
python refresh_once.py
```

## API Endpoints

Health check:

```text
GET /api/health
```

Metadata and data summary:

```text
GET /api/meta
```

Candidate query:

```text
GET /api/candidates?eop_max=1.0&ipu_max=1.0&margin_min=1.0&limit=100&sort=eop_asc
```

Manual S3 refresh:

```text
POST /api/admin/refresh
```

Local raw-to-Parquet rebuild:

```text
POST /api/admin/rebuild-local
```

## Deployment Example

```bash
gunicorn -w 1 --threads 4 -b 0.0.0.0:8000 "app:create_app()"
```

When using the built-in scheduler, a single worker is recommended to avoid duplicate scheduled jobs.

For production systems, the recommended architecture is to separate the web server from the scheduled ingestion job:

```text
Flask server
  └── query and review UI

Cron, Kubernetes CronJob, or Airflow
  └── scheduled S3 download and Parquet conversion
```

## Privacy and Security Principles

MatAI is designed around local-first and privacy-conscious operation.

* Prediction tables are downloaded into a local environment.
* Query serving is performed through local DuckDB execution.
* No sample data in this repository contains proprietary experimental data.
* Secrets should be stored in `.env` or an external secret manager.
* Real S3 credentials, raw experimental data, and production prediction outputs should not be committed to GitHub.

## Roadmap

* Add schema validation for prediction tables.
* Add configurable column mapping through YAML.
* Add candidate tagging and review status storage.
* Add SQLite or PostgreSQL integration for review metadata.
* Add automated tests for ingestion, conversion, and query logic.
* Add GitHub Actions for linting and test execution.
* Add Docker and Docker Compose examples.
* Add deployment examples for internal R&D environments.
* Add documentation for materials informatics workflows beyond the initial EUV resist example.
* Add Codex-assisted maintainer workflows for issue triage, PR review, and documentation updates.

## Intended Users

MatAI is intended for:

* Materials informatics researchers
* Semiconductor materials engineers
* Chemistry and formulation scientists
* R&D teams operationalizing ML prediction outputs
* Engineers building lightweight internal AI tools
* Open-source contributors interested in local-first scientific software

## Contributing

Contributions are welcome. Good first contributions include:

* Improving documentation
* Adding test cases
* Supporting additional input formats
* Improving schema validation
* Adding UI filters
* Adding deployment examples
* Hardening S3 and local file handling

## License

This project is released under the MIT License.

## Project Status

MatAI is an early-stage open-source project. The current implementation demonstrates the core workflow and will be expanded toward a more robust, contributor-ready platform for local AI prediction review in materials R&D.
