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

_requests = None
_BeautifulSoup = None

def _ensure_deps(debug_mode=False):
    global _requests, _BeautifulSoup
    if _requests is None:
        try:
            import requests
            from bs4 import BeautifulSoup
            _requests = requests
            _BeautifulSoup = BeautifulSoup
            return True
        except ImportError as e:
            if debug_mode:
                print(f"[WARN] Hitmotop: нет зависимостей: {e}")
            return False
    return True

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

def _absolutize_url(url, base="https://rus.hitmotop.com"):
    if not url:
        return ""
    if url.startswith('http'):
        return url
    if url.startswith('/'):
        return base + url
    return base + '/' + url

def _is_direct_mp3_url(url):
    """проверяет ведёт ли ссыль в mp3"""
    return '/get/' in url or url.lower().endswith('.mp3') or '.mp3?' in url.lower()

def _get_real_download_link(track_page_url, debug_mode=False):
    """
    получает mp3 ссыль из страницы трека
    если УРЛ уже прямой то возвращает его без запросов
    """
    if _is_direct_mp3_url(track_page_url):
        return track_page_url
    
    if not _ensure_deps(debug_mode):
        return None
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9',
        }
        resp = _requests.get(track_page_url, headers=headers, timeout=10, stream=True)
        
        #если это аудио, а не хтмл
        content_type = resp.headers.get('Content-Type', '').lower()
        if 'audio/' in content_type or 'application/octet-stream' in content_type:
            if debug_mode:
                print(f"[DEBUG] Hitmotop: прямой аудио-ответ → {track_page_url}")
            return track_page_url
        
        resp.raise_for_status()
        html_chunk = resp.raw.read(50 * 1024).decode('utf-8', errors='ignore')
        
        patterns = [
            r'["\'](/get/[^"\']+\.mp3[^"\']*)["\']',
            r'["\'](https?://[^"\']+\.hitmotop\.com/get/[^"\']+\.mp3[^"\']*)["\']',
            r'data-href=["\']([^"\']+\.mp3[^"\']*)["\']',
            r'href=["\']([^"\']+\.mp3\?[^"\']*)["\']',
        ]
        for pattern in patterns:
            match = re.search(pattern, html_chunk)
            if match:
                return _absolutize_url(match.group(1))
        
        soup = _BeautifulSoup(html_chunk, 'html.parser')
        btn = soup.find('a', class_='track__download-btn')
        if btn and btn.get('href'):
            return _absolutize_url(btn['href'])
            
        return None
    except UnicodeDecodeError:
        #получил бинарник значит это уже мп3
        if debug_mode:
            print(f"[DEBUG] Hitmotop: бинарный ответ - прямой MP3: {track_page_url}")
        return track_page_url
    except Exception as e:
        if debug_mode:
            print(f"[WARN] Hitmotop: не удалось получить линк: {e}")
        return None

