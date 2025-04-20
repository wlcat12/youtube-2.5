import os
import json
import yt_dlp
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import shutil
import random
import string

# ВНИМАНИЕ
# эта хуета это ai generated slop сделанный потому что почему нет
# код сам по себе ужасен, если решите чёто делать с ним, то лучше подумайте дважды
# НО ОН РАБОТАЕТ, и это главное

# Конфигурация
APP_DIR = "app"
VIDEOS_DIR = os.path.join(APP_DIR, "videos")
THUMBS_DIR = os.path.join(APP_DIR, "thumbs")
DATA_FILE = os.path.join(APP_DIR, "data.js")

def ensure_dirs():
    """Создаёт папки приложения"""
    os.makedirs(VIDEOS_DIR, exist_ok=True)
    os.makedirs(THUMBS_DIR, exist_ok=True)

def process_thumbnail(video_id):
    """Качает и конвертирует превью с YouTube"""
    jpg_path = os.path.join(THUMBS_DIR, f"{video_id}.jpg")
    
    # 1. Пробуем скачать через yt-dlp
    ydl_opts = {
        'writethumbnail': True,
        'skip_download': True,
        'outtmpl': os.path.join(THUMBS_DIR, f"{video_id}.%(ext)s"),
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"https://youtu.be/{video_id}"])
    except Exception as e:
        print(f"Ошибка загрузки превью: {e}")

    # 2. Ищем скачанный файл (проверяем все форматы)
    for ext in ['webp', 'jpg', 'png']:
        src_path = os.path.join(THUMBS_DIR, f"{video_id}.{ext}")
        if os.path.exists(src_path):
            try:
                # Конвертируем в JPG с максимальным качеством
                with Image.open(src_path) as img:
                    rgb_img = img.convert("RGB")
                    rgb_img.save(jpg_path, "JPEG", quality=95, subsampling=0)
                
                # Удаляем исходник если это не JPG
                if ext != 'jpg':
                    os.remove(src_path)
                return True
            except Exception as e:
                print(f"Ошибка конвертации {ext}: {e}")
                continue
    
    # 3. Если ничего не получилось - генерируем превью
    print("Создаем превью-заглушку")
    generate_thumbnail(video_id, "Превью")
    return False

def generate_id():
    """Генерирует ID для локальных видео"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(11))

def load_videos():
    """Загружает список видео из data.js"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.loads(f.read().replace('var videos = ', '').rstrip(';'))
    return []

