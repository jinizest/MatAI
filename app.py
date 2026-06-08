import atexit
import os
from threading import Lock

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from db import get_summary, query_candidates, read_metadata
from updater import download_convert_update, rebuild_local_raw


load_dotenv()
update_lock = Lock()


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
    app.config["AWS_REGION"] = os.getenv("AWS_REGION", "ap-northeast-2")
    app.config["AWS_PROFILE"] = os.getenv("AWS_PROFILE") or None
    app.config["S3_BUCKET"] = os.getenv("S3_BUCKET", "")
    app.config["S3_KEY"] = os.getenv("S3_KEY", "")
    app.config["RAW_DIR"] = os.getenv("RAW_DIR", "data/raw")
    app.config["RAW_LOCAL_PATH"] = os.getenv("RAW_LOCAL_PATH", "data/raw/latest_prediction.csv")
    app.config["PROCESSED_PARQUET_PATH"] = os.getenv("PROCESSED_PARQUET_PATH", "data/processed/mor_predictions_latest.parquet")
    app.config["LOCAL_META_PATH"] = os.getenv("LOCAL_META_PATH", "data/processed/mor_predictions_meta.json")
    app.config["ENABLE_SCHEDULER"] = os.getenv("ENABLE_SCHEDULER", "0")
    app.config["SCHEDULER_TIMEZONE"] = os.getenv("SCHEDULER_TIMEZONE", "Asia/Seoul")

    register_routes(app)
    maybe_start_scheduler(app)
    return app


def run_s3_update_job(app: Flask):
    with app.app_context():
        with update_lock:
            metadata = download_convert_update(
                bucket=app.config["S3_BUCKET"],
                key=app.config["S3_KEY"],
                raw_dir=app.config["RAW_DIR"],
                processed_parquet_path=app.config["PROCESSED_PARQUET_PATH"],
                local_meta_path=app.config["LOCAL_META_PATH"],
                region_name=app.config["AWS_REGION"],
                profile_name=app.config["AWS_PROFILE"],
                timezone=app.config["SCHEDULER_TIMEZONE"],
            )
            app.logger.info("S3 prediction table updated: %s", metadata)


def maybe_start_scheduler(app: Flask):
    if app.config["ENABLE_SCHEDULER"] != "1":
        return

    is_reloader_process = os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    is_normal_process = not app.debug
    if not (is_reloader_process or is_normal_process):
        return

    scheduler = BackgroundScheduler(timezone=app.config["SCHEDULER_TIMEZONE"])
    scheduler.add_job(
        func=lambda: run_s3_update_job(app),
        trigger="cron",
        hour=0,
        minute=0,
        id="daily_s3_prediction_table_update",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown(wait=False))
    app.logger.info("Scheduler started: daily S3 raw table update at 00:00 KST")


def register_routes(app: Flask):
    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/api/meta")
    def meta():
        metadata = read_metadata(app.config["LOCAL_META_PATH"])
        try:
            summary = get_summary(parquet_path=app.config["PROCESSED_PARQUET_PATH"])
        except FileNotFoundError:
            summary = None
        return jsonify({"metadata": metadata, "summary": summary})

    @app.post("/api/admin/rebuild-local")
    def manual_rebuild_local():
        try:
            with update_lock:
                metadata = rebuild_local_raw(
                    raw_local_path=app.config["RAW_LOCAL_PATH"],
                    processed_parquet_path=app.config["PROCESSED_PARQUET_PATH"],
                    local_meta_path=app.config["LOCAL_META_PATH"],
                    timezone=app.config["SCHEDULER_TIMEZONE"],
                )
            return jsonify({"status": "success", "metadata": metadata})
        except Exception as e:
            return jsonify({"status": "failed", "error": repr(e)}), 500

    @app.post("/api/admin/refresh-s3")
    def manual_refresh_s3():
        if not app.config["S3_BUCKET"] or not app.config["S3_KEY"]:
            return jsonify({
                "status": "failed",
                "error": "S3_BUCKET and S3_KEY must be configured in .env",
            }), 400

        try:
            with update_lock:
                metadata = download_convert_update(
                    bucket=app.config["S3_BUCKET"],
                    key=app.config["S3_KEY"],
                    raw_dir=app.config["RAW_DIR"],
                    processed_parquet_path=app.config["PROCESSED_PARQUET_PATH"],
                    local_meta_path=app.config["LOCAL_META_PATH"],
                    region_name=app.config["AWS_REGION"],
                    profile_name=app.config["AWS_PROFILE"],
                    timezone=app.config["SCHEDULER_TIMEZONE"],
                )
            return jsonify({"status": "success", "metadata": metadata})
        except Exception as e:
            return jsonify({"status": "failed", "error": repr(e)}), 500

    @app.get("/api/candidates")
    def candidates():
        eop_max = request.args.get("eop_max", default=1.0, type=float)
        ipu_max = request.args.get("ipu_max", default=1.0, type=float)
        margin_min = request.args.get("margin_min", default=1.0, type=float)
        limit = request.args.get("limit", default=100, type=int)
        sort = request.args.get("sort", default="eop_asc", type=str)

        try:
            result = query_candidates(
                parquet_path=app.config["PROCESSED_PARQUET_PATH"],
                eop_max=eop_max,
                ipu_max=ipu_max,
                margin_min=margin_min,
                limit=limit,
                sort=sort,
            )
            return jsonify({"status": "success", "count": len(result), "data": result})
        except FileNotFoundError as e:
            return jsonify({"status": "failed", "error": str(e)}), 404


app = create_app()