def search(query, limit=5, timeout=20, debug_mode=False):
    if not _ensure_deps(debug_mode):
        return {'success': False, 'tracks': [], 'count': 0, 'error': 'Нет зависимостей', 'stderr': ''}
    
    try:
        search_query = "+".join(query.split())
        search_url = f"https://rus.hitmotop.com/search?q={_requests.utils.quote(search_query)}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9',
        }
        
        response = _requests.get(search_url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        soup = _BeautifulSoup(response.text, 'html.parser')
        tracks = []
        
        for item in soup.find_all('li', class_='tracks__item')[:limit]:
            try:
                title_elem = item.find('div', class_='track__title')
                title = title_elem.get_text(strip=True) if title_elem else ''
                
                artist_elem = item.find('div', class_='track__desc')
                artist = artist_elem.get_text(strip=True) if artist_elem else 'Unknown'
                
                duration = 0
                dur_elem = item.find('div', class_='track__fulltime')
                if dur_elem:
                    try:
                        dur_text = re.sub(r'[^\d:]', '', dur_elem.get_text(strip=True))
                        parts = dur_text.split(':')
                        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                            duration = (int(parts[0]) * 60 + int(parts[1])) * 1000
                    except:
                        pass
                
                download_btn = item.find('a', class_='track__download-btn')
                if not download_btn or 'href' not in download_btn.attrs:
                    continue
                
                page_url = _absolutize_url(download_btn['href'])
                
                if _is_direct_mp3_url(page_url):
                    direct_url = page_url
                else:
                    direct_url = _get_real_download_link(page_url, debug_mode)
                    if not direct_url:
                        direct_url = page_url
                
                tracks.append({
                    'title': title,
                    'uploader': artist,
                    'url': direct_url,
                    'id': page_url.split('/')[-1],
                    'duration': duration,
                    'page_url': page_url,
                })
            except Exception as e:
                if debug_mode:
                    print(f"[WARN] Hitmotop: ошибка парсинга трека: {e}")
                continue
        
        return {
            'success': True,
            'tracks': tracks,
            'count': len(tracks),
            'stderr': '',
            'error': ''
        }
        
    except _requests.Timeout:
        return {'success': False, 'tracks': [], 'count': 0, 'error': f'Таймаут {timeout} сек', 'stderr': ''}
    except _requests.RequestException as e:
        return {'success': False, 'tracks': [], 'count': 0, 'error': str(e), 'stderr': ''}
    except Exception as e:
        return {'success': False, 'tracks': [], 'count': 0, 'error': str(e), 'stderr': ''}

def download(url, output_path, artist, track, ffmpeg_path="", use_artist_folders=False, timeout=180, debug_mode=False):
    if not _ensure_deps(debug_mode):
        return {'success': False, 'filepath': None, 'stderr': 'Нет зависимостей', 'returncode': -1}
    
    import re
    try:
        safe_artist = re.sub(r'[^\w\s-]', '', artist)
        safe_track = re.sub(r'[^\w\s-]', '', track)
        
        if use_artist_folders:
            output_dir = os.path.join(output_path, safe_artist)
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f"{safe_artist} - {safe_track}.mp3")
        else:
            output_file = os.path.join(output_path, f"{safe_artist} - {safe_track}.mp3")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Accept-Language': 'ru-RU,ru;q=0.9',
        }
        
        response = _requests.get(url, headers=headers, stream=True, timeout=timeout)
        response.raise_for_status()
        
        with open(output_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        #конвертация если нужна
        file_ext = os.path.splitext(output_file)[1].lower()
        if file_ext != '.mp3' and ffmpeg_path and os.path.exists(ffmpeg_path):
            temp_mp3 = output_file.replace(file_ext, '.mp3')
            cmd = [ffmpeg_path, '-i', output_file, '-vn', '-b:a', '320k', '-y', temp_mp3]
            creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            result = subprocess.run(cmd, capture_output=True, timeout=60, creationflags=creationflags)
            if result.returncode == 0 and os.path.exists(temp_mp3):
                try:
                    os.remove(output_file)
                except:
                    pass
                output_file = temp_mp3
        
        return {
            'success': True,
            'filepath': output_file,
            'stderr': '',
            'stdout': '',
            'returncode': 0
        }
        
    except subprocess.TimeoutExpired:
        return {'success': False, 'filepath': None, 'stderr': f'Таймаут ({timeout} сек)', 'returncode': -1}
    except Exception as e:
        return {'success': False, 'filepath': None, 'stderr': str(e), 'returncode': -1}

def is_region_blocked(track_info, download_result, filepath=None):
    stderr = download_result.get('stderr', '').lower()
    for kw in ['region', 'blocked', 'not available', 'geoblock', 'restricted', 'russia']:
        if kw in stderr:
            return True
    if filepath and os.path.exists(filepath):
        try:
            if os.path.getsize(filepath) < 100 * 1024:
                return True
        except:
            pass
    return False