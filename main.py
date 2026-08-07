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

import os
import importlib.util
import sys
import json
import re
import time
import threading
import subprocess
import shutil
from pathlib import Path
from tkinter import (
    Tk, Frame, Label, Entry, Button, Text, Scrollbar,
    filedialog, messagebox, ttk, END, BooleanVar, Checkbutton, Canvas, Toplevel, Radiobutton, IntVar
)
from rapidfuzz import fuzz, process
from PIL import Image, ImageTk
import requests


from datetime import datetime
import webbrowser
from stratwindow import open_strategy_window

class Colors:
    BG_PRIMARY = "#121212"
    BG_SECONDARY = "#1E1E1E"
    BG_TERTIARY = "#252525"
    BG_HOVER = "#2D2D2D"
    ACCENT_PRIMARY = "#7C3AED"
    ACCENT_HOVER = "#8B5CF6"
    ACCENT_SUCCESS = "#10B981"
    ACCENT_ERROR = "#EF4444"
    ACCENT_WARNING = "#F59E0B"
    TEXT_PRIMARY = "#FFFFFF"
    TEXT_SECONDARY = "#A1A1AA"
    TEXT_MUTED = "#71717A"
    BORDER = "#3F3F46"
    BORDER_FOCUS = "#7C3AED"
    PROGRESS_BG = "#27272A"
    PROGRESS_FG = "#7C3AED"

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