def save_videos(videos):
    """Сохраняет видео в data.js"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        f.write(f"var videos = {json.dumps(videos, ensure_ascii=False, indent=2)};")

def download_youtube_video(url):
    """Качает видео и обрабатывает превью"""
    ydl_opts = {
        'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]',
        'outtmpl': os.path.join(VIDEOS_DIR, '%(id)s.%(ext)s'),
        'writethumbnail': False,  # Отключаем авто-загрузку, будем качать отдельно
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        video_id = info['id']
        
        # Отдельно качаем превью
        if not process_thumbnail(video_id):
            print("Не удалось получить оригинальное превью")
        
        return info
    
def download_youtube_playlist(url):
    """Качает все видео из плейлиста"""
    ydl_opts = {
        'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]',
        'outtmpl': os.path.join(VIDEOS_DIR, '%(id)s.%(ext)s'),
        'writethumbnail': False,
        'concurrent-fragments': 8,
        'n_threads': 4,
        'extract_flat': False,  # Для обработки плейлистов
        'ignoreerrors': True   # Пропускать ошибки в плейлисте
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        
        videos = load_videos()
        
        # Если это плейлист - обрабатываем все записи
        if 'entries' in info:
            for entry in info['entries']:
                if entry:  # Пропускаем None (если были ошибки)
                    video_id = entry['id']
                    if not process_thumbnail(video_id):
                        print(f"Не удалось получить превью для {video_id}")
                    
                    videos.append({
                        "id": video_id,
                        "title": entry.get('title', 'Без названия'),
                        "author": entry.get('uploader', 'Неизвестно'),
                        "description": entry.get('description', ''),
                        "filename": f"{video_id}.mp4",
                        "date": datetime.now().strftime("%d.%m.%Y"),
                        "views": f"{entry.get('view_count', 0)} просмотров"
                    })
        
        save_videos(videos)
        return info


def convert_thumb(video_id, source_path=None):
    """Обрабатывает превью"""
    jpg_path = os.path.join(THUMBS_DIR, f"{video_id}.jpg")
    
    if source_path:  # Для локальных видео
        if source_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            shutil.copy2(source_path, jpg_path)
        else:
            generate_thumbnail(video_id, "Превью")
    else:  # Для YouTube
        webp_path = os.path.join(THUMBS_DIR, f"{video_id}.webp")
        if os.path.exists(webp_path):
            img = Image.open(webp_path).convert("RGB")
            img.save(jpg_path, "JPEG", quality=85)
            os.remove(webp_path)

def generate_thumbnail(video_id, text):
    """Генерирует превью для локальных видео"""
    img = Image.new('RGB', (1280, 720), color=(30, 30, 30))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 60)
    except:
        font = ImageFont.load_default()
    draw.text((100, 300), text, fill=(255, 255, 255), font=font)
    img.save(os.path.join(THUMBS_DIR, f"{video_id}.jpg"))

def add_youtube_video():
    """Добавляет видео с YouTube"""
    update_html()
    url = input("Введите URL YouTube видео: ").strip()
    if not url.startswith(('http://', 'https://')):
        print("Неверный URL")
        return

    try:
        ensure_dirs()
        info = download_youtube_video(url)
        
        videos = load_videos()
        videos.append({
            "id": info['id'],
            "title": info.get('title', 'Без названия'),
            "author": info.get('uploader', 'Неизвестно'),
            "description": info.get('description', ''),
            "filename": f"{info['id']}.mp4",
            "date": datetime.now().strftime("%d.%m.%Y"),
            "views": f"{info.get('view_count', 0)} просмотров"
        })
        
        save_videos(videos)
        print(f"Видео '{info['title']}' добавлено!")
        print(f"Превью: app/thumbs/{info['id']}.jpg")

    except Exception as e:
        print(f"Ошибка: {str(e)}")

def add_youtube_playlist():
    """Добавляет все видео из плейлиста YouTube"""
    update_html()
    url = input("Введите URL плейлиста YouTube: ").strip()
    if not url.startswith(('http://', 'https://')):
        print("Неверный URL")
        return

    try:
        ensure_dirs()
        info = download_youtube_playlist(url)
        print(f"Добавлено {len(info.get('entries', []))} видео из плейлиста!")
    except Exception as e:
        print(f"Ошибка: {str(e)}")

def add_local_video():
    """Добавляет локальное видео"""
    update_html()
    src_path = input("Введите путь к видеофайлу: ").strip()
    if not src_path or not os.path.exists(src_path):
        print("Файл не найден!")
        return

    try:
        ensure_dirs()
        video_id = generate_id()
        ext = Path(src_path).suffix.lower()
        filename = f"{video_id}{ext}"
        
        shutil.copy2(src_path, os.path.join(VIDEOS_DIR, filename))

        thumb_path = input("Путь к обложке (Enter для автогенерации): ").strip()
        convert_thumb(video_id, thumb_path if thumb_path else None)

        videos = load_videos()
        videos.append({
            "id": video_id,
            "title": input("Название: ").strip() or "Без названия",
            "author": input("Автор: ").strip() or "Аноним",
            "description": input("Описание: ").strip() or "",
            "filename": filename,
            "date": datetime.now().strftime("%d.%m.%Y"),
            "views": f"{random.randint(1, 1000)} просмотров"
        })
        
        save_videos(videos)
        print(f"Видео добавлено! ID: {video_id}")

    except Exception as e:
        print(f"Ошибка: {str(e)}")

def remove_video():
    """Удаляет видео"""
    update_html()
    videos = load_videos()
    if not videos:
        print("Плейлист пуст!")
        return

    print("\nСписок видео:")
    for i, video in enumerate(videos, 1):
        print(f"{i}. {video['title']} (ID: {video['id']})")

    try:
        choice = int(input("Номер для удаления: ")) - 1
        if 0 <= choice < len(videos):
            video = videos.pop(choice)
            os.remove(os.path.join(VIDEOS_DIR, video['filename']))
            os.remove(os.path.join(THUMBS_DIR, f"{video['id']}.jpg"))
            save_videos(videos)
            print(f"Удалено: {video['title']}")
        else:
            print("Неверный номер!")
    except ValueError:
        print("Введите число!")

def update_html():
    # остатки легаси цивилизаций
    # практически не нужен
    Path(f'{APP_DIR}').mkdir(parents=True, exist_ok=True)

    shutil.copy('templates/index.html', f'{APP_DIR}')
    shutil.copy('templates/video.html', f'{APP_DIR}')
    print("HTML-страницы обновляются автоматически")

if __name__ == "__main__":
    ensure_dirs()
    while True:
        print("\n=== Youtube 2.5 Uzbekistan edition ===")
        print("1. Добавить видео с YouTube")
        print("2. Добавить плейлист с YouTube")
        print("3. Добавить локальное видео")
        print("4. Удалить видео")
        print("5. Выход")
        
        choice = input("Выберите действие: ").strip()
        
        if choice == "1":
            add_youtube_video()
        elif choice == "2":
            add_youtube_playlist()
        elif choice == "3":
            add_local_video()
        elif choice == "4":
            remove_video()
        elif choice == "5":
            break
        else:
            print("Неверный ввод!")