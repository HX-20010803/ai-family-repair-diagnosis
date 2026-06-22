@echo off
set DATABASE_URL=postgresql+psycopg://repair:repair@localhost:5432/repair_ai
cd /d "%~dp0..\backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
