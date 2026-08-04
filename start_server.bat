@echo off
cd /d "E:\gs\pt\2\backend"
python -m uvicorn main:app --host 0.0.0.0 --port 8000
