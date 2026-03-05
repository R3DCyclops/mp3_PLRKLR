@echo off
chcp 65001 >nul
setlocal

echo    mp3_PLRKLR - Сборка в OneFile
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python не найден
    pause
    exit /b 1
)
echo [OK] Python найден

echo [INFO] Установка зависимостей...
pip install --upgrade pip --quiet
pip install pyinstaller --quiet
pip install rapidfuzz pillow requests --quiet
echo [OK] Зависимости готовы

if not exist "ffmpeg\bin\ffmpeg.exe" (
    echo [WARNING] ffmpeg\bin\ffmpeg.exe не найден
    echo [INFO] Программа будет искать ffmpeg в системе
    set "FFMPEG_PARAM="
) else (
    echo [OK] ffmpeg найден, вшиваю всю папку...
    set "FFMPEG_PARAM=--add-data ffmpeg;ffmpeg"
)

set "ICON_PARAM="
if exist "ico.ico" (
    set "ICON_PARAM=--icon ico.ico"
    echo [OK] Иконка найдена
) else (
    echo [WARNING] ico.ico не найден
)

if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "*.spec" del /q "*.spec"

echo [INFO] Начало компиляции...
echo.

pyinstaller ^
    --onefile ^
    --windowed ^
    --name "mp3_PLRKLR" ^
    %ICON_PARAM% ^
    %FFMPEG_PARAM% ^
    --add-data logo.png;. ^
    --add-data ico.ico;. ^
    --add-data screen1.png;. ^
    --add-data screen2.png;. ^
    --add-data egg.png;. ^
    --add-data strat;strat ^
    --add-data stratwindow.py;. ^
    --add-data LICENSE;. ^
    --hidden-import rapidfuzz ^
    --hidden-import PIL ^
    --hidden-import requests ^
    --hidden-import tkinter ^
    --hidden-import requests ^
    --hidden-import bs4 ^
    --hidden-import certifi ^
    --hidden-import webbrowser ^
    --hidden-import json ^
    --hidden-import ctypes ^
    --hidden-import yt_dlp ^
    --hidden-import packaging ^
    --noconfirm ^
    --clean ^
    "main.py"

if errorlevel 1 (
    echo.
    echo [ERROR] Ошибка компиляции
    pause
    exit /b 1
)

echo.
echo    [OK] Сборка завершена
echo.
echo Файл: dist\mp3_PLRKLR.exe
echo.

start "" "dist"
pause