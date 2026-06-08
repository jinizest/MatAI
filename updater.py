import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import boto3
import duckdb
import pandas as pd


CANONICAL_COLUMNS = [
    "sample_id",
    "precursor_set",
    "solvent",
    "ul",
    "pred_eop",
    "pred_ipu",
    "pred_margin",
    "model_version",
]


COLUMN_MAPPING = {
    "sample_id": "sample_id",
    "Sample ID": "sample_id",
    "SAMPLE_ID": "sample_id",
    "precursor_set": "precursor_set",
    "Precursor Set": "precursor_set",
    "solvent": "solvent",
    "Solvent": "solvent",
    "ul": "ul",
    "UL": "ul",
    "pred_eop": "pred_eop",
    "Pred EOP": "pred_eop",
    "predicted_eop": "pred_eop",
    "pred_ipu": "pred_ipu",
    "Pred IPU": "pred_ipu",
    "predicted_ipu": "pred_ipu",
    "pred_margin": "pred_margin",
    "Pred Margin": "pred_margin",
    "pred_defect_margin": "pred_margin",
    "model_version": "model_version",
    "Model Version": "model_version",
}


def sql_str(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def make_boto3_client(region_name: str, profile_name: str | None = None):
    session_kwargs = {}
    if profile_name:
        session_kwargs["profile_name"] = profile_name
    session = boto3.Session(**session_kwargs)
    return session.client("s3", region_name=region_name)


def normalize_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns=COLUMN_MAPPING)

    missing = [col for col in CANONICAL_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df[CANONICAL_COLUMNS].copy()
    for col in ["sample_id", "precursor_set", "solvent", "ul", "model_version"]:
        df[col] = df[col].astype(str)

    for col in ["pred_eop", "pred_ipu", "pred_margin"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["pred_eop", "pred_ipu", "pred_margin"])
    return df


def convert_csv_to_parquet(raw_path: Path, parquet_path: Path):
    con = duckdb.connect(":memory:")
    try:
        con.execute(
            f"""
            COPY (
                SELECT
                    CAST(sample_id AS VARCHAR) AS sample_id,
                    CAST(precursor_set AS VARCHAR) AS precursor_set,
                    CAST(solvent AS VARCHAR) AS solvent,
                    CAST(ul AS VARCHAR) AS ul,
                    CAST(pred_eop AS DOUBLE) AS pred_eop,
                    CAST(pred_ipu AS DOUBLE) AS pred_ipu,
                    CAST(pred_margin AS DOUBLE) AS pred_margin,
                    CAST(model_version AS VARCHAR) AS model_version
                FROM read_csv_auto({sql_str(str(raw_path))}, header = true)
                WHERE pred_eop IS NOT NULL
                  AND pred_ipu IS NOT NULL
                  AND pred_margin IS NOT NULL
            )
            TO {sql_str(str(parquet_path))}
            (FORMAT PARQUET, COMPRESSION ZSTD)
            """
        )
    finally:
        con.close()


def convert_excel_to_parquet(raw_path: Path, parquet_path: Path):
    df = pd.read_excel(raw_path)
    df = normalize_dataframe_columns(df)
    df.to_parquet(parquet_path, index=False)


def convert_json_to_parquet(raw_path: Path, parquet_path: Path):
    con = duckdb.connect(":memory:")
    try:
        con.execute(
            f"""
            COPY (
                SELECT
                    CAST(sample_id AS VARCHAR) AS sample_id,
                    CAST(precursor_set AS VARCHAR) AS precursor_set,
                    CAST(solvent AS VARCHAR) AS solvent,
                    CAST(ul AS VARCHAR) AS ul,
                    CAST(pred_eop AS DOUBLE) AS pred_eop,
                    CAST(pred_ipu AS DOUBLE) AS pred_ipu,
                    CAST(pred_margin AS DOUBLE) AS pred_margin,
                    CAST(model_version AS VARCHAR) AS model_version
                FROM read_json_auto({sql_str(str(raw_path))})
                WHERE pred_eop IS NOT NULL
                  AND pred_ipu IS NOT NULL
                  AND pred_margin IS NOT NULL
            )
            TO {sql_str(str(parquet_path))}
            (FORMAT PARQUET, COMPRESSION ZSTD)
            """
        )
    finally:
        con.close()


def convert_parquet_to_canonical_parquet(raw_path: Path, parquet_path: Path):
    con = duckdb.connect(":memory:")
    try:
        con.execute(
            f"""
            COPY (
                SELECT
                    CAST(sample_id AS VARCHAR) AS sample_id,
                    CAST(precursor_set AS VARCHAR) AS precursor_set,
                    CAST(solvent AS VARCHAR) AS solvent,
                    CAST(ul AS VARCHAR) AS ul,
                    CAST(pred_eop AS DOUBLE) AS pred_eop,
                    CAST(pred_ipu AS DOUBLE) AS pred_ipu,
                    CAST(pred_margin AS DOUBLE) AS pred_margin,
                    CAST(model_version AS VARCHAR) AS model_version
                FROM read_parquet({sql_str(str(raw_path))})
                WHERE pred_eop IS NOT NULL
                  AND pred_ipu IS NOT NULL
                  AND pred_margin IS NOT NULL
            )
            TO {sql_str(str(parquet_path))}
            (FORMAT PARQUET, COMPRESSION ZSTD)
            """
        )
    finally:
        con.close()


def convert_raw_to_parquet(raw_path: Path, parquet_path: Path):
    suffix = raw_path.suffix.lower()
    parquet_path.parent.mkdir(parents=True, exist_ok=True)

    if suffix == ".csv":
        convert_csv_to_parquet(raw_path, parquet_path)
    elif suffix in [".xlsx", ".xls"]:
        convert_excel_to_parquet(raw_path, parquet_path)
    elif suffix in [".json", ".jsonl", ".ndjson"]:
        convert_json_to_parquet(raw_path, parquet_path)
    elif suffix == ".parquet":
        convert_parquet_to_canonical_parquet(raw_path, parquet_path)
    else:
        raise ValueError(f"Unsupported raw file extension: {suffix}")


def validate_parquet(parquet_path: Path) -> dict:
    con = duckdb.connect(":memory:")
    try:
        row = con.execute(
            """
            SELECT
                COUNT(*) AS row_count,
                MIN(pred_eop) AS min_eop,
                MAX(pred_eop) AS max_eop,
                MIN(pred_ipu) AS min_ipu,
                MAX(pred_ipu) AS max_ipu,
                MIN(pred_margin) AS min_margin,
                MAX(pred_margin) AS max_margin
            FROM read_parquet(?)
            """,
            [str(parquet_path)],
        ).fetchone()
        return {
            "row_count": int(row[0]),
            "min_eop": row[1],
            "max_eop": row[2],
            "min_ipu": row[3],
            "max_ipu": row[4],
            "min_margin": row[5],
            "max_margin": row[6],
        }
    finally:
        con.close()


def rebuild_local_raw(
    *,
    raw_local_path: str,
    processed_parquet_path: str,
    local_meta_path: str,
    timezone: str = "Asia/Seoul",
) -> dict:
    raw_path = Path(raw_local_path)
    processed_path = Path(processed_parquet_path)
    meta_path = Path(local_meta_path)

    if not raw_path.exists():
        raise FileNotFoundError(f"Raw local file not found: {raw_path}")

    processed_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".parquet",
        dir=str(processed_path.parent),
    ) as tmp_parquet:
        tmp_parquet_path = Path(tmp_parquet.name)

    try:
        convert_raw_to_parquet(raw_path, tmp_parquet_path)
        validation = validate_parquet(tmp_parquet_path)
        os.replace(tmp_parquet_path, processed_path)

        metadata = {
            "status": "success",
            "updated_at": datetime.now(ZoneInfo(timezone)).isoformat(timespec="seconds"),
            "source": "local_raw_rebuild",
            "raw_path": str(raw_path),
            "processed_parquet_path": str(processed_path),
            **validation,
        }
        meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        return metadata
    except Exception:
        if tmp_parquet_path.exists():
            tmp_parquet_path.unlink(missing_ok=True)
        raise


