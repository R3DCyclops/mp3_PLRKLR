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

import subprocess
import sys
import os
import re
import json
import urllib.parse

def get_ffmpeg_path():
    paths = [
        os.path.join(os.path.dirname(__file__), "..", "..", "ffmpeg", "bin", "ffmpeg.exe"),
        os.path.join(os.path.dirname(__file__), "..", "..", "ffmpeg", "ffmpeg.exe"),
    ]
    for p in paths:
        if os.path.exists(p):
            return os.path.normpath(p)
    try:
        result = subprocess.run(['where', 'ffmpeg'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return result.stdout.strip().split('\n')[0].strip()
    except:
        pass
    return ""

def _clean_text(text):
    if not text:
        return ""
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'\(.*?\)', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip().lower()

def _encode_query(query):
    """кодирует запрос сохраняя кириллицу"""
    return query

def search(query, limit=5, timeout=20, debug_mode=False):
    try:
        cmd = [
            'yt-dlp',
            '--flat-playlist',
            '--dump-json',
            '--no-download',
            '--extractor-args', 'youtube:player_client=web,ios',
            f'ytsearch:{query}',
            '--playlist-end', str(limit)
        ]
        if debug_mode:
            cmd.append('--verbose')
            print(f"[DEBUG] YouTube search: ytsearch:{query}")
        
        creationflags = 0
        if sys.platform == 'win32':
            creationflags = subprocess.CREATE_NO_WINDOW
        
        result = subprocess.run(cmd, capture_output=True, timeout=timeout, creationflags=creationflags)
        stdout = result.stdout.decode('utf-8', errors='replace')
        stderr = result.stderr.decode('utf-8', errors='replace') if result.stderr else ''
        
        tracks = []
        for line in stdout.strip().split('\n'):
            if line.strip():
                try:
                    track_data = json.loads(line)
                    title = track_data.get('title') or track_data.get('track') or 'Unknown'
                    artist = (track_data.get('uploader') or 
                             track_data.get('channel') or 
                             track_data.get('artist') or 
                             track_data.get('creator') or 
                             'Unknown')
                    
                    url = track_data.get('url') or track_data.get('webpage_url')
                    if not url:
                        continue
                    
                    tracks.append({
                        'title': title,
                        'uploader': artist,
                        'url': url if url.startswith('http') else f"https://www.youtube.com{url}",
                        'id': track_data.get('id', ''),
                        'duration': track_data.get('duration', 0),
                        'extractor': track_data.get('extractor', 'youtube'),
                        'webpage_url': track_data.get('webpage_url', '')
                    })
                except Exception as e:
                    if debug_mode:
                        print(f"[WARN] YouTube: parse error: {e}")
                    continue
        
        if debug_mode:
            print(f"[DEBUG] YouTube: найдено {len(tracks)} треков")
        
        return {
            'success': True,
            'tracks': tracks,
            'count': len(tracks),
            'stderr': stderr[:500] if stderr else '',
            'error': ''
        }
        
    except subprocess.TimeoutExpired:
        return {'success': False, 'tracks': [], 'count': 0, 'error': f'Таймаут {timeout} сек', 'stderr': ''}
    except FileNotFoundError:
        return {'success': False, 'tracks': [], 'count': 0, 'error': 'yt-dlp не найден', 'stderr': ''}
    except Exception as e:
        return {'success': False, 'tracks': [], 'count': 0, 'error': str(e), 'stderr': ''}

def download(url, output_path, artist, track, ffmpeg_path="", use_artist_folders=False, timeout=180, debug_mode=False):
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
                if filename.endswith('.mp3') and (safe_artist[:10] in filename or safe_track[:10] in filename):
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
        return {'success': False, 'filepath': None, 'stderr': f'Таймаут ({timeout} сек)', 'returncode': -1}
    except FileNotFoundError:
        return {'success': False, 'filepath': None, 'stderr': 'yt-dlp не найден', 'returncode': -1}
    except Exception as e:
        return {'success': False, 'filepath': None, 'stderr': str(e), 'returncode': -1}

def is_region_blocked(track_info, download_result, filepath=None):
    stderr = download_result.get('stderr', '').lower()
    stdout = download_result.get('stdout', '').lower()
    
    region_keywords = [
        'region', 'blocked', 'not available in your location',
        'country restriction', 'geoblock', 'geo-block', 'unavailable',
        'restricted', 'this track', 'russian federation', 'not available in russia',
        'private video', 'video unavailable', 'deleted by uploader', 'copyright'
    ]
    
    for kw in region_keywords:
        if kw in stderr or kw in stdout:
            return True
    
    if filepath and os.path.exists(filepath):
        try:
            if os.path.getsize(filepath) < 100 * 1024:
                return True
        except:
            pass
    
    duration = track_info.get('duration', 0)
    if duration and duration < 35000:
        format_id = track_info.get('format_id', '').lower()
        if 'preview' in format_id or 'snippet' in format_id:
            return True
    
    return False