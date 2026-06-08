import json
from pathlib import Path

import duckdb


SORT_MAP = {
    "eop_asc": "pred_eop ASC, pred_ipu ASC, pred_margin DESC",
    "ipu_asc": "pred_ipu ASC, pred_eop ASC, pred_margin DESC",
    "margin_desc": "pred_margin DESC, pred_eop ASC, pred_ipu ASC",
    "balanced": "((pred_eop + pred_ipu) - pred_margin) ASC",
}


def check_parquet_exists(parquet_path: str):
    path = Path(parquet_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Processed Parquet not found: {parquet_path}. "
            f"Run local rebuild or S3 refresh first."
        )


def query_candidates(
    *,
    parquet_path: str,
    eop_max: float,
    ipu_max: float,
    margin_min: float,
    limit: int = 100,
    sort: str = "eop_asc",
):
    check_parquet_exists(parquet_path)

    limit = max(1, min(int(limit), 1000))
    order_by = SORT_MAP.get(sort, SORT_MAP["eop_asc"])

    con = duckdb.connect(":memory:")
    try:
        rows = con.execute(
            f"""
            SELECT
                sample_id,
                precursor_set,
                solvent,
                ul,
                pred_eop,
                pred_ipu,
                pred_margin,
                model_version,
                ((pred_eop + pred_ipu) - pred_margin) AS candidate_score
            FROM read_parquet(?)
            WHERE pred_eop <= ?
              AND pred_ipu <= ?
              AND pred_margin >= ?
            ORDER BY {order_by}
            LIMIT ?
            """,
            [
                parquet_path,
                eop_max,
                ipu_max,
                margin_min,
                limit,
            ],
        ).fetchall()

        return [
            {
                "sample_id": row[0],
                "precursor_set": row[1],
                "solvent": row[2],
                "ul": row[3],
                "pred_eop": row[4],
                "pred_ipu": row[5],
                "pred_margin": row[6],
                "model_version": row[7],
                "candidate_score": row[8],
            }
            for row in rows
        ]
    finally:
        con.close()


def get_summary(*, parquet_path: str):
    check_parquet_exists(parquet_path)

    con = duckdb.connect(":memory:")
    try:
        row = con.execute(
            """
            SELECT
                COUNT(*) AS n_rows,
                MIN(pred_eop) AS min_eop,
                MAX(pred_eop) AS max_eop,
                MIN(pred_ipu) AS min_ipu,
                MAX(pred_ipu) AS max_ipu,
                MIN(pred_margin) AS min_margin,
                MAX(pred_margin) AS max_margin,
                COUNT(DISTINCT model_version) AS n_model_versions,
                SUM(CASE WHEN pred_eop <= 1.0 AND pred_ipu <= 1.0 AND pred_margin >= 1.0 THEN 1 ELSE 0 END) AS n_default_hits
            FROM read_parquet(?)
            """,
            [parquet_path],
        ).fetchone()

        return {
            "n_rows": row[0],
            "min_eop": row[1],
            "max_eop": row[2],
            "min_ipu": row[3],
            "max_ipu": row[4],
            "min_margin": row[5],
            "max_margin": row[6],
            "n_model_versions": row[7],
            "n_default_hits": row[8],
        }
    finally:
        con.close()


def read_metadata(meta_path: str):
    path = Path(meta_path)
    if not path.exists():
        return {
            "status": "not_downloaded",
            "message": "No metadata file yet.",
        }
    return json.loads(path.read_text(encoding="utf-8"))
