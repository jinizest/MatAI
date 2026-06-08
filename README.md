# MOR Prediction Viewer Demo

이 예제는 S3에서 최신 prediction table을 받아 로컬 raw 파일로 저장한 뒤, Parquet로 변환하고 Flask + DuckDB로 후보군을 조회하는 최소 예시입니다.

## 포함 파일

```text
mor_viewer_demo/
  app.py
  db.py
  updater.py
  refresh_once.py
  rebuild_local_once.py
  make_sample_data.py
  requirements.txt
  .env.example
  data/raw/latest_prediction.csv
  data/processed/mor_predictions_latest.parquet
  data/processed/mor_predictions_meta.json
  templates/index.html
```

## 빠른 실행

```bash
cd mor_viewer_demo
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app app run --debug --no-reload
```

Windows PowerShell에서는 아래처럼 실행합니다.

```powershell
cd mor_viewer_demo
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
flask --app app run --debug --no-reload
```

접속 주소:

```text
http://127.0.0.1:5000
```

## 로컬 예시 데이터 재생성

```bash
python make_sample_data.py
```

## 로컬 raw CSV를 Parquet로 다시 변환

```bash
python rebuild_local_once.py
```

또는 웹 화면에서 `Local raw 재변환` 버튼을 누릅니다.

## S3 사용으로 전환

```bash
cp .env.example .env
```

`.env`에서 아래 값을 실제 값으로 수정합니다.

```bash
AWS_REGION=ap-northeast-2
AWS_PROFILE=your-profile
S3_BUCKET=your-bucket-name
S3_KEY=ml-output/latest_prediction.csv
ENABLE_SCHEDULER=1
```

수동 S3 업데이트:

```bash
python refresh_once.py
```

또는 웹 화면에서 `S3 다운로드 및 변환` 버튼을 누릅니다.

## 운영 예시

```bash
gunicorn -w 1 --threads 4 -b 0.0.0.0:8000 "app:create_app()"
```

Flask 내부 scheduler를 쓰는 경우 worker는 1개로 두는 것을 권장합니다.
