# Security Policy

## Reporting a Vulnerability

If you discover a security issue in MatAI, please open a private security advisory on GitHub or contact the maintainer directly.

Please do not include real credentials, proprietary datasets, or confidential experimental data in public issues.

## Data Handling

MatAI is designed for local-first prediction table review. Users should not commit the following to the repository:

- AWS credentials
- `.env` files
- production prediction tables
- proprietary experimental datasets
- confidential material candidate information

## Supported Versions

MatAI is currently an early-stage project. Security fixes will be applied to the main branch until formal versioned releases are introduced.

## Scope

Security-relevant areas include:

- S3 ingestion
- local file handling
- raw-to-Parquet conversion
- API endpoints
- environment variable handling
- web UI input handling