def download_convert_update(
    *,
    bucket: str,
    key: str,
    raw_dir: str,
    processed_parquet_path: str,
    local_meta_path: str,
    region_name: str = "ap-northeast-2",
    profile_name: str | None = None,
    timezone: str = "Asia/Seoul",
) -> dict:
    raw_dir_path = Path(raw_dir)
    processed_path = Path(processed_parquet_path)
    meta_path = Path(local_meta_path)

    raw_dir_path.mkdir(parents=True, exist_ok=True)
    processed_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.parent.mkdir(parents=True, exist_ok=True)

    raw_suffix = Path(key).suffix.lower()
    if not raw_suffix:
        raise ValueError("S3_KEY must include file extension, e.g. .csv, .xlsx, .json, .parquet")

    raw_path = raw_dir_path / f"latest_prediction{raw_suffix}"
    s3 = make_boto3_client(region_name=region_name, profile_name=profile_name)

    tmp_raw_path = None
    tmp_parquet_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=raw_suffix, dir=str(raw_dir_path)) as tmp_raw:
            tmp_raw_path = Path(tmp_raw.name)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".parquet", dir=str(processed_path.parent)) as tmp_parquet:
            tmp_parquet_path = Path(tmp_parquet.name)

        s3.download_file(Bucket=bucket, Key=key, Filename=str(tmp_raw_path))
        os.replace(tmp_raw_path, raw_path)

        convert_raw_to_parquet(raw_path, tmp_parquet_path)
        validation = validate_parquet(tmp_parquet_path)
        os.replace(tmp_parquet_path, processed_path)

        metadata = {
            "status": "success",
            "updated_at": datetime.now(ZoneInfo(timezone)).isoformat(timespec="seconds"),
            "source": "s3_download_convert",
            "bucket": bucket,
            "key": key,
            "raw_path": str(raw_path),
            "processed_parquet_path": str(processed_path),
            **validation,
        }
        meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        return metadata
    except Exception as e:
        for path in [tmp_raw_path, tmp_parquet_path]:
            if path and path.exists():
                path.unlink(missing_ok=True)

        metadata = {
            "status": "failed",
            "failed_at": datetime.now(ZoneInfo(timezone)).isoformat(timespec="seconds"),
            "source": "s3_download_convert",
            "bucket": bucket,
            "key": key,
            "error": repr(e),
        }
        meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        raise
