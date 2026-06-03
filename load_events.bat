@echo off
title Load Events

echo.
echo =========================================
echo  Loading events into API...
echo  (Make sure API is running first!)
echo =========================================
cd /d %~dp0
python load_events.py
echo.
echo Done! Refresh your dashboard.
pause