def get_license_text():
    license_filename = "LICENSE"
    
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
        license_path = os.path.join(base_path, license_filename)
        if os.path.exists(license_path):
            with open(license_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            return "Текст лицензии не найден внутри приложения."
    
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        license_path = os.path.join(script_dir, license_filename)
        if os.path.exists(license_path):
            with open(license_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            return "Файл LICENSE не найден рядом со скриптом."

def get_app_directory():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

class Config:
    def __init__(self):
        self.app_dir = get_app_directory()
        self.config_file = os.path.join(self.app_dir, "config.json")
        self.default_config = {
            "match_threshold": 85,
            "delay_between_tracks": 2,
            "search_timeout": 20,
            "download_timeout": 180,
            "audio_format": "mp3",
            "ffmpeg_path": "",
            "debug_mode": False,
            "use_artist_folders": False,
            "selected_strategy": "strat1.txt",
            "last_input_file": "",
            "last_input_file": "",
            "last_output_dir": "",
            "last_iframe_input": ""
        }
        self.config = self.load()

    def load(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return {**self.default_config, **json.load(f)}
            except:
                return self.default_config.copy()
        return self.default_config.copy()

    def save(self):
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save()

class RealTimeLogger:
    def __init__(self, app_dir, input_filename):
        self.app_dir = app_dir
        self.input_filename = input_filename
        self.log_file = os.path.join(app_dir, f"{input_filename}_downloaded.txt")
        self.lost_file = None
        self.lock = threading.Lock()
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write("")

    def _ensure_lost_file(self, output_dir):
        if self.lost_file is None:
            lost_dir = os.path.join(output_dir, "lost")
            os.makedirs(lost_dir, exist_ok=True)
            self.lost_file = os.path.join(lost_dir, f"lost_{self.input_filename}.txt")
            if not os.path.exists(self.lost_file):
                with open(self.lost_file, 'w', encoding='utf-8') as f:
                    f.write("")

    def log_track(self, artist, track, status, score=0, output_dir=None):
        with self.lock:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                if status == 'low_match':
                    f.write(f"{artist} - {track} [low_match]\n")
                elif status == 'not_found':
                    f.write(f"{artist} - {track} [not_found]\n")
                elif status == 'download_error':
                    f.write(f"{artist} - {track} [download_error]\n")
                elif status == 'region_blocked':
                    f.write(f"{artist} - {track} [rg_block]\n")
                elif status == 'downloaded':
                    f.write(f"{artist} - {track}\n")
                elif status == 'skipped':
                    f.write(f"{artist} - {track} [skipped]\n")

            if status in ['not_found', 'low_match', 'download_error', 'region_blocked'] and output_dir:
                self._ensure_lost_file(output_dir)
                if self.lost_file and os.path.exists(self.lost_file):
                    with open(self.lost_file, 'a', encoding='utf-8') as f:
                        if status == 'low_match':
                            f.write(f"{artist} - {track} [low_match]\n")
                        elif status == 'region_blocked':
                            f.write(f"{artist} - {track} [rg_block]\n")
                        else:
                            f.write(f"{artist} - {track}\n")

    def get_downloaded_count(self):
        if not os.path.exists(self.log_file):
            return 0
        count = 0
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and '[not_found]' not in line and '[download_error]' not in line:
                        count += 1
        except Exception:
            pass
        return count

    def is_downloaded(self, artist, track):
        if not os.path.exists(self.log_file):
            return False
        key = f"{artist} - {track}".lower()
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip().lower()
                    if line == key or (line.startswith(key) and '[' not in line):
                        return True
        except Exception:
            pass
        return False

class FFmpegFinder:
    @staticmethod
    def find():
        paths_to_check = [
            resource_path(os.path.join("ffmpeg", "bin", "ffmpeg.exe")),
            resource_path(os.path.join("ffmpeg", "ffmpeg.exe")),
            resource_path(os.path.join("bin", "ffmpeg.exe")),
            resource_path("ffmpeg.exe"),
        ]
        for path in paths_to_check:
            if os.path.exists(path):
                return path
        
        try:
            creationflags = 0
            if sys.platform == 'win32':
                creationflags = subprocess.CREATE_NO_WINDOW
            result = subprocess.run(['where', 'ffmpeg'], capture_output=True, text=True, timeout=5, creationflags=creationflags)
            if result.returncode == 0:
                path = result.stdout.strip().split('\n')[0].strip()
                if os.path.exists(path):
                    return path
        except:
            pass
        return ""
    
    @staticmethod
    def verify(path):
        if not path or not os.path.exists(path):
            return False
        try:
            creationflags = 0
            if sys.platform == 'win32':
                creationflags = subprocess.CREATE_NO_WINDOW
            result = subprocess.run([path, '-version'], capture_output=True, timeout=5, creationflags=creationflags)
            return result.returncode == 0
        except:
            return False

class TrackListParser:
    @staticmethod
    def clean_text(text):
        text = re.sub(r'\[.*?\]', '', text)
        text = re.sub(r'\(.*?\)', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip().lower()

    @staticmethod
    def parse_line(line):
        line = line.strip()
        if not line or line.startswith('#'):
            return None, None
        if ' - ' in line:
            parts = line.split(' - ', 1)
            artist = parts[0].strip()
            track = parts[1].strip()
            return artist, track
        return None, line

    @staticmethod
    def parse_file(filepath):
        tracks = []
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                artist, track = TrackListParser.parse_line(line)
                if artist and track:
                    tracks.append({
                        'line_num': line_num,
                        'artist': artist,
                        'track': track,
                        'original': f"{artist} - {track}",
                        'status': 'pending',
                        'source_url': '',
                        'match_score': 0,
                        'file_path': '',
                        'search_results': [],
                        'error_message': ''
                    })
        return tracks

class YandexMusicExporter:
    @staticmethod
    def export_playlist(owner, kinds):
        return f"playlist_{kinds}", ""

    @staticmethod
    def parse_iframe(iframe_html):
        #ищем UUID в тегах <a href="...playlists/UUID...">
        uuid_match = re.search(r'playlists/([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', iframe_html, re.IGNORECASE)
        if uuid_match:
            uuid = uuid_match.group(1)
            print(f"[DEBUG PARSE_IFRAME] Найден UUID плейлиста: {uuid}")
            return "uuid", uuid
        
        #если формат другой ищем любой UUID в тексте
        any_uuid = re.search(r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', iframe_html, re.IGNORECASE)
        if any_uuid:
            print(f"[DEBUG PARSE_IFRAME] Найден резервный UUID: {any_uuid.group(1)}")
            return "uuid", any_uuid.group(1)
            
        return None, None


class SoundCloudSearcher:
    def __init__(self, ffmpeg_path, debug_mode=False):
        self.debug_mode = debug_mode
        if not ffmpeg_path or not os.path.exists(ffmpeg_path):
            self.ffmpeg_path = FFmpegFinder.find()
        else:
            self.ffmpeg_path = os.path.normpath(ffmpeg_path)
        if not FFmpegFinder.verify(self.ffmpeg_path):
            self.ffmpeg_path = FFmpegFinder.find()

    def search(self, query, limit=5, timeout=20):
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
            if self.debug_mode:
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
                        if self.debug_mode:
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

    def get_file_duration(self, filepath):
        if not os.path.exists(filepath):
            return 0
        try:
            ffprobe_path = self.ffmpeg_path.replace('ffmpeg.exe', 'ffprobe.exe') if self.ffmpeg_path else 'ffprobe'
            cmd = [
                ffprobe_path,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                filepath
            ]
            creationflags = 0
            if sys.platform == 'win32':
                creationflags = subprocess.CREATE_NO_WINDOW
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, encoding='utf-8', creationflags=creationflags)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                duration = float(data.get('format', {}).get('duration', 0))
                return duration * 1000
        except Exception as e:
            return 0
        return 0

    def is_region_blocked(self, track_info, download_result, filepath=None):
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
        
        if filepath:
            for _ in range(10):
                if os.path.exists(filepath):
                    break
                time.sleep(0.5)
            if os.path.exists(filepath):
                actual_duration = self.get_file_duration(filepath)
                if actual_duration and actual_duration < 35000:
                    return True
        
        duration = track_info.get('duration', 0)
        if duration and duration < 35000:
            format_id = track_info.get('format_id', '').lower()
            if 'preview' in format_id or 'snippet' in format_id:
                return True
        
        return False

    def find_best_match(self, target_artist, target_track, search_results, threshold=85):
        best_score = 0
        best_track = None
        target_artist_clean = TrackListParser.clean_text(target_artist)
        target_track_clean = TrackListParser.clean_text(target_track)
        
        for item in search_results:
            uploader = item.get('uploader', '')
            title = item.get('title', '')
            score_track = fuzz.ratio(TrackListParser.clean_text(title), target_track_clean)
            score_artist = fuzz.ratio(TrackListParser.clean_text(uploader), target_artist_clean)
            total_score = (score_track * 0.7) + (score_artist * 0.3)
            if total_score > best_score:
                best_score = total_score
                best_track = item
        
        return best_track, best_score

    def download(self, url, output_path, artist, track, use_artist_folders=False, timeout=180):
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
            if self.ffmpeg_path and os.path.exists(self.ffmpeg_path):
                cmd.extend(['--ffmpeg-location', self.ffmpeg_path])
            if self.debug_mode:
                cmd.append('--verbose')
            
            creationflags = 0
            if sys.platform == 'win32':
                creationflags = subprocess.CREATE_NO_WINDOW
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout, creationflags=creationflags)
            stderr = result.stderr[:1000] if result.stderr else ''
            stdout = result.stdout[:500] if result.stdout else ''
            return {'success': result.returncode == 0, 'stderr': stderr, 'stdout': stdout, 'returncode': result.returncode}
        except subprocess.TimeoutExpired:
            return {'success': False, 'stderr': f'Таймаут скачивания ({timeout} сек)', 'returncode': -1}
        except Exception as e:
            return {'success': False, 'stderr': str(e), 'returncode': -1}

class DownloadManager:
    def __init__(self, config, app_dir):
        self.config = config
        self.app_dir = app_dir
        self.searcher = SoundCloudSearcher(config.get('ffmpeg_path', ''), config.get('debug_mode', False))
        self.tracks = []
        self.output_dir = ""
        self.input_filename = ""
        self.stop_flag = False
        self.logger = None
        self.stats = {'downloaded': 0, 'not_found': 0, 'low_match': 0, 'download_error': 0, 'stopped': 0, 'skipped': 0}
        self.strategy_methods = []
        self.load_strategy()

    def load_strategy(self):
        strategy_file = self.config.get('selected_strategy', 'strat1.txt')
        
        if getattr(sys, 'frozen', False):
            strat_dir = os.path.join(sys._MEIPASS, "strat")
        else:
            strat_dir = os.path.join(self.app_dir, "strat")
        
        strat_path = os.path.join(strat_dir, strategy_file)
        
        if not os.path.exists(strat_path):
            print(f"[WARN] Стратегия не найдена: {strat_path}")
            self.strategy_methods = ['soundcloud.py']
            return
        
        try:
            with open(strat_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if len(lines) >= 2:
                    methods_line = lines[1].strip()
                    self.strategy_methods = [m.strip() for m in methods_line.split('+')]
                else:
                    self.strategy_methods = ['soundcloud.py']
        except Exception as e:
            print(f"[ERROR] Ошибка загрузки стратегии: {e}")
            self.strategy_methods = ['soundcloud.py']
        
        print(f"[INFO] Загружена стратегия: {strategy_file} -> {self.strategy_methods}")

    def load_tracks(self, filepath):
        self.tracks = TrackListParser.parse_file(filepath)
        self.input_filename = Path(filepath).stem
        self.logger = RealTimeLogger(self.app_dir, self.input_filename)
        return len(self.tracks)

    def set_output_dir(self, output_dir):
        self.output_dir = os.path.join(output_dir, self.input_filename)
        os.makedirs(self.output_dir, exist_ok=True)
        self.lost_dir = os.path.join(self.output_dir, "lost")
        os.makedirs(self.lost_dir, exist_ok=True)
        self.low_match_dir = os.path.join(self.output_dir, "low_match")
        os.makedirs(self.low_match_dir, exist_ok=True)

    def process_all(self, callback=None):
        total = len(self.tracks)
        search_timeout = self.config.get('search_timeout', 20)
        download_timeout = self.config.get('download_timeout', 180)
        use_artist_folders = self.config.get('use_artist_folders', False)
        threshold = self.config.get('match_threshold', 85)
        MIN_DOWNLOAD_SCORE = 40
        
        method_modules = {}
        if getattr(sys, 'frozen', False):
            methods_dir = os.path.join(sys._MEIPASS, "strat", "methods")
        else:
            methods_dir = os.path.join(self.app_dir, "strat", "methods")
        
        for method_file in self.strategy_methods:
            method_name = method_file.replace('.py', '')
            try:
                spec = importlib.util.spec_from_file_location(method_name, os.path.join(methods_dir, method_file))
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                method_modules[method_file] = module
                print(f"[INFO] Загружен метод: {method_file}")
            except Exception as e:
                print(f"[ERROR] Не удалось загрузить метод {method_file}: {e}")
        
        for i, track in enumerate(self.tracks):
            if self.stop_flag:
                track['status'] = 'stopped'
                self.stats['stopped'] += 1
                continue
            
            artist = track['artist']
            title = track['track']
            
            #проверка на скачанный
            if self.logger and self.logger.is_downloaded(artist, title):
                track['status'] = 'skipped'
                self.stats['skipped'] += 1
                if self.logger:
                    self.logger.log_track(artist, title, 'skipped')
                if callback:
                    callback(i + 1, total, track, None)
                continue
            
            query = f"{artist} {title}"
            
            best_match = None
            best_score = 0
            best_method = None
            found_above_threshold = False
            
            all_search_results = {}
            
            for method_file in self.strategy_methods:
                if found_above_threshold:
                    break
                    
                if method_file not in method_modules:
                    continue
                
                module = method_modules[method_file]
                
                try:
                    search_result = module.search(query, limit=5, timeout=search_timeout, debug_mode=self.config.get('debug_mode', False))
                    
                    all_search_results[method_file] = search_result
                    
                    if not search_result['success'] or search_result['count'] == 0:
                        continue
                    
                    method_best, method_score = self.searcher.find_best_match(artist, title, search_result['tracks'], threshold=threshold)
                    
                    if method_score > best_score:
                        best_score = method_score
                        best_match = method_best
                        best_method = method_file
                    
                    if method_score >= threshold:
                        found_above_threshold = True
                        if self.config.get('debug_mode', False):
                            print(f"[DEBUG] {method_file}: найден матч {method_score:.1f}% >= {threshold}% — остановка поиска")
                        break
                        
                except Exception as e:
                    print(f"[ERROR] Ошибка метода {method_file}: {e}")
                    all_search_results[method_file] = {'success': False, 'count': 0, 'tracks': []}
                    continue
            
            track['match_score'] = best_score
        
            if best_match and best_score >= MIN_DOWNLOAD_SCORE:
                if best_score >= threshold:
                    download_path = self.output_dir
                    log_status = 'downloaded'
                else:
                    download_path = self.low_match_dir
                    log_status = 'low_match'
                
                if best_method and best_method in method_modules:
                    module = method_modules[best_method]
                    download_result = module.download(
                        best_match['url'],
                        download_path,
                        artist,
                        title,
                        ffmpeg_path=self.searcher.ffmpeg_path,
                        use_artist_folders=use_artist_folders,
                        timeout=download_timeout,
                        debug_mode=self.config.get('debug_mode', False)
                    )
                    
                    if download_result['success']:
                        actual_filepath = download_result.get('filepath')
                        
                        if self.searcher.is_region_blocked(best_match, download_result, filepath=actual_filepath):
                            track['status'] = 'region_blocked'
                            track['error_message'] = 'Трека нет в вашем регионе'
                            self.stats['not_found'] += 1
                            if actual_filepath and os.path.exists(actual_filepath):
                                try:
                                    os.remove(actual_filepath)
                                except:
                                    pass
                            if self.logger:
                                self.logger.log_track(artist, title, 'region_blocked', output_dir=self.output_dir)
                        else:
                            track['status'] = log_status
                            track['source_url'] = best_match['url']
                            track['file_path'] = actual_filepath
                            if log_status == 'downloaded':
                                self.stats['downloaded'] += 1
                            else:
                                self.stats['low_match'] += 1
                            if self.logger:
                                self.logger.log_track(artist, title, log_status, best_score, output_dir=self.output_dir)
                    else:
                        track['status'] = 'download_error'
                        track['error_message'] = download_result.get('stderr', '')[:200]
                        self.stats['download_error'] += 1
                        if self.logger:
                            self.logger.log_track(artist, title, 'download_error', output_dir=self.output_dir)
                else:
                    track['status'] = 'download_error'
                    track['error_message'] = 'Нет доступного метода для скачивания'
                    self.stats['download_error'] += 1
            else:
                track['status'] = 'not_found'
                track['error_message'] = f'Не найдено ни в одном методе (лучший: {best_score}%)'
                self.stats['not_found'] += 1
                if self.logger:
                    self.logger.log_track(artist, title, 'not_found', output_dir=self.output_dir)
            
            if callback:
                callback(i + 1, total, track, {'count': sum(r.get('count', 0) for r in all_search_results.values())})
            
            time.sleep(self.config.get('delay_between_tracks', 2))
        
        self.save_report()

    def save_report(self):
        report_path = os.path.join(self.output_dir, "download_report.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump({'stats': self.stats, 'tracks': self.tracks}, f, indent=2, ensure_ascii=False)

    def stop(self):
        self.stop_flag = True

class ModernButton(Button):
    def __init__(self, master, text, command, bg=Colors.ACCENT_PRIMARY, fg=Colors.TEXT_PRIMARY, **kwargs):
        super().__init__(
            master,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            font=('Segoe UI', 10, 'bold'),
            relief='flat',
            cursor='hand2',
            padx=20,
            pady=10,
            **kwargs
        )
        self.bind('<Enter>', self.on_enter)
        self.bind('<Leave>', self.on_leave)
        self.default_bg = bg
        self.hover_bg = Colors.ACCENT_HOVER

    def on_enter(self, e):
        self.config(bg=self.hover_bg)

    def on_leave(self, e):
        self.config(bg=self.default_bg)

class ModernEntry(Entry):
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            bg=Colors.BG_TERTIARY,
            fg=Colors.TEXT_PRIMARY,
            insertbackground=Colors.TEXT_PRIMARY,
            font=('Segoe UI', 10),
            relief='flat',
            highlightthickness=1,
            highlightbackground=Colors.BORDER,
            highlightcolor=Colors.BORDER_FOCUS,
            **kwargs
        )

class ModernCheckbutton(Checkbutton):
    def __init__(self, master, text, variable, **kwargs):
        super().__init__(
            master,
            text=text,
            variable=variable,
            bg=Colors.BG_SECONDARY,
            fg=Colors.TEXT_SECONDARY,
            font=('Segoe UI', 9),
            selectcolor=Colors.BG_TERTIARY,
            activebackground=Colors.BG_SECONDARY,
            activeforeground=Colors.TEXT_PRIMARY,
            relief='flat',
            cursor='hand2',
            **kwargs
        )

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("mp3_plrklr")
        self.root.geometry("1000x900")
        self.root.resizable(False, False)
        
        icon_path = resource_path("ico.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(default=icon_path) 
            except Exception as e:
                print(f"[WARN] Не удалось установить иконку: {e}")
        
        self.root.configure(bg=Colors.BG_PRIMARY)
        self.setup_styles()
        
        self.config = Config()
        self.app_dir = get_app_directory()
        
        default_downloads = os.path.join(self.app_dir, "downloads")
        os.makedirs(default_downloads, exist_ok=True)  
        
        saved_output = self.config.get('last_output_dir', '')
        if not saved_output or not os.path.exists(saved_output):
            self.config.set('last_output_dir', default_downloads)
        
        self.manager = DownloadManager(self.config, self.app_dir)
        
        self.selected_strategy = self.config.get('selected_strategy', 'strat1.txt')
        
        self.download_thread = None
        self.input_mode = IntVar(value=0)
        self.previous_input_mode = 0
        self.txt_input_value = ""
        self.ym_input_value = ""
        self.temp_playlist_file = None
        self.temp_dir = None
        
        self.setup_ui()

    def is_ru_lang_keyboard(self):
        """Проверка кириллицы в раскладке"""
        try:
            import ctypes
            u = ctypes.windll.LoadLibrary("user32.dll")
            pf = getattr(u, "GetKeyboardLayout")
            return hex(pf(0)) == '0x4190419'
        except:
            return False

    def setup_copy_paste_fix(self, widget):
        """Фикс копипаст любой раскладки"""
        def keys(event):
            if event.keycode == 86:  #V
                try:
                    widget.event_generate("<<Paste>>")
                except:
                    pass
                return 'break'
            if event.keycode == 67:  #C
                try:
                    widget.event_generate("<<Copy>>")
                except:
                    pass
                return 'break'
            if event.keycode == 88:  #X
                try:
                    widget.event_generate("<<Cut>>")
                except:
                    pass
                return 'break'
            if event.keycode == 65:  #A
                try:
                    widget.event_generate("<<SelectAll>>")
                except:
                    pass
                return 'break'
            return None
        
        widget.bind("<Control-KeyPress>", keys)

    def open_strategy_selector(self):
        selected = open_strategy_window(self.root, self.app_dir, self.selected_strategy)
        if selected and selected != self.selected_strategy:
            self.selected_strategy = selected
            self.config.set('selected_strategy', selected)
            self.manager.load_strategy()
            self.log(f"[INFO] Стратегия изменена на: {selected} -> {self.manager.strategy_methods}")

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background=Colors.BG_PRIMARY)
        style.configure("TLabel", background=Colors.BG_PRIMARY, foreground=Colors.TEXT_SECONDARY, font=('Segoe UI', 9))
        style.configure("Title.TLabel", background=Colors.BG_PRIMARY, foreground=Colors.TEXT_PRIMARY, font=('Segoe UI', 14, 'bold'))
        style.configure("TProgressbar", background=Colors.PROGRESS_FG, troughcolor=Colors.PROGRESS_BG, borderwidth=0, lightcolor=Colors.PROGRESS_FG, darkcolor=Colors.PROGRESS_FG)
        style.configure("TSpinbox", fieldbackground=Colors.BG_TERTIARY, foreground=Colors.TEXT_PRIMARY, background=Colors.BG_TERTIARY, arrowcolor=Colors.TEXT_SECONDARY, bordercolor=Colors.BORDER, darkcolor=Colors.BORDER, lightcolor=Colors.BORDER, font=('Segoe UI', 10))
        style.configure("TCombobox", fieldbackground=Colors.BG_TERTIARY, background=Colors.BG_SECONDARY, arrowcolor=Colors.TEXT_SECONDARY)

    def setup_ui(self):
        main_container = Frame(self.root, bg=Colors.BG_PRIMARY)
        main_container.pack(fill='both', expand=True, padx=20, pady=20)
        
        header_frame = Frame(main_container, bg=Colors.BG_PRIMARY)
        header_frame.pack(fill='x', pady=(0, 20))
        
        left_frame = Frame(header_frame, bg=Colors.BG_PRIMARY)
        left_frame.pack(side='left')
        
        title_inner = Frame(left_frame, bg=Colors.BG_PRIMARY)
        title_inner.pack(anchor='w')
        Label(title_inner, text="mp3_", font=('Segoe UI', 24, 'bold'), bg=Colors.BG_PRIMARY, fg="#ff3a3a").pack(side='left')
        Label(title_inner, text="PLRKLR", font=('Segoe UI', 24, 'bold'), bg=Colors.BG_PRIMARY, fg=Colors.TEXT_PRIMARY).pack(side='left')
        Label(left_frame, text="You don't know us.", font=('Segoe UI', 10), bg=Colors.BG_PRIMARY, fg=Colors.TEXT_MUTED).pack(anchor='w')
        
        about_label = Label(
            left_frame,
            text="о программе",
            font=('Segoe UI', 9),
            bg=Colors.BG_PRIMARY,
            fg="#555555",
            cursor="hand2"
        )
        about_label.pack(anchor='w', pady=(2, 0))
        about_label.bind('<Button-1>', lambda e: self.show_about())
        about_label.bind('<Enter>', lambda e: about_label.config(fg=Colors.ACCENT_PRIMARY))
        about_label.bind('<Leave>', lambda e: about_label.config(fg="#555555"))
        
        self.made_by_label = Label(
            header_frame,
            text="made by m0reslav",
            font=('Segoe UI', 10),
            bg=Colors.BG_PRIMARY,
            fg=Colors.TEXT_MUTED,
            cursor='hand2'
        )
        self.made_by_label.pack(side='left', padx=20, pady=8)
        
        self.strategy_btn = ModernButton(
            header_frame,
            text="Стратегия",
            command=self.open_strategy_selector,
            bg=Colors.BG_TERTIARY,
            fg=Colors.TEXT_PRIMARY
        )
        self.strategy_btn.pack(side='left', padx=10)
        
        self.made_by_label.bind('<Button-1>', lambda e: webbrowser.open('https://moreslav.ru/'))
        self.made_by_label.bind('<Enter>', lambda e: self.made_by_label.config(fg=Colors.ACCENT_PRIMARY))
        self.made_by_label.bind('<Leave>', lambda e: self.made_by_label.config(fg=Colors.TEXT_MUTED))
        
        try:
            logo_path = resource_path("logo.png")
            if os.path.exists(logo_path):
                logo_img = Image.open(logo_path)
                logo_img = logo_img.resize((75, 75), Image.Resampling.LANCZOS)
                self.logo_photo = ImageTk.PhotoImage(logo_img)
                self.logo_label = Label(header_frame, image=self.logo_photo, bg=Colors.BG_PRIMARY, cursor="hand2")
                self.logo_label.pack(side='right', padx=10)
                self.logo_label.bind('<Button-1>', lambda e: self.show_cheat_input())
                self.logo_label.bind('<Enter>', lambda e: self.logo_label.config(bg=Colors.BG_TERTIARY))
                self.logo_label.bind('<Leave>', lambda e: self.logo_label.config(bg=Colors.BG_PRIMARY))
        except Exception as e:
            print(f"[WARN] Не удалось загрузить логотип: {e}")
        
        settings_panel = Frame(main_container, bg=Colors.BG_SECONDARY)
        settings_panel.pack(fill='x', pady=(0, 15))
        
        settings_inner = Frame(settings_panel, bg=Colors.BG_SECONDARY)
        settings_inner.pack(fill='x', padx=20, pady=20)
        
        settings_inner.grid_columnconfigure(0, weight=1)
        settings_inner.grid_columnconfigure(1, weight=0)
        settings_inner.grid_columnconfigure(2, weight=0)
        settings_inner.grid_columnconfigure(3, weight=0)
        
        mode_frame = Frame(settings_inner, bg=Colors.BG_SECONDARY)
        mode_frame.grid(row=0, column=0, columnspan=4, sticky='w', pady=(0, 10))
        
        Label(mode_frame, text="Источник:", font=('Segoe UI', 9, 'bold'), bg=Colors.BG_SECONDARY, fg=Colors.TEXT_PRIMARY).pack(side='left', padx=(0, 15))
        
        self.radio_ym = Radiobutton(
            mode_frame,
            text="Плейлист ЯМ",
            variable=self.input_mode,
            value=0,
            bg=Colors.BG_SECONDARY,
            fg=Colors.TEXT_SECONDARY,
            font=('Segoe UI', 9),
            selectcolor=Colors.BG_TERTIARY,
            activebackground=Colors.BG_SECONDARY,
            activeforeground=Colors.TEXT_PRIMARY,
            cursor='hand2',
            command=self.on_mode_change
        )
        self.radio_ym.pack(side='left', padx=(0, 20))
        
        self.radio_txt = Radiobutton(
            mode_frame,
            text="Список треков",
            variable=self.input_mode,
            value=1,
            bg=Colors.BG_SECONDARY,
            fg=Colors.TEXT_SECONDARY,
            font=('Segoe UI', 9),
            selectcolor=Colors.BG_TERTIARY,
            activebackground=Colors.BG_SECONDARY,
            activeforeground=Colors.TEXT_PRIMARY,
            cursor='hand2',
            command=self.on_mode_change
        )
        self.radio_txt.pack(side='left')
        
        self.input_label = Label(
            settings_inner,
            text="Список треков:",
            font=('Segoe UI', 9, 'bold'),
            bg=Colors.BG_SECONDARY,
            fg=Colors.TEXT_PRIMARY
        )
        self.input_label.grid(row=1, column=0, sticky='w', pady=(0, 5))
        
        self.input_entry = ModernEntry(settings_inner, width=60)
        self.input_entry.grid(row=2, column=0, padx=(0, 10), sticky='ew')
        
        self.browse_input_btn = ModernButton(
            settings_inner,
            text="Обзор",
            command=self.browse_input,
            bg=Colors.BG_TERTIARY,
            fg=Colors.TEXT_PRIMARY
        )
        self.browse_input_btn.grid(row=2, column=1)
        
        self.start_button = ModernButton(
            settings_inner,
            text="Начать",
            command=self.start_download,
            bg=Colors.ACCENT_PRIMARY,
            fg=Colors.TEXT_PRIMARY
        )
        self.start_button.grid(row=2, column=2, padx=(10, 5))
        
        self.stop_button = ModernButton(
            settings_inner,
            text="Стоп",
            command=self.stop_download,
            bg=Colors.ACCENT_ERROR,
            fg=Colors.TEXT_PRIMARY,
            state='disabled'
        )
        self.stop_button.grid(row=2, column=3, padx=5)
        
        self.output_label = Label(
            settings_inner,
            text="Папка загрузки:",
            font=('Segoe UI', 9, 'bold'),
            bg=Colors.BG_SECONDARY,
            fg=Colors.TEXT_PRIMARY
        )
        self.output_label.grid(row=3, column=0, sticky='w', pady=(15, 5))
        
        self.output_entry = ModernEntry(settings_inner, width=60)
        self.output_entry.grid(row=4, column=0, padx=(0, 10), sticky='ew')
        
        self.browse_output_btn = ModernButton(
            settings_inner,
            text="Обзор",
            command=self.browse_output,
            bg=Colors.BG_TERTIARY,
            fg=Colors.TEXT_PRIMARY
        )
        self.browse_output_btn.grid(row=4, column=1)
        
        self.open_folder_btn = ModernButton(
            settings_inner,
            text="Открыть",
            command=self.open_output_folder,
            bg=Colors.BG_TERTIARY,
            fg=Colors.TEXT_PRIMARY
        )
        self.open_folder_btn.grid(row=4, column=2, padx=(10, 5), columnspan=2)
        
        options_frame = Frame(settings_inner, bg=Colors.BG_SECONDARY)
        options_frame.grid(row=5, column=0, columnspan=2, sticky='w', pady=(20, 0))
        
        settings_configs = [
            ("Порог совпадения:", 50, 100, 85),
            ("Задержка (сек):", 0, 30, 2),
            ("Таймаут (сек):", 10, 120, 20),
        ]
        for i, (label_text, from_val, to_val, default_val) in enumerate(settings_configs):
            col_frame = Frame(options_frame, bg=Colors.BG_SECONDARY)
            col_frame.grid(row=0, column=i, padx=(0, 30), sticky='w')
            Label(col_frame, text=label_text, font=('Segoe UI', 9), bg=Colors.BG_SECONDARY, fg=Colors.TEXT_SECONDARY).pack(anchor='w')
            var_obj = ttk.Spinbox(col_frame, from_=from_val, to=to_val, width=8, style="TSpinbox")
            var_obj.set(default_val)
            var_obj.pack(anchor='w', pady=(5, 0))
            if i == 0:
                self.threshold_var = var_obj
            elif i == 1:
                self.delay_var = var_obj
            else:
                self.timeout_var = var_obj
        
        checkboxes_frame = Frame(options_frame, bg=Colors.BG_SECONDARY)
        checkboxes_frame.grid(row=0, column=3, padx=(30, 0), sticky='w')
        
        self.debug_var = BooleanVar(value=self.config.get('debug_mode', False))
        debug_cb = ModernCheckbutton(checkboxes_frame, text="Режим отладки (для разработчиков)", variable=self.debug_var)
        debug_cb.pack(anchor='w', pady=(0, 5))
        
        self.artist_folders_var = BooleanVar(value=self.config.get('use_artist_folders', False))
        artist_cb = ModernCheckbutton(checkboxes_frame, text="Папки артистов", variable=self.artist_folders_var)
        artist_cb.pack(anchor='w')
        
        progress_panel = Frame(main_container, bg=Colors.BG_SECONDARY)
        progress_panel.pack(fill='x', pady=(0, 15))
        
        progress_inner = Frame(progress_panel, bg=Colors.BG_SECONDARY)
        progress_inner.pack(fill='x', padx=20, pady=20)
        
        self.progress = ttk.Progressbar(progress_inner, mode='determinate', length=0)
        self.progress.pack(fill='x', pady=(0, 10))
        
        self.status_label = Label(progress_inner, text="Готов к загрузке", font=('Segoe UI', 10), bg=Colors.BG_SECONDARY, fg=Colors.TEXT_SECONDARY)
        self.status_label.pack(anchor='w')
        
        stats_panel = Frame(main_container, bg=Colors.BG_SECONDARY)
        stats_panel.pack(fill='x', pady=(0, 15))
        
        stats_inner = Frame(stats_panel, bg=Colors.BG_SECONDARY)
        stats_inner.pack(fill='x', padx=20, pady=15)
        
        self.stats_vars = {}
        stats_items = [
            ('downloaded', 'Скачано', Colors.ACCENT_SUCCESS),
            ('skipped', 'Пропущено', Colors.TEXT_MUTED),
            ('not_found', 'Не найдено', Colors.ACCENT_ERROR),
            ('low_match', 'Low Match', Colors.ACCENT_WARNING),
            ('download_error', 'Ошибки', Colors.ACCENT_ERROR),
        ]
        for i, (key, label, color) in enumerate(stats_items):
            stat_frame = Frame(stats_inner, bg=Colors.BG_TERTIARY)
            stat_frame.grid(row=0, column=i, padx=(0, 10), sticky='ew')
            stats_inner.grid_columnconfigure(i, weight=1)
            Label(stat_frame, text=label, font=('Segoe UI', 8), bg=Colors.BG_TERTIARY, fg=Colors.TEXT_MUTED).pack(pady=(8, 2))
            value_label = Label(stat_frame, text="0", font=('Segoe UI', 18, 'bold'), bg=Colors.BG_TERTIARY, fg=color)
            value_label.pack()
            self.stats_vars[key] = value_label
        
        log_panel = Frame(main_container, bg=Colors.BG_SECONDARY)
        log_panel.pack(fill='both', expand=True)
        
        log_inner = Frame(log_panel, bg=Colors.BG_SECONDARY)
        log_inner.pack(fill='both', expand=True, padx=20, pady=20)
        
        Label(log_inner, text="Лог операций", font=('Segoe UI', 10, 'bold'), bg=Colors.BG_SECONDARY, fg=Colors.TEXT_PRIMARY).pack(anchor='w', pady=(0, 10))
        
        log_container = Frame(log_inner, bg=Colors.BG_TERTIARY)
        log_container.pack(fill='both', expand=True)
        
        self.log_text = Text(log_container, font=('Consolas', 9), bg=Colors.BG_TERTIARY, fg=Colors.TEXT_SECONDARY, insertbackground=Colors.TEXT_PRIMARY, relief='flat', highlightthickness=0, spacing1=4, spacing2=2, spacing3=4)
        self.log_text.pack(side='left', fill='both', expand=True, padx=(1, 0), pady=(1, 0))
        
        log_scrollbar = Scrollbar(log_container, command=self.log_text.yview, bg=Colors.BG_SECONDARY, activebackground=Colors.BORDER, troughcolor=Colors.BG_SECONDARY, borderwidth=0)
        log_scrollbar.pack(side='right', fill='y')
        self.log_text.config(yscrollcommand=log_scrollbar.set)
        
        if self.config.get('last_input_file'):
            self.input_entry.insert(0, self.config.get('last_input_file'))
        
        self.output_entry.insert(0, self.config.get('last_output_dir', ''))
        
        if self.config.get('last_iframe_input') and self.input_mode.get() == 0:
            self.input_entry.insert(0, self.config.get('last_iframe_input'))
        
        self.on_mode_change()
        self.setup_copy_paste_fix(self.input_entry)
        self.setup_copy_paste_fix(self.output_entry)

    def show_about(self):
        about_win = Toplevel(self.root)
        about_win.title("О программе")
        about_win.geometry("400x300")
        about_win.resizable(False, False)
        about_win.configure(bg=Colors.BG_SECONDARY)
        
        icon_path = resource_path("ico.ico")
        if os.path.exists(icon_path):
            try:
                about_win.iconbitmap(icon_path)
            except:
                pass

        about_win.update_idletasks()
        x = (about_win.winfo_screenwidth() - 400) // 2
        y = (about_win.winfo_screenheight() - 300) // 2
        about_win.geometry(f"400x300+{x}+{y}")

        container = Frame(about_win, bg=Colors.BG_SECONDARY)
        container.pack(fill='both', expand=True, padx=20, pady=20)

        title_frame = Frame(container, bg=Colors.BG_SECONDARY)
        title_frame.pack(pady=(10, 5))

        Label(
            title_frame,
            text="mp3_",
            font=('Segoe UI', 20, 'bold'),
            bg=Colors.BG_SECONDARY,
            fg="#ff3a3a"
        ).pack(side='left')

        Label(
            title_frame,
            text="PLRKLR",
            font=('Segoe UI', 20, 'bold'),
            bg=Colors.BG_SECONDARY,
            fg=Colors.TEXT_PRIMARY
        ).pack(side='left')

        copyright_lbl = Label(
            container,
            text="Copyright (C) 2026 m0reslav",
            font=('Segoe UI', 10),
            bg=Colors.BG_SECONDARY,
            fg=Colors.TEXT_SECONDARY
        )
        copyright_lbl.pack(pady=(0, 20))

        desc_lbl = Label(
            container,
            text="Это свободное ПО, распространяемое под лицензией GPL v3.",
            font=('Segoe UI', 9),
            bg=Colors.BG_SECONDARY,
            fg=Colors.TEXT_MUTED,
            wraplength=350,
            justify='center'
        )
        desc_lbl.pack(pady=(0, 20))

        license_btn = Label(
            container,
            text="LICENSE",
            font=('Segoe UI', 10, 'underline'),
            bg=Colors.BG_SECONDARY,
            fg=Colors.ACCENT_PRIMARY,
            cursor="hand2"
        )
        license_btn.pack(pady=(10, 0))
        license_btn.bind('<Button-1>', lambda e: self.show_license(about_win))
        license_btn.bind('<Enter>', lambda e: license_btn.config(fg=Colors.ACCENT_HOVER))
        license_btn.bind('<Leave>', lambda e: license_btn.config(fg=Colors.ACCENT_PRIMARY))

        close_btn = ModernButton(container, text="Закрыть", command=about_win.destroy, bg=Colors.BG_TERTIARY)
        close_btn.pack(pady=(20, 0))

    def show_license(self, parent_win):
        license_win = Toplevel(parent_win)
        license_win.title("GNU General Public License v3")
        license_win.geometry("600x500")
        license_win.configure(bg=Colors.BG_SECONDARY)
        
        icon_path = resource_path("ico.ico")
        if os.path.exists(icon_path):
            try:
                license_win.iconbitmap(icon_path)
            except:
                pass

        license_win.update_idletasks()
        x = (license_win.winfo_screenwidth() - 600) // 2
        y = (license_win.winfo_screenheight() - 500) // 2
        license_win.geometry(f"600x500+{x}+{y}")

        text_frame = Frame(license_win, bg=Colors.BG_TERTIARY)
        text_frame.pack(fill='both', expand=True, padx=10, pady=10)

        license_text_widget = Text(text_frame, font=('Consolas', 9), bg=Colors.BG_TERTIARY, fg=Colors.TEXT_SECONDARY, wrap='word', relief='flat', highlightthickness=0)
        license_text_widget.pack(side='left', fill='both', expand=True)

        scrollbar = Scrollbar(text_frame, command=license_text_widget.yview, bg=Colors.BG_SECONDARY, activebackground=Colors.BORDER, troughcolor=Colors.BG_SECONDARY, borderwidth=0)
        scrollbar.pack(side='right', fill='y')
        license_text_widget.config(yscrollcommand=scrollbar.set)

        content = get_license_text()
        license_text_widget.insert(END, content)
        license_text_widget.config(state='disabled')

        close_btn = ModernButton(license_win, text="Закрыть", command=license_win.destroy, bg=Colors.BG_TERTIARY)
        close_btn.pack(pady=(0, 10))

    def on_mode_change(self):
        current_value = self.input_entry.get()
        
        if self.previous_input_mode == 1:
            self.txt_input_value = current_value
        else:
            self.ym_input_value = current_value
        
        self.previous_input_mode = self.input_mode.get()
        
        if self.input_mode.get() == 0:
            self.input_label.config(text="Вставьте iframe плейлиста:")
            self.browse_input_btn.grid_remove()
            
            self.input_entry.delete(0, END)
            self.input_entry.insert(0, self.ym_input_value)
            
            if not hasattr(self, 'ym_help_label') or not self.ym_help_label:
                self.ym_help_label = Label(
                    self.input_entry.master,
                    text="Что такое iframe плейлиста?",
                    font=('Segoe UI', 9),
                    bg=Colors.BG_SECONDARY,
                    fg=Colors.ACCENT_PRIMARY,
                    cursor="hand2"
                )
                self.ym_help_label.grid(row=3, column=0, sticky='w', pady=(5, 0))
                self.ym_help_label.bind('<Button-1>', lambda e: self.show_iframe_help())
                self.ym_help_label.bind('<Enter>', lambda e: self.ym_help_label.config(fg=Colors.ACCENT_HOVER))
                self.ym_help_label.bind('<Leave>', lambda e: self.ym_help_label.config(fg=Colors.ACCENT_PRIMARY))
            else:
                self.ym_help_label.grid()
        else:
            self.input_label.config(text="Список треков:")
            self.browse_input_btn.grid()
            
            self.input_entry.delete(0, END)
            self.input_entry.insert(0, self.txt_input_value)
            
            if hasattr(self, 'ym_help_label') and self.ym_help_label:
                self.ym_help_label.grid_remove()
                
    def show_iframe_help(self):
        help_window = Toplevel(self.root)
        help_window.title("Что такое iframe плейлиста?")
        help_window.geometry("720x720")
        help_window.resizable(False, False)
        help_window.configure(bg=Colors.BG_SECONDARY)
        
        icon_path = resource_path("ico.ico")
        if os.path.exists(icon_path):
            help_window.iconbitmap(icon_path)
        
        help_window.update_idletasks()
        x = (help_window.winfo_screenwidth() - 720) // 2
        y = (help_window.winfo_screenheight() - 720) // 2
        help_window.geometry(f"500x720+{x}+{y}")
        
        canvas = Canvas(help_window, bg=Colors.BG_SECONDARY, highlightthickness=0)
        canvas.pack(side='left', fill='both', expand=True)
        
        scrollbar = Scrollbar(help_window, command=canvas.yview, bg=Colors.BG_TERTIARY)
        scrollbar.pack(side='right', fill='y')
        
        canvas.configure(yscrollcommand=scrollbar.set)
        
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        def on_close():
            canvas.unbind_all("<MouseWheel>")
            help_window.destroy()
        
        help_window.protocol("WM_DELETE_WINDOW", on_close)
        
        help_frame = Frame(canvas, bg=Colors.BG_SECONDARY)
        canvas.create_window((0, 0), window=help_frame, anchor='nw', width=480)
        
        title_label = Label(
            help_frame,
            text="Как получить iframe плейлиста Яндекс Музыки",
            font=('Segoe UI', 12, 'bold'),
            bg=Colors.BG_SECONDARY,
            fg=Colors.TEXT_PRIMARY
        )
        title_label.pack(pady=(20, 15), padx=20)
        
        step1 = Label(
            help_frame,
            text="Откройте плейлист в Яндекс Музыке",
            font=('Segoe UI', 10),
            bg=Colors.BG_SECONDARY,
            fg=Colors.TEXT_SECONDARY,
            wraplength=460,
            justify='left'
        )
        step1.pack(anchor='w', padx=20, pady=(10, 5))
        
        try:
            screen1_path = resource_path("screen1.png")
            if os.path.exists(screen1_path):
                screen1_img = Image.open(screen1_path)
                screen1_img = screen1_img.resize((500, int(screen1_img.height * (500 / screen1_img.width))), Image.Resampling.LANCZOS)
                self.screen1_photo = ImageTk.PhotoImage(screen1_img)
                screen1_label = Label(help_frame, image=self.screen1_photo, bg=Colors.BG_TERTIARY)
                screen1_label.image = self.screen1_photo
                screen1_label.pack(pady=10, padx=20)
        except Exception as e:
            print(f"[WARN] Не удалось загрузить screen1.png: {e}")
            placeholder1 = Label(help_frame, text="[Изображение 1]", font=('Segoe UI', 10), bg=Colors.BG_TERTIARY, fg=Colors.TEXT_MUTED, width=60, height=10)
            placeholder1.pack(pady=10, padx=20)
        
        step2 = Label(
            help_frame,
            text="Нажмите кнопку «Поделиться» и выберите «HTML код»",
            font=('Segoe UI', 10),
            bg=Colors.BG_SECONDARY,
            fg=Colors.TEXT_SECONDARY,
            wraplength=460,
            justify='left'
        )
        step2.pack(anchor='w', padx=20, pady=(10, 5))
        
        try:
            screen2_path = resource_path("screen2.png")
            if os.path.exists(screen2_path):
                screen2_img = Image.open(screen2_path)
                screen2_img = screen2_img.resize((500, int(screen2_img.height * (500 / screen2_img.width))), Image.Resampling.LANCZOS)
                self.screen2_photo = ImageTk.PhotoImage(screen2_img)
                screen2_label = Label(help_frame, image=self.screen2_photo, bg=Colors.BG_TERTIARY)
                screen2_label.image = self.screen2_photo
                screen2_label.pack(pady=10, padx=20)
        except Exception as e:
            print(f"[WARN] Не удалось загрузить screen2.png: {e}")
            placeholder2 = Label(help_frame, text="[Изображение 2]", font=('Segoe UI', 10), bg=Colors.BG_TERTIARY, fg=Colors.TEXT_MUTED, width=60, height=10)
            placeholder2.pack(pady=10, padx=20)
        
        step3 = Label(
            help_frame,
            text="Скопируйте полученный HTML код и вставьте его в поле ввода",
            font=('Segoe UI', 10),
            bg=Colors.BG_SECONDARY,
            fg=Colors.TEXT_SECONDARY,
            wraplength=460,
            justify='left'
        )
        step3.pack(anchor='w', padx=20, pady=(10, 20))
        
        help_frame.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox('all'))
        
        close_btn = ModernButton(help_frame, text="Закрыть", command=on_close, bg=Colors.BG_TERTIARY)
        close_btn.pack(pady=(0, 20))

    def export_yandex_playlist(self, iframe_html):
        #Парсим iframe, достаем owner, kind, UUID
        src_match = re.search(r'src=["\'](?:https?://music\.yandex\.ru)?/iframe/playlist/([^/]+)/(\d+)["\']', iframe_html, re.IGNORECASE)
        
        uuid_match = re.search(r'playlists/(?:lk\.)?([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', iframe_html, re.IGNORECASE)
        
        if not uuid_match:
            raise Exception("UUID плейлиста не найден в iframe")
            
        clean_uuid = uuid_match.group(1)
        owner = src_match.group(1) if src_match else None
        kind = src_match.group(2) if src_match else None
        
        self.log(f"[DEBUG] UUID: {clean_uuid}, Owner: {owner}, Kind: {kind}")
        
        is_personal = kind in ['3', '1001', '1002', '1003', '1004']
        
        if is_personal and owner:
            api_url = f"https://api.music.yandex.net/users/{owner}/playlists/{kind}"
            self.log(f"[INFO] Запрос к API (личный плейлист): {api_url}")
        else:
            api_url = f"https://api.music.yandex.net/playlist/{clean_uuid}"
            self.log(f"[INFO] Запрос к API (публичный плейлист): {api_url}")
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                'Origin': 'https://music.yandex.ru',
                'Referer': 'https://music.yandex.ru/'
            }
            resp = requests.get(api_url, headers=headers, timeout=25)
            
            if resp.status_code in [401, 403, 404] and is_personal:
                raise Exception(f"Плейлист '{kind}' является приватным. API Яндекса требует авторизации для доступа к 'Мне нравится'. Используйте обычный плейлист или экспортируйте треки вручную.")
            
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.HTTPError as e:
            raise Exception(f"Ошибка API ({resp.status_code}): {e}")
        except Exception as e:
            raise Exception(f"Ошибка сети/API: {e}")
        
        try:
            result = data.get('result', {})
            playlist_name = result.get('title', f"Playlist {clean_uuid[:8]}")
            raw_tracks = result.get('tracks', [])
            
            if not raw_tracks:
                volumes = result.get('volumes', [])
                if volumes and isinstance(volumes, list):
                    raw_tracks = [t for vol in volumes if isinstance(vol, list) for t in vol]
            
            self.log(f"[OK] Плейлист: '{playlist_name}', треков: {len(raw_tracks)}")
            
            if not raw_tracks:
                raise Exception("API вернул пустой список треков")
                
        except Exception as e:
            raise Exception(f"Ошибка парсинга JSON: {e}")
        
        playlist_content = ""
        parsed_count = 0
        
        for item in raw_tracks:
            try:
                track = item.get('track', item) if isinstance(item, dict) else item
                if not isinstance(track, dict):
                    continue
                
                title = track.get('title', 'Unknown Track')
                if track.get('version'):
                    title = f"{title} ({track['version']})"
                
                artists = track.get('artists', [])
                artists_names = ", ".join(a['name'] for a in artists if isinstance(a, dict) and 'name' in a)
                
                playlist_content += f"{artists_names or 'Unknown Artist'} - {title}\n"
                parsed_count += 1
            except Exception:
                continue
        
        if parsed_count == 0:
            raise Exception("Не удалось распарсить ни одного трека")
        
        self.log(f"[OK] Распарсено: {parsed_count} треков")
        
        self.temp_dir = os.path.join(self.app_dir, "temp")
        os.makedirs(self.temp_dir, exist_ok=True)
        
        safe_title = re.sub(r'[^\w\s-]', '', playlist_name).strip() or f"pl_{clean_uuid[:8]}"
        self.temp_playlist_file = os.path.join(self.temp_dir, f"{safe_title}.txt")
        
        with open(self.temp_playlist_file, 'w', encoding='utf-8') as f:
            f.write(playlist_content)
            
        self.log(f"[OK] Файл создан: {os.path.basename(self.temp_playlist_file)}")
        return self.temp_playlist_file

    def cleanup_temp(self):
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                self.temp_dir = None
                self.temp_playlist_file = None
            except Exception as e:
                print(f"[WARN] Не удалось удалить временную папку: {e}")

    def browse_input(self):
        filepath = filedialog.askopenfilename(
            title="Выберите файл со списком треков",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filepath:
            self.input_entry.delete(0, END)
            self.input_entry.insert(0, filepath)
            self.config.set('last_input_file', filepath)

    def browse_output(self):
        directory = filedialog.askdirectory(title="Выберите папку для загрузок")
        if directory:
            self.output_entry.delete(0, END)
            self.output_entry.insert(0, directory)
            self.config.set('last_output_dir', directory)

    def log(self, message):
        def _log():
            self.log_text.insert(END, message + "\n")
            self.log_text.see(END)
        self.root.after(0, _log)

    def update_stats(self, stats):
        def _update():
            for key, value in stats.items():
                if key in self.stats_vars:
                    self.stats_vars[key].config(text=str(value))
        self.root.after(0, _update)

    def update_progress(self, current, total, track, search_result=None):
        def _update():
            self.progress['value'] = (current / total) * 100
            status_icons = {
                'downloaded': '[OK]',
                'skipped': '[SKIP]',
                'not_found': '[NF]',
                'low_match': '[LOW]',
                'download_error': '[ERR]',
                'region_blocked': '[RGBLOCK]'
            }
            icon = status_icons.get(track['status'], '[?]')
            self.status_label.config(text=f"[{current}/{total}] {icon} {track['artist']} - {track['track']}")
            
            log_msg = f"[{current}/{total}] {icon} {track['artist']} - {track['track']} [{track['status']}] ({track['match_score']}%)"
            if track['status'] == 'skipped':
                log_msg += " - Уже скачан"
            elif track['status'] == 'not_found':
                if search_result and search_result.get('count', 0) > 0:
                    log_msg += f" - Найдено {search_result['count']} треков"
                else:
                    log_msg += " - Поиск не вернул результатов"
            elif track['status'] == 'download_error':
                log_msg += f" - {track.get('error_message', '')[:80]}"
            elif track['status'] == 'low_match':
                log_msg += " - Скачан в low_match/"
            
            self.log(log_msg)
            self.update_stats(self.manager.stats)
            
            if current >= total:
                self.on_complete()
        
        self.root.after(0, _update)

    def start_download(self):
        current_value = self.input_entry.get().strip()
        if self.input_mode.get() == 0:
            self.ym_input_value = current_value
            self.config.set('last_iframe_input', current_value)
        else:
            self.txt_input_value = current_value
        output_dir = self.output_entry.get().strip()
        if not output_dir:
            self.show_error("Выберите папку для загрузок")
            return
        
        try:
            if self.input_mode.get() == 0:
                iframe_html = self.input_entry.get().strip()
                if not iframe_html:
                    self.show_error("Вставьте iframe плейлиста Яндекс Музыки")
                    return
                
                self.log("=" * 70)
                self.log("[INFO] Экспорт плейлиста Яндекс Музыки...")
                
                try:
                    playlist_file = self.export_yandex_playlist(iframe_html)
                    self.log(f"[OK] Плейлист экспортирован: {os.path.basename(playlist_file)}")
                except Exception as e:
                    self.show_error(f"Ошибка экспорта плейлиста: {str(e)}")
                    self.cleanup_temp()
                    return
                
                input_file = playlist_file
            else:
                input_file = self.input_entry.get().strip()
                if not input_file or not os.path.exists(input_file):
                    self.show_error("Выберите существующий файл со списком треков")
                    return
            
            self.config.set('match_threshold', int(self.threshold_var.get()))
            self.config.set('delay_between_tracks', int(self.delay_var.get()))
            self.config.set('search_timeout', int(self.timeout_var.get()))
            self.config.set('debug_mode', self.debug_var.get())
            self.config.set('use_artist_folders', self.artist_folders_var.get())
            
            count = self.manager.load_tracks(input_file)
            self.manager.set_output_dir(output_dir)
            
            skipped_count = self.manager.logger.get_downloaded_count() if self.manager.logger else 0
            if skipped_count > 0:
                self.log(f"[INFO] Найдено {skipped_count} уже скачанных треков - будут пропущены")
            
            self.log("=" * 70)
            self.log(f"[INFO] Треков в списке: {count}")
            self.log(f"[INFO] Пропущено (уже скачано): {skipped_count}")
            self.log(f"[INFO] Папка: {self.manager.output_dir}")
            self.log(f"[INFO] Порог: {self.config.get('match_threshold')}% | Таймаут: {self.config.get('search_timeout')}с")
            self.log(f"[INFO] Папки артистов: {'ВКЛ' if self.config.get('use_artist_folders') else 'ВЫКЛ'}")
            self.log("=" * 70)
            
            self.start_button.config(state='disabled')
            self.stop_button.config(state='normal')
            self.progress['maximum'] = 100
            self.progress['value'] = 0
            
            self.download_thread = threading.Thread(
                target=self._download_with_cleanup,
                args=(self.update_progress,),
                daemon=True
            )
            self.download_thread.start()
            
        except Exception as e:
            self.show_error(f"Ошибка: {str(e)}")
            self.cleanup_temp()

    def _download_with_cleanup(self, callback):
        try:
            self.manager.process_all(callback)
        finally:
            if self.input_mode.get() == 0:
                self.root.after(0, self._schedule_cleanup)

    def _schedule_cleanup(self):
        self.log("[INFO] Очистка временных файлов...")
        self.cleanup_temp()
        self.log("[OK] Временные файлы удалены")

    def on_complete(self):
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.status_label.config(text="Загрузка завершена")
        self.log("=" * 70)
        self.log("[OK] Загрузка завершена!")
        self.log(f"[OK] Скачано: {self.manager.stats['downloaded']}")
        self.log(f"[SKIP] Пропущено: {self.manager.stats['skipped']}")
        self.log(f"[NF] Не найдено: {self.manager.stats['not_found']}")
        self.log(f"[LOW] Low match: {self.manager.stats['low_match']}")
        self.log(f"[ERR] Ошибки: {self.manager.stats['download_error']}")
        
        lost_count = self.manager.stats['not_found'] + self.manager.stats['low_match'] + self.manager.stats['download_error']
        if lost_count > 0:
            self.log(f"\n[WARN] Проблемных треков: {lost_count}")
        
        self.log(f"[INFO] Лог: {self.manager.logger.log_file if self.manager.logger else 'N/A'}")
        
        self.show_info(
            "Загрузка завершена",
            f"Скачано: {self.manager.stats['downloaded']}\n"
            f"Пропущено: {self.manager.stats['skipped']}\n"
            f"Не найдено: {self.manager.stats['not_found']}\n"
            f"Low match: {self.manager.stats['low_match']}\n"
            f"Ошибки: {self.manager.stats['download_error']}"
        )

    def stop_download(self):
        self.manager.stop()
        self.log("[STOP] Остановка...")
        self.status_label.config(text="Остановка загрузки")
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')

    def open_output_folder(self):
        if self.manager.output_dir and os.path.exists(self.manager.output_dir):
            os.startfile(self.manager.output_dir)
        else:
            output_dir = self.output_entry.get().strip()
            if output_dir and os.path.exists(output_dir):
                os.startfile(output_dir)
            else:
                self.show_info("Инфо", "Папка загрузки ещё не создана")

    def show_cheat_input(self):
        cheat_window = Toplevel(self.root)
        cheat_window.title("???")
        cheat_window.geometry("300x150")
        cheat_window.resizable(False, False)
        cheat_window.configure(bg=Colors.BG_SECONDARY)
        cheat_window.attributes('-topmost', True)
        
        icon_path = resource_path("ico.ico")
        if os.path.exists(icon_path):
            cheat_window.iconbitmap(icon_path)
        
        cheat_window.update_idletasks()
        x = (cheat_window.winfo_screenwidth() - 300) // 2
        y = (cheat_window.winfo_screenheight() - 150) // 2
        cheat_window.geometry(f"300x150+{x}+{y}")
        
        Label(cheat_window, text="Введите чит-код:", font=('Segoe UI', 12), bg=Colors.BG_SECONDARY, fg=Colors.TEXT_PRIMARY).pack(pady=(20, 10))
        
        cheat_entry = ModernEntry(cheat_window, width=30)
        cheat_entry.pack(pady=10)
        cheat_entry.focus()
        
        def check_code():
            code = cheat_entry.get().strip()
            if code.lower() == "wwssadadba":
                cheat_window.destroy()
                self.show_easter_egg()
            else:
                cheat_window.destroy()
        
        def on_enter(event):
            check_code()
        
        cheat_entry.bind('<Return>', on_enter)
        
        submit_btn = ModernButton(cheat_window, text="OK", command=check_code, bg=Colors.ACCENT_PRIMARY)
        submit_btn.pack(pady=10)
        
        cheat_window.focus_set()
        cheat_window.grab_set()

    def show_easter_egg(self):
        egg_window = Toplevel(self.root)
        egg_window.title("???")
        egg_window.geometry("350x150")
        egg_window.resizable(False, False)
        egg_window.configure(bg="#000000")
        egg_window.attributes('-topmost', True)
        
        icon_path = resource_path("ico.ico")
        if os.path.exists(icon_path):
            egg_window.iconbitmap(icon_path)
        
        egg_window.update_idletasks()
        x = (egg_window.winfo_screenwidth() - 350) // 2
        y = (egg_window.winfo_screenheight() - 150) // 2
        egg_window.geometry(f"350x150+{x}+{y}")
        
        container = Frame(egg_window, bg="#000000")
        container.pack(expand=True, fill='both', padx=20, pady=20)
        
        Label(container, text="кусок", font=('Segoe UI', 18, 'bold'), bg="#000000", fg="#fdd400").pack(side='left', padx=(0, 15))
        
        try:
            egg_path = resource_path("egg.png")
            if os.path.exists(egg_path):
                egg_img = Image.open(egg_path)
                egg_img = egg_img.resize((75, 75), Image.Resampling.LANCZOS)
                self.egg_photo = ImageTk.PhotoImage(egg_img)
                egg_label = Label(container, image=self.egg_photo, bg="#000000")
                egg_label.image = self.egg_photo
                egg_label.pack(side='left', padx=15)
        except Exception as e:
            print(f"[ERROR] Не удалось загрузить egg.png: {e}")
            Label(container, text="[???]", font=('Segoe UI', 40), bg="#000000", fg="#fdd400").pack(side='left', padx=15)
        
        Label(container, text="говна", font=('Segoe UI', 18, 'bold'), bg="#000000", fg="#fdd400").pack(side='left', padx=(15, 0))
        
        def close_egg(event=None):
            egg_window.destroy()
        
        egg_window.bind('<Button-1>', close_egg)
        egg_window.bind('<Return>', close_egg)
        egg_window.bind('<Escape>', close_egg)

    def show_error(self, message):
        messagebox.showerror("Ошибка", message)

    def show_info(self, title, message):
        messagebox.showinfo(title, message)

if __name__ == "__main__":
    root = Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    app = App(root)
    root.mainloop()