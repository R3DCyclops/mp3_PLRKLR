#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import shutil
import zipfile
import urllib.request
from pathlib import Path

FFMPEG_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl-shared.zip"
ARCHIVE_NAME = "ffmpeg-master-latest-win64-gpl-shared.zip"
EXTRACTED_FOLDER = "ffmpeg-master-latest-win64-gpl-shared"
TARGET_FOLDER = "ffmpeg"

def download_file(url, destination):
    def reporthook(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            percent = min(100, downloaded * 100 / total_size)
            print(f"\r[INFO] Прогресс: {percent:.1f}% ({downloaded // 1024} KB / {total_size // 1024} KB)", end='')
    try:
        urllib.request.urlretrieve(url, destination, reporthook=reporthook)
        print()
        print(f"[OK] Файл сохранён: {destination}")
        return True
    except Exception as e:
        print(f"\n[ERROR] Ошибка загрузки: {e}")
        return False

def extract_and_rename(archive_path, target_name):
    try:
        with zipfile.ZipFile(archive_path, 'r') as zf:
            zf.extractall('.')
        print(f"[OK] Архив распакован")
        
        if os.path.exists(EXTRACTED_FOLDER):
            if os.path.exists(target_name):
                print(f"[INFO] Папка '{target_name}' уже существует, удаляю...")
                shutil.rmtree(target_name)
            os.rename(EXTRACTED_FOLDER, target_name)
            print(f"[OK] Папка переименована: {EXTRACTED_FOLDER} -> {target_name}")
            return True
        else:
            print(f"[ERROR] Папка '{EXTRACTED_FOLDER}' не найдена после распаковки")
            return False
    except Exception as e:
        print(f"[ERROR] Ошибка при распаковке: {e}")
        return False

def cleanup(archive_path):
    if os.path.exists(archive_path):
        os.remove(archive_path)
        print(f"[OK] Архив удалён: {archive_path}")

def main():
    print("=" * 60)
    print("FFmpeg Setup Script (GPL build)")
    print("Источник: BtbN/FFmpeg-Builds")
    print("Лицензия: GNU General Public License")
    print("=" * 60)
    
    if os.path.exists(TARGET_FOLDER) and os.listdir(TARGET_FOLDER):
        print(f"[INFO] Папка '{TARGET_FOLDER}' уже существует и не пуста")
        answer = input("Перезаписать? (y/n): ").strip().lower()
        if answer != 'y':
            print("[INFO] Отменено пользователем")
            return
        shutil.rmtree(TARGET_FOLDER)
    
    if not download_file(FFMPEG_URL, ARCHIVE_NAME):
        sys.exit(1)
    
    if not extract_and_rename(ARCHIVE_NAME, TARGET_FOLDER):
        sys.exit(1)
    
    cleanup(ARCHIVE_NAME)
    
    ffmpeg_exe = os.path.join(TARGET_FOLDER, "bin", "ffmpeg.exe")
    if os.path.exists(ffmpeg_exe):
        print(f"[OK] FFmpeg готов: {ffmpeg_exe}")
    else:
        print(f"[WARN] ffmpeg.exe не найден по ожидаемому пути")
    
    print("=" * 60)
    print("[OK] Установка завершена")
    print(f"Важно: Данный билд FFmpeg распространяется под лицензией GPL.")
    print("При модификации или распространении проекта соблюдайте условия GPL.")
    print("=" * 60)

if __name__ == "__main__":
    main()