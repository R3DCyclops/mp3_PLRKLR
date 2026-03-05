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
Метод поиска и скачивания с lmusic.kz
Возвращает список треков с полями: title, uploader, url, id, duration
"""
import subprocess
import sys
import os
import re
import json
import requests
from html import unescape

try:
    from bs4 import BeautifulSoup
    _HAS_BS4 = True
except ImportError:
    _HAS_BS4 = False


def get_ffmpeg_path():
    """Поиск ffmpeg в проекте или в системе"""
    paths = [
        os.path.join(os.path.dirname(__file__), "..", "..", "ffmpeg", "bin", "ffmpeg.exe"),
        os.path.join(os.path.dirname(__file__), "..", "..", "ffmpeg", "ffmpeg.exe"),
        os.path.join(os.path.dirname(__file__), "..", "bin", "ffmpeg.exe"),
        os.path.join(os.path.dirname(__file__), "ffmpeg.exe"),
    ]
    for p in paths:
        if os.path.exists(p):
            return os.path.normpath(p)
    # Поиск в PATH
    try:
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        result = subprocess.run(['where', 'ffmpeg'] if sys.platform == 'win32' else ['which', 'ffmpeg'],
                               capture_output=True, text=True, timeout=5, creationflags=creationflags)
        if result.returncode == 0:
            path = result.stdout.strip().split('\n')[0].strip()
            if os.path.exists(path):
                return path
    except:
        pass
    return ""


def _clean_text(text):
    """Нормализация текста для сравнения"""
    if not text:
        return ""
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'\(.*?\)', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip().lower()


def _parse_html_results(html: str, base_url: str = "https://lmusic.kz") -> list:
    """Парсинг HTML из API ответа"""
    results = []
    
    if _HAS_BS4 and BeautifulSoup:
        soup = BeautifulSoup(html, 'html.parser')
        cards = soup.find_all('a', class_='c-search-card')
        
        for card in cards:
            href = card.get('href', '')
            #Извлекает ID: /mp3/artist-title/217906 - 217906
            match = re.search(r'/(\d+)(?:/|$)', href)
            if not match:
                continue
            track_id = match.group(1)
            
            titles = card.find_all('span', class_='c-search-card__title')
            if len(titles) < 2:
                continue
            
            title_raw = titles[0].get_text(strip=True)
            artist = unescape(titles[1].get_text(strip=True))
            title = re.sub(r'<[^>]+>', '', title_raw).strip()
            title = unescape(title)
            
            results.append({
                'title': title,
                'uploader': artist,
                'url': f'{base_url}/api/download/{track_id}',
                'id': track_id,
                'duration': 0,
                'page_url': f'{base_url}{href}',
            })
    else:
        pattern = r'<a\s+href="(/mp3/[^"]+/(\d+))"[^>]*class="[^"]*c-search-card[^"]*"[^>]*>.*?<strong>([^<]+)</strong>.*?<span[^>]*>([^<]+)</span>'
        for match in re.finditer(pattern, html, re.DOTALL | re.IGNORECASE):
            href, track_id, title, artist = match.groups()
            results.append({
                'title': unescape(title.strip()),
                'uploader': unescape(artist.strip()),
                'url': f'{base_url}/api/download/{track_id}',
                'id': track_id,
                'duration': 0,
                'page_url': f'{base_url}{href}',
            })
    
    return results


def search(query, limit=5, timeout=20, debug_mode=False):
    """
    Поиск треков на lmusic.kz
    
    Args:
        query: Строка поиска (например "МАНДЕЛА - ЯД")
        limit: Максимум результатов
        timeout: Таймаут в секундах
        debug_mode: Режим отладки
        
    Returns:
        dict: {
            'success': bool,
            'tracks': list of dicts with title/uploader/url/id/duration,
            'count': int,
            'error': str (если ошибка),
            'stderr': str
        }
    """
    base_url = "https://lmusic.kz"
    search_url = f"{base_url}/api/typeahead"
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'Referer': f'{base_url}/',
            'X-Requested-With': 'XMLHttpRequest',
        }
        
        params = {'query': query, 'limit': limit}
        
        if debug_mode:
            print(f"[DEBUG] LMUSIC: GET {search_url} params={params}")
        
        response = requests.get(search_url, params=params, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        data = response.json()
        html = data.get('vars', {}).get('html', '')
        
        if not html:
            if debug_mode:
                print(f"[WARN] LMUSIC: пустой HTML в ответе")
            return {'success': True, 'tracks': [], 'count': 0, 'stderr': '', 'error': ''}
        
        tracks = _parse_html_results(html, base_url)
        
        if debug_mode:
            print(f"[DEBUG] LMUSIC: найдено {len(tracks)} треков")
            for t in tracks[:3]:
                print(f"  - {t['uploader']} - {t['title']} (ID: {t['id']})")
        
        return {
            'success': True,
            'tracks': tracks,
            'count': len(tracks),
            'stderr': '',
            'error': ''
        }
        
    except requests.Timeout:
        return {'success': False, 'tracks': [], 'count': 0, 'error': f'Таймаут {timeout} сек', 'stderr': ''}
    except requests.RequestException as e:
        return {'success': False, 'tracks': [], 'count': 0, 'error': str(e), 'stderr': ''}
    except Exception as e:
        return {'success': False, 'tracks': [], 'count': 0, 'error': str(e), 'stderr': ''}


def download(url, output_path, artist, track, ffmpeg_path="", use_artist_folders=False, timeout=180, debug_mode=False):
    """
    Скачивание трека с lmusic.kz
    
    Args:
        url: Ссылка на скачивание (/api/download/{id})
        output_path: Папка для сохранения
        artist: Имя артиста (для имени файла)
        track: Название трека (для имени файла)
        ffmpeg_path: Путь к ffmpeg (не используется, т.к. скачиваем готовый MP3)
        use_artist_folders: Создавать подпапку с именем артиста
        timeout: Таймаут скачивания
        debug_mode: Режим отладки
        
    Returns:
        dict: {
            'success': bool,
            'filepath': str (путь к скачанному файлу),
            'stderr': str,
            'stdout': str,
            'returncode': int
        }
    """
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
            'Referer': 'https://lmusic.kz/',
        }
        
        if debug_mode:
            print(f"[DEBUG] LMUSIC: скачиваю {url} → {output_file}")
        
        response = requests.get(url, headers=headers, stream=True, timeout=timeout)
        response.raise_for_status()
        
        content_type = response.headers.get('Content-Type', '').lower()
        if 'audio/mpeg' not in content_type and not url.endswith('.mp3'):
            if debug_mode:
                print(f"[WARN] LMUSIC: неожиданный Content-Type: {content_type}")
        
        with open(output_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        if os.path.exists(output_file):
            size = os.path.getsize(output_file)
            if size < 10 * 1024:
                if debug_mode:
                    print(f"[WARN] LMUSIC: файл слишком мал ({size} байт), удаляю")
                try:
                    os.remove(output_file)
                except:
                    pass
                return {
                    'success': False,
                    'filepath': None,
                    'stderr': 'Файл слишком мал (возможно ошибка)',
                    'stdout': '',
                    'returncode': -1
                }
        
        return {
            'success': True,
            'filepath': output_file,
            'stderr': '',
            'stdout': '',
            'returncode': 0
        }
        
    except requests.Timeout:
        return {'success': False, 'filepath': None, 'stderr': f'Таймаут скачивания ({timeout} сек)', 'returncode': -1}
    except Exception as e:
        return {'success': False, 'filepath': None, 'stderr': str(e), 'returncode': -1}


def is_region_blocked(track_info, download_result, filepath=None):
    stderr = download_result.get('stderr', '').lower()
    stdout = download_result.get('stdout', '').lower()
    
    region_keywords = [
        'region', 'blocked', 'not available', 'geoblock', 'restricted',
        'russia', 'unavailable', 'access denied', '403', 'forbidden'
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
    
    return False