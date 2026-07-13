@echo off
title Dactyl-AI Modern Web Dashboard Launcher
echo ========================================================================
echo   DACTYL-AI V2.5 - MAGIC CURSOR MODERN WEB DASHBOARD LAUNCHER
echo ========================================================================
echo.
echo Memulai Server UI Backend...
start /B python dactyl_launcher_server.py
timeout /t 2 /nobreak > nul
echo.
echo Membuka Web Dashboard di Browser...
start http://localhost:8080/run_system_ui.html
echo.
echo Dashboard aktif! Biarkan jendela terminal ini terbuka saat menggunakan sistem.
echo Tekan CTRL+C untuk menutup server.
pause
