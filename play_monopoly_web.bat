@echo off
cd /d "C:\Users\mschl\OneDrive\Documents\GitHub\Monopoly"
start "" "C:\Users\mschl\AppData\Local\Programs\Python\Python310\python.exe" web/server.py
timeout /t 2 /nobreak >nul
start http://127.0.0.1:5000

