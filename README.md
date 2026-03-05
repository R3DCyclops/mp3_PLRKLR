# mp3_PLRKLR

**Для автоматического импорта нужной версии ffpeg в проект запустите ffmpeg_importer.py**

> Desktop-приложение для поиска и скачивания музыки из различных источников

![License](https://img.shields.io/badge/license-GPLv3-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)

**mp3_PLRKLR** — это свободное приложение с графическим интерфейсом для массового скачивания музыкальных треков. На основе Ваших плейлистов из Яндекс Музыки.
** Помогает убрать цензуру в треках Ваших плейлистов.

### Особенности

- **Мультиисточники**: поиск через Hitmotop, SoundCloud, YouTube Music
- **Умное сопоставление**: нечёткий поиск с настраиваемым порогом совпадения (rapidfuzz)
- **Организация**: опциональное создание папок по артистам, сортировка по статусам
- **Стратегии поиска**: 6 предустановленных стратегий с возможностью расширения
- **Yandex Music**: импорт плейлистов через iframe-код
- **Статистика в реальном времени**: отслеживание прогресса, логирование результатов
- **Современный UI**: тёмная тема, адаптивный интерфейс на Tkinter
- **Portables**: сборка в один .exe-файл через PyInstaller

## Быстрый старт

### Требования

- Python 3.10 или выше
- Windows 10/11
- Доступ к интернету

### Установка зависимостей

pip install -r requirements.txt

### Запуск из исходного кода

python main.py

### Сборка в exe

compile.bat

Готовый файл появится в папке `dist/mp3_PLRKLR.exe`

## Настройка

Основные параметры настраиваются через `config.json` или графический интерфейс:

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `match_threshold` | Минимальный процент совпадения для скачивания | 85 |
| `delay_between_tracks` | Задержка между запросами (сек) | 2 |
| `search_timeout` | Таймаут поиска (сек) | 20 |
| `download_timeout` | Таймаут скачивания (сек) | 180 |
| `use_artist_folders` | Создавать папки по имени артиста | false |
| `debug_mode` | Режим отладки с подробным логом | false |

## Стратегии поиска

Стратегии определяют порядок и комбинацию источников


> Примечание: Для работы SoundCloud и YouTube Music может потребоваться VPN или Zapret.

## Структура проекта

mp3_PLRKLR/
├── main.py              # Точка входа, основной класс App
├── config.json          # Конфигурация
├── compile.bat          # Скрипт сборки PyInstaller
├── requirements.txt     # Зависимости Python
├── strat/               # Стратегии поиска
│   ├── strat*.txt       # Файлы стратегий
│   └── methods/         # Модули источников
│       ├── hitmo.py     # Hitmotop API
│       ├── soundcloud.py# SoundCloud через yt-dlp
│       └── ytm.py       # YouTube Music через yt-dlp
├── ffmpeg/              # Встроенный FFmpeg (опционально)
├── dist/                # Выходная папка после сборки
└── *.png, *.ico         # Ресурсы интерфейса

## Лицензия

Проект распространяется под лицензией **GNU General Public License v3.0**.

Copyright (C) 2026 m0reslav

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

### Сторонние компоненты

| Компонент | Лицензия | Источник |
|-----------|----------|----------|
| **FFmpeg** | GPL | [BtbN/FFmpeg-Builds](https://github.com/BtbN/FFmpeg-Builds/releases) |
| yt-dlp | Unlicense | [yt-dlp/yt-dlp](https://github.com/yt-dlp/yt-dlp) |
| rapidfuzz | MIT | [rapidfuzz/rapidfuzz](https://github.com/rapidfuzz/rapidfuzz) |
| Pillow | HPND | [python-pillow/Pillow](https://github.com/python-pillow/Pillow) |
| requests | Apache 2.0 | [psf/requests](https://github.com/psf/requests) |

> Важно: При использовании встроенной сборки FFmpeg помните, что она распространяется под лицензией GPL. Если вы модифицируете или распространяете этот проект, убедитесь в соблюдении условий совместимости лицензий.

### Отладка

Включите `debug_mode` в настройках или запустите с флагом:

python main.py --debug

## FAQ

**В: Почему некоторые треки попадают в папку `low_match`?**  
О: Треки с совпадением ниже `match_threshold`, но выше минимального порога (40%), скачиваются в отдельную папку для ручной проверки.

**В: Как импортировать плейлист Яндекс Музыки?**  
О: Откройте плейлист → «Поделиться» → «HTML-код» → скопируйте iframe и вставьте в поле ввода программы.

**В: Программа не находит ffmpeg**  
О: Убедитесь, что папка `ffmpeg/` находится рядом с `main.py`, или укажите путь к ffmpeg в `config.json`.

## Контакты

- Автор: **m0reslav**
- Сайт: [moreslav.ru](https://moreslav.ru)

---

> Примечание: Используйте программу только для загрузки контента, распространение которого разрешено правообладателями или соответствует законодательству вашей страны.
