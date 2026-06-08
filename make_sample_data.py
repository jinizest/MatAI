from pathlib import Path
import json
import random
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd


BASE = Path(__file__).resolve().parent
RAW_PATH = BASE / "data/raw/latest_prediction.csv"
PARQUET_PATH = BASE / "data/processed/mor_predictions_latest.parquet"
META_PATH = BASE / "data/processed/mor_predictions_meta.json"


def main():
    random.seed(42)
    precursors = ["SnA/SnB", "SnA/SnC", "SnB/SnD", "SnC/SnE", "SnA/SnF", "SnD/SnG"]
    solvents = ["Solv_A", "Solv_B", "Solv_C"]
    uls = ["UL_01", "UL_02", "UL_03", "UL_04"]
    additives = ["None", "Add_01", "Add_02"]

    rows = []
    for i in range(1, 81):
        pred_eop = random.uniform(0.78, 1.18)
        pred_ipu = random.uniform(0.82, 1.25)
        pred_margin = random.uniform(0.84, 1.34)
        if i in [3, 7, 11, 19, 23, 37, 41, 58, 62, 76]:
            pred_eop = random.uniform(0.80, 0.97)
            pred_ipu = random.uniform(0.82, 0.99)
            pred_margin = random.uniform(1.05, 1.32)

        rows.append({
            "sample_id": f"MOR_VS_{i:04d}",
            "precursor_set": random.choice(precursors),
            "solvent": random.choice(solvents),
            "ul": random.choice(uls),
            "additive": random.choice(additives),
            "pred_eop": round(pred_eop, 4),
            "pred_ipu": round(pred_ipu, 4),
            "pred_margin": round(pred_margin, 4),
            "confidence": round(random.uniform(0.62, 0.96), 4),
            "model_version": "mor_fcb_v0.3.1",
            "batch_id": "demo_batch_20260608",
        })

    df = pd.DataFrame(rows)
    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    PARQUET_PATH.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(RAW_PATH, index=False)
    df[[
        "sample_id",
        "precursor_set",
        "solvent",
        "ul",
        "pred_eop",
        "pred_ipu",
        "pred_margin",
        "model_version",
    ]].to_parquet(PARQUET_PATH, index=False)

    meta = {
        "status": "success",
        "updated_at": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds"),
        "source": "sample_generated_locally",
        "raw_path": str(RAW_PATH.relative_to(BASE)),
        "processed_parquet_path": str(PARQUET_PATH.relative_to(BASE)),
        "row_count": int(len(df)),
        "min_eop": float(df["pred_eop"].min()),
        "max_eop": float(df["pred_eop"].max()),
        "min_ipu": float(df["pred_ipu"].min()),
        "max_ipu": float(df["pred_ipu"].max()),
        "min_margin": float(df["pred_margin"].min()),
        "max_margin": float(df["pred_margin"].max()),
    }
    META_PATH.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {RAW_PATH}")
    print(f"Wrote {PARQUET_PATH}")
    print(f"Wrote {META_PATH}")


if __name__ == "__main__":
    main()
