import os
from dotenv import load_dotenv

from updater import rebuild_local_raw


load_dotenv()


if __name__ == "__main__":
    metadata = rebuild_local_raw(
        raw_local_path=os.getenv("RAW_LOCAL_PATH", "data/raw/latest_prediction.csv"),
        processed_parquet_path=os.getenv("PROCESSED_PARQUET_PATH", "data/processed/mor_predictions_latest.parquet"),
        local_meta_path=os.getenv("LOCAL_META_PATH", "data/processed/mor_predictions_meta.json"),
        timezone=os.getenv("SCHEDULER_TIMEZONE", "Asia/Seoul"),
    )
    print(metadata)
