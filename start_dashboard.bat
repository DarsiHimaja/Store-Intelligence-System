@echo off
title Store Intelligence Dashboard

echo.
echo =========================================
echo  Starting Dashboard on http://localhost:8501
echo  (Make sure API is running first!)
echo =========================================
cd /d %~dp0
python -m streamlit run dashboard/app.py --server.port 8501
pause
