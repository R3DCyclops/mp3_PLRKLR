#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (C) 2026 m0reslav
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

"""
возвращает список треков с полями title, uploader, url, id, duration
"""

import subprocess
import sys
import json
import os

def get_ffmpeg_path():
    paths_to_check = [
        os.path.join(os.path.dirname(__file__), "..", "..", "ffmpeg", "bin", "ffmpeg.exe"),
        os.path.join(os.path.dirname(__file__), "..", "..", "ffmpeg", "ffmpeg.exe"),
    ]
    for path in paths_to_check:
        if os.path.exists(path):
            return os.path.normpath(path)
    try:
        result = subprocess.run(['where', 'ffmpeg'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return result.stdout.strip().split('\n')[0].strip()
    except:
        pass
    return ""

def search(query, limit=5, timeout=20, debug_mode=False):
    """
    Поиск треков на SoundCloud
    
    Args:
        query: Строка поиска (artist - track)
        limit: Максимум результатов
        timeout: Таймаут в секундах
        debug_mode: Режим отладки
    
    Returns:
        dict: {
            'success': bool,
            'tracks': list,
            'count': int,
            'error': str (если ошибка)
        }
    """
    try:
        cmd = [
            'yt-dlp',
            '--flat-playlist',
            '--dump-json',
            '--no-download',
            '--extractor-args', 'soundcloud:formats=*_aac,*_mp3',
            f'scsearch:{query}',
            '--playlist-end', str(limit)
        ]
        if debug_mode:
            cmd.append('--verbose')
        
        creationflags = 0
        if sys.platform == 'win32':
            creationflags = subprocess.CREATE_NO_WINDOW
        
        result = subprocess.run(cmd, capture_output=True, timeout=timeout, creationflags=creationflags)
        stdout = result.stdout.decode('utf-8', errors='replace')
        stderr = result.stderr.decode('utf-8', errors='replace') if result.stderr else ''
        
        tracks = []
        for line in stdout.strip().split('\n'):
            if line:
                try:
                    track_data = json.loads(line)
                    tracks.append({
                        'title': track_data.get('title', 'Unknown'),
                        'uploader': track_data.get('uploader', 'Unknown'),
                        'url': track_data.get('url', ''),
                        'id': track_data.get('id', ''),
                        'duration': track_data.get('duration', 0)
                    })
                except Exception as e:
                    if debug_mode:
                        print(f"[WARN] Ошибка парсинга JSON: {e}")
        
        return {
            'success': True,
            'tracks': tracks,
            'count': len(tracks),
            'stderr': stderr[:500] if stderr else ''
        }
    except subprocess.TimeoutExpired:
        return {'success': False, 'tracks': [], 'count': 0, 'error': f'Таймаут {timeout} сек', 'stderr': ''}
    except Exception as e:
        return {'success': False, 'tracks': [], 'count': 0, 'error': str(e), 'stderr': ''}

def download(url, output_path, artist, track, ffmpeg_path="", use_artist_folders=False, timeout=180, debug_mode=False):
    """
    Скачать трек по URL
    
    Returns:
        dict: {
            'success': bool,
            'filepath': str (путь к файлу),
            'stderr': str
        }
    """
    import re
    try:
        safe_artist = re.sub(r'[^\w\s-]', '', artist)
        safe_track = re.sub(r'[^\w\s-]', '', track)
        
        if use_artist_folders:
            output_template = os.path.join(output_path, safe_artist, f"{safe_artist} - {safe_track}.%(ext)s")
        else:
            output_template = os.path.join(output_path, f"{safe_artist} - {safe_track}.%(ext)s")
        
        cmd = [
            'yt-dlp',
            '-x',
            '--audio-format', 'mp3',
            '--embed-metadata',
            '--embed-thumbnail',
            '-o', output_template,
            url
        ]
        
        if ffmpeg_path and os.path.exists(ffmpeg_path):
            cmd.extend(['--ffmpeg-location', ffmpeg_path])
        
        if debug_mode:
            cmd.append('--verbose')
        
        creationflags = 0
        if sys.platform == 'win32':
            creationflags = subprocess.CREATE_NO_WINDOW
        
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout, creationflags=creationflags)
        stderr = result.stderr[:1000] if result.stderr else ''
        stdout = result.stdout[:500] if result.stdout else ''
        
        actual_filepath = None
        if os.path.exists(output_path):
            for filename in os.listdir(output_path):
                if filename.endswith('.mp3') and safe_artist[:10] in filename:
                    actual_filepath = os.path.join(output_path, filename)
                    break
        
        return {
            'success': result.returncode == 0,
            'filepath': actual_filepath,
            'stderr': stderr,
            'stdout': stdout,
            'returncode': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {'success': False, 'filepath': None, 'stderr': f'Таймаут скачивания ({timeout} сек)', 'returncode': -1}
    except Exception as e:
        return {'success': False, 'filepath': None, 'stderr': str(e), 'returncode': -1}

def is_region_blocked(track_info, download_result, filepath=None):
    """проверка на блокировку по региону"""
    stderr = download_result.get('stderr', '').lower()
    stdout = download_result.get('stdout', '').lower()
    
    region_keywords = [
        'region', 'blocked', 'not available in your location',
        'country restriction', 'geoblock', 'geo-block', 'unavailable',
        'restricted', 'this track', 'russian federation', 'not available in russia'
    ]
    
    for kw in region_keywords:
        if kw in stderr or kw in stdout:
            return True
    
    if filepath and os.path.exists(filepath):
        #проверка длительности (менее 35 сек - снипп)
        try:
            ffprobe_path = ""
            if ffmpeg_path := get_ffmpeg_path():
                ffprobe_path = ffmpeg_path.replace('ffmpeg.exe', 'ffprobe.exe')
            
            if ffprobe_path and os.path.exists(ffprobe_path):
                cmd = [ffprobe_path, '-v', 'quiet', '-print_format', 'json', '-show_format', filepath]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    duration = float(data.get('format', {}).get('duration', 0)) * 1000
                    if duration < 35000:
                        return True
        except:
            pass
    
    duration = track_info.get('duration', 0)
    if duration and duration < 35000:
        format_id = track_info.get('format_id', '').lower()
        if 'preview' in format_id or 'snippet' in format_id:
            return True
    
    return False