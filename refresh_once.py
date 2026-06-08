import os
from dotenv import load_dotenv

from updater import download_convert_update


load_dotenv()


if __name__ == "__main__":
    metadata = download_convert_update(
        bucket=os.getenv("S3_BUCKET", ""),
        key=os.getenv("S3_KEY", ""),
        raw_dir=os.getenv("RAW_DIR", "data/raw"),
        processed_parquet_path=os.getenv("PROCESSED_PARQUET_PATH", "data/processed/mor_predictions_latest.parquet"),
        local_meta_path=os.getenv("LOCAL_META_PATH", "data/processed/mor_predictions_meta.json"),
        region_name=os.getenv("AWS_REGION", "ap-northeast-2"),
        profile_name=os.getenv("AWS_PROFILE") or None,
        timezone=os.getenv("SCHEDULER_TIMEZONE", "Asia/Seoul"),
    )
    print(metadata)
