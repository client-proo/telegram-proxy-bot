
# ============================================
# نصب پیش‌نیازها
# ============================================
!pip install pyrogram requests nest_asyncio tgcrypto aiohttp aiofiles yt-dlp spotdl -q
!apt-get install ffmpeg -qq > /dev/null 2>&1

import os
import re
import subprocess
import time
import asyncio
from urllib.parse import unquote, urlparse
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode
import nest_asyncio
import aiohttp
import aiofiles
import yt_dlp
import json

nest_asyncio.apply()

# ============================================
# تنظیمات ربات
# ============================================
API_ID = 29534256
API_HASH = "8a2b0ee3e07f6903bff02dd53cb93ff8"
BOT_TOKEN = "8024769265:AAHVZelW7PojoJybjRV3a1i8QoWzm7rmemQ"
LOG_CHANNEL = "@storage110"
CHUNK_SIZE = 1024 * 1024

app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ============================================
# مدیریت وضعیت کاربران و رویدادهای لغو
# ============================================
user_states = {}
cancel_events = {}

# ============================================
# توابع کمکی (فرمت‌سازی)
# ============================================
VIDEO_EXT = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
AUDIO_EXT = {'.mp3', '.m4a', '.flac', '.wav', '.aac', '.ogg'}

def is_video_file(filename: str) -> bool:
    return os.path.splitext(filename)[1].lower() in VIDEO_EXT

def is_audio_file(filename: str) -> bool:
    return os.path.splitext(filename)[1].lower() in AUDIO_EXT

def format_size(size_bytes: int) -> str:
    if not size_bytes or size_bytes <= 0:
        return "نامشخص"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"

def format_speed(bytes_per_sec: float) -> str:
    if bytes_per_sec <= 0:
        return "⏳ محاسبه..."
    if bytes_per_sec < 1024:
        return f"{bytes_per_sec:.0f} B/s"
    elif bytes_per_sec < 1024**2:
        return f"{bytes_per_sec/1024:.1f} KB/s"
    elif bytes_per_sec < 1024**3:
        return f"{bytes_per_sec/1024**2:.1f} MB/s"
    else:
        return f"{bytes_per_sec/1024**3:.1f} GB/s"

def format_time(seconds: int) -> str:
    if not seconds or seconds <= 0:
        return "نامشخص"
    if seconds < 60:
        return f"{seconds:.0f} sec"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes} min {secs} sec"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours} h {minutes} min"

def make_progress_text(title: str, filename: str, percent: float, downloaded: int, total: int, speed: float, elapsed: float) -> str:
    filled = int(percent // 5)
    progress_bar = "▣" * filled + "▢" * (20 - filled)

    if speed > 0 and total > downloaded:
        remaining_bytes = total - downloaded
        time_left = remaining_bytes / speed
        time_left_str = format_time(time_left)
    else:
        time_left_str = "⏳ محاسبه..."

    speed_str = format_speed(speed)

    text = (
        f"**{title}**\n"
        f"نام: `{filename}`\n\n"
        f"**پیشرفت:** `{percent:.2f}%`\n"
        f"[{progress_bar}]\n\n"
        f"➩ 🚀 **سرعت:** `{speed_str}`\n"
        f"➩ ✅ **دریافت:** `{format_size(downloaded)}`\n"
        f"➩ 📁 **حجم کل:** `{format_size(total)}`\n"
        f"➩ 🕒 **زمان باقی‌مانده:** `{time_left_str}`"
    )
    return text

# ============================================
# تشخیص نوع لینک
# ============================================
def detect_link_type(url: str) -> str:
    patterns = {
        'youtube': [r'(?:youtube\.com|youtu\.be)'],
        'spotify': [r'spotify\.com'],
        'instagram': [r'instagram\.com', r'instagr\.am'],
        'soundcloud': [r'soundcloud\.com'],
        'twitter': [r'twitter\.com', r'x\.com'],
        'tiktok': [r'tiktok\.com'],
        'vimeo': [r'vimeo\.com'],
        'facebook': [r'facebook\.com', r'fb\.watch']
    }
    for platform, patterns_list in patterns.items():
        for pattern in patterns_list:
            if re.search(pattern, url, re.I):
                return platform
    return 'direct'

# ============================================
# استخراج فرمت‌های ویدیویی با yt-dlp (یوتیوب و غیره)
# ============================================
async def extract_video_formats(url: str):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'force_generic_extractor': False,
        'format_sort': ['res:1080', 'res:720', 'res:480', 'res:360'],
        'merge_output_format': 'mp4',
        'ignoreerrors': True,
    }
    
    def extract_info_sync():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                return info
            except Exception as e:
                return {'error': str(e)}
    
    loop = asyncio.get_event_loop()
    info = await loop.run_in_executor(None, extract_info_sync)
    
    if 'error' in info:
        if 'cookies' in info['error'].lower() or 'login' in info['error'].lower():
            raise Exception("این سایت نیاز به احراز هویت دارد. لطفاً از لینک مستقیم یا ویدیوهای عمومی استفاده کنید.")
        if 'DRM' in info['error']:
            raise Exception("این ویدیو با DRM محافظت می‌شود و قابل دانلود نیست.")
        raise Exception(f"خطا در استخراج اطلاعات: {info['error']}")
    if not info:
        raise Exception("اطلاعاتی از لینک استخراج نشد")
    
    formats = []
    seen_heights = set()
    for f in info.get('formats', []):
        if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
            height = f.get('height')
            if height is None:
                continue
            if height in seen_heights:
                continue
            seen_heights.add(height)
            formats.append({
                'format_id': f['format_id'],
                'height': height,
                'width': f.get('width'),
                'ext': f.get('ext', 'mp4'),
            })
    
    formats.sort(key=lambda x: x['height'], reverse=True)
    if not formats:
        raise Exception("لینک ویدیویی معتبر نیست یا فرمت ویدیویی پشتیبانی نمی‌شود")
    
    title = info.get('title', 'video')
    if not title:
        title = "unknown"
    
    return formats, title

# ============================================
# دانلود از اسپاتیفای با spotdl (به‌روز شده)
# ============================================
async def download_spotify(url: str, filename: str, progress_callback, cancel_event: asyncio.Event):
    """دانلود آهنگ از اسپاتیفای با spotdl (نسخه جدید)"""
    
    def download_sync():
        try:
            import spotdl
            from spotdl import Spotdl
            
            # تنظیمات spotdl
            spotify = Spotdl(
                client_id=None,
                client_secret=None,
                # user_agent حذف شد - خطای قبلی را رفع می‌کند
            )
            
            # جستجو و دانلود
            results = spotify.search([url])
            if not results:
                raise Exception("آهنگی در اسپاتیفای پیدا نشد")
            
            # دانلود
            song = results[0]
            downloaded_file = song.download()
            
            # بررسی فایل دانلود شده
            if not downloaded_file or not os.path.exists(downloaded_file):
                raise Exception("دانلود ناموفق بود")
            
            # تغییر نام به نام مورد نظر
            os.rename(downloaded_file, filename)
            return True
            
        except ImportError:
            # اگر spotdl نصب نیست، از yt-dlp استفاده کنیم (اما ممکن است DRM بخورد)
            raise Exception("لطفاً spotdl را نصب کنید: !pip install spotdl")
        except Exception as e:
            raise Exception(f"خطا در دانلود از اسپاتیفای: {str(e)}")
    
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, download_sync)
    await progress_callback(100, 1, 1, 0)

# ============================================
# دانلود با yt-dlp (ویدیو)
# ============================================
async def download_with_ytdlp(url: str, format_id: str, filename: str, progress_callback, cancel_event: asyncio.Event):
    main_loop = asyncio.get_running_loop()
    
    def progress_hook(d):
        if cancel_event.is_set():
            raise Exception("لغو توسط کاربر")
        
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)
            speed = d.get('speed', 0)
            if total > 0:
                percent = (downloaded / total) * 100
                asyncio.run_coroutine_threadsafe(
                    progress_callback(percent, downloaded, total, speed),
                    main_loop
                )
        elif d['status'] == 'finished':
            asyncio.run_coroutine_threadsafe(
                progress_callback(100, 1, 1, 0),
                main_loop
            )
    
    ydl_opts = {
        'format': format_id,
        'outtmpl': filename,
        'quiet': True,
        'no_warnings': True,
        'progress_hooks': [progress_hook],
        'restrictfilenames': True,
        'ignoreerrors': True,
    }
    
    def download_sync():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                ydl.download([url])
                # بررسی اینکه فایل واقعاً دانلود شده است
                if not os.path.exists(filename):
                    raise Exception("فایل دانلود نشد")
            except Exception as e:
                if "لغو توسط کاربر" in str(e):
                    raise
                else:
                    raise Exception(f"خطا در دانلود: {str(e)}")
    
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, download_sync)

# ============================================
# دانلود مستقیم با aiohttp (برای فایل‌های معمولی)
# ============================================
async def download_file_with_aiohttp(url: str, filename: str, progress_callback, cancel_event: asyncio.Event):
    downloaded_size = 0
    if os.path.exists(filename):
        downloaded_size = os.path.getsize(filename)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': '*/*',
        'Accept-Encoding': 'identity',
        'Connection': 'keep-alive'
    }
    if downloaded_size > 0:
        headers['Range'] = f'bytes={downloaded_size}-'
    
    timeout = aiohttp.ClientTimeout(total=600, connect=30, sock_read=60)
    max_retries = 10
    retry_delay = 3
    
    for attempt in range(max_retries):
        if cancel_event.is_set():
            raise asyncio.CancelledError("عملیات توسط کاربر لغو شد")
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 416:
                        await progress_callback(100, downloaded_size, downloaded_size, 0)
                        return True
                    if response.status == 404:
                        raise Exception("فایل پیدا نشد (404)")
                    if response.status not in (200, 206):
                        raise Exception(f"خطا در پاسخ سرور: {response.status}")
                    
                    total_size = int(response.headers.get('content-length', 0))
                    content_range = response.headers.get('content-range', '')
                    if content_range and 'bytes' in content_range:
                        match = re.search(r'bytes \d+-\d+/(\d+)', content_range)
                        if match:
                            total_size = int(match.group(1))
                    if total_size == 0:
                        total_size = downloaded_size + int(response.headers.get('content-length', 0))
                    
                    if downloaded_size >= total_size > 0:
                        await progress_callback(100, total_size, total_size, 0)
                        return True
                    
                    mode = 'ab' if downloaded_size > 0 else 'wb'
                    current_size = downloaded_size
                    last_update_time = time.time()
                    last_downloaded = downloaded_size
                    async with aiofiles.open(filename, mode) as f:
                        async for chunk in response.content.iter_chunked(CHUNK_SIZE):
                            if cancel_event.is_set():
                                raise asyncio.CancelledError("عملیات توسط کاربر لغو شد")
                            if chunk:
                                await f.write(chunk)
                                current_size += len(chunk)
                                now = time.time()
                                elapsed = now - last_update_time
                                if elapsed >= 1:
                                    speed = (current_size - last_downloaded) / elapsed if elapsed else 0
                                    last_downloaded = current_size
                                    last_update_time = now
                                    percent = (current_size / total_size) * 100 if total_size else 0
                                    await progress_callback(percent, current_size, total_size, speed)
                    await progress_callback(100, current_size, total_size, 0)
                    return True
        except asyncio.CancelledError:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError, ConnectionError, aiohttp.ClientPayloadError, aiohttp.ClientOSError) as e:
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                downloaded_size = os.path.getsize(filename)
                headers['Range'] = f'bytes={downloaded_size}-'
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
            raise Exception(f"خطا در دانلود: {str(e)}")
        except Exception as e:
            raise Exception(f"خطا در دانلود: {str(e)}")
    raise Exception("تعداد تلاش‌های مجدد بیش از حد مجاز")

# ============================================
# توابع پردازش فایل (تامنیل، مدت زمان، ...)
# ============================================
def generate_thumbnail(video_path: str, thumb_path: str) -> bool:
    try:
        cmd = ['ffmpeg', '-i', video_path, '-ss', '00:00:01', '-vframes', '1', '-vf', 'scale=320:-1', '-q:v', '2', thumb_path, '-y']
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 0
    except:
        return False

def get_video_duration(video_path: str):
    try:
        out = subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', video_path], text=True).strip()
        return int(float(out))
    except:
        return None

# ============================================
# نمایش اطلاعات فایل (برای لینک‌های مستقیم)
# ============================================
async def show_file_info(client, message, user_id, url, original_filename):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ پیش‌فرض", callback_data="default_yes"),
         InlineKeyboardButton("✏️ ویرایش", callback_data="edit_file")]
    ])
    info_text = f"📁 **نام فایل:** `{original_filename}`\n💾 **حجم فایل:** در حال بررسی..."
    info_msg = await message.reply(info_text, reply_markup=keyboard)
    user_states[user_id] = {
        'step': 'showing_info',
        'info_msg_id': info_msg.id,
        'url': url,
        'original_filename': original_filename,
        'custom_filename': None,
        'thumbnail_path': None,
        'status_msg_id': None,
        'link_msg_id': message.id
    }
    try:
        head = requests.head(url, allow_redirects=True, timeout=10)
        total = int(head.headers.get('content-length', 0))
        if total > 0:
            await info_msg.edit_text(f"📁 **نام فایل:** `{original_filename}`\n💾 **حجم فایل:** `{format_size(total)}`", reply_markup=keyboard)
    except:
        pass

# ============================================
# نمایش کیفیت‌های ویدیویی (فقط کیفیت روی دکمه‌ها)
# ============================================
async def show_quality_options(client, message, user_id, url, formats, title):
    buttons = []
    for f in formats:
        height = f['height']
        label = f"{height}p"
        buttons.append([InlineKeyboardButton(label, callback_data=f"quality_{f['format_id']}")])
    
    keyboard = InlineKeyboardMarkup(buttons)
    info_msg = await message.reply(f"🎬 **ویدیو:** `{title}`\nلطفاً کیفیت مورد نظر را انتخاب کنید:", reply_markup=keyboard)
    
    user_states[user_id] = {
        'step': 'awaiting_quality_selection',
        'info_msg_id': info_msg.id,
        'url': url,
        'formats': formats,
        'title': title,
        'custom_filename': None,
        'thumbnail_path': None,
        'status_msg_id': None,
        'link_msg_id': message.id,
        'link_type': 'youtube'
    }

# ============================================
# هندلرهای پیام
# ============================================
@app.on_message(filters.command("start"))
async def start_command(client, message):
    await message.reply(
        "🤖 **ربات دانلود و آپلود**\n\n"
        "لینک مستقیم فایل یا لینک از سایت‌های زیر را ارسال کنید:\n"
        "✅ یوتیوب (YouTube)\n"
        "✅ اسپاتیفای (Spotify) - **فقط MP3**\n"
        "✅ اینستاگرام (Instagram)\n"
        "✅ ساندکلاود (SoundCloud)\n"
        "✅ توییتر (Twitter/X)\n"
        "✅ تیک‌تاک (TikTok)\n"
        "✅ و بسیاری دیگر\n\n"
        "📌 لینک‌های مستقیم فایل (PDF, ZIP, APK و ...) نیز پشتیبانی می‌شوند."
    )
    if message.chat.id in user_states:
        del user_states[message.chat.id]
    user_states[message.chat.id] = {'step': 'awaiting_link'}

@app.on_message(filters.text & ~filters.command("start"))
async def handle_link_or_name(client, message):
    user_id = message.chat.id
    text = message.text.strip()
    
    if user_id in user_states and user_states[user_id].get('step') == 'awaiting_new_filename':
        if text.lower() == 'skip':
            user_states[user_id]['custom_filename'] = None
        else:
            user_states[user_id]['custom_filename'] = text
        user_states[user_id]['step'] = 'awaiting_new_thumbnail_choice'
        await ask_thumbnail_choice_for_edit(client, message, user_id)
        return
    
    if user_id not in user_states or user_states[user_id].get('step') == 'awaiting_link':
        if not text.startswith(('http://', 'https://')):
            await message.reply("❌ لطفاً یک لینک معتبر ارسال کنید.")
            return
        
        user_states[user_id] = {
            'step': 'checking',
            'url': text,
            'original_filename': None,
            'custom_filename': None,
            'thumbnail_path': None,
            'info_msg_id': None,
            'status_msg_id': None,
            'link_msg_id': message.id
        }
        check_msg = await message.reply("🔍 Checking....")
        
        try:
            link_type = detect_link_type(text)
            
            # تشخیص اسپاتیفای
            if link_type == 'spotify':
                await check_msg.edit_text("🎵 **اسپاتیفای تشخیص داده شد**\n🔄 در حال آماده‌سازی برای دانلود...")
                user_states[user_id]['link_type'] = 'spotify'
                user_states[user_id]['step'] = 'processing'
                await check_msg.delete()
                await start_processing(client, message, user_id, message.from_user)
                return
            
            # بررسی لینک مستقیم با HEAD
            head = requests.head(text, allow_redirects=True, timeout=10)
            content_type = head.headers.get('content-type', '')
            content_length = int(head.headers.get('content-length', 0))
            
            is_direct = False
            if content_length > 0:
                if ('video' in content_type or
                    'application/octet-stream' in content_type or
                    'application/zip' in content_type or
                    'application/pdf' in content_type or
                    'application/x-zip-compressed' in content_type or
                    'application/vnd.android.package-archive' in content_type or
                    'audio/' in content_type or
                    'image/' in content_type):
                    is_direct = True
                elif 'text/html' not in content_type and 'application/xhtml' not in content_type:
                    is_direct = True
            
            if is_direct:
                original_filename = get_final_filename(text, head)
                user_states[user_id]['original_filename'] = original_filename
                await check_msg.delete()
                await show_file_info(client, message, user_id, text, original_filename)
            else:
                await check_msg.edit_text("🔄 در حال استخراج اطلاعات ویدیو...")
                formats, title = await extract_video_formats(text)
                if not formats:
                    await check_msg.edit_text("❌ هیچ فرمت ویدیویی مناسبی پیدا نشد.")
                    user_states[user_id]['step'] = 'awaiting_link'
                    return
                await check_msg.delete()
                await show_quality_options(client, message, user_id, text, formats, title)
                
        except Exception as e:
            error_msg = str(e)
            if "DRM" in error_msg:
                await check_msg.edit_text(
                    "❌ **این ویدیو با DRM محافظت می‌شود و قابل دانلود نیست.**\n"
                    "لطفاً از لینک مستقیم یا ویدیوهای عمومی استفاده کنید."
                )
            elif "ویدیویی معتبر نیست" in error_msg or "فرمت ویدیویی مناسبی پیدا نشد" in error_msg:
                await check_msg.edit_text(
                    "❌ لینک ارسالی یک ویدیو یا فایل مستقیم معتبر نیست.\n"
                    "لطفاً لینک مستقیم فایل (مثل PDF, ZIP, APK و ...) یا لینک ویدیو از سایت‌های پشتیبانی‌شده را ارسال کنید."
                )
            else:
                await check_msg.edit_text(f"❌ خطا در بررسی لینک: {error_msg}")
            user_states[user_id]['step'] = 'awaiting_link'
        
        return
    else:
        await message.reply("⏳ لطفاً منتظر بمانید تا مراحل قبلی کامل شود.")

def get_final_filename(url: str, response_head) -> str:
    original = extract_original_filename(url, response_head)
    if '.' not in original:
        content_type = response_head.headers.get('content-type', '') if response_head else ''
        if 'video' in content_type:
            original += '.mp4'
        elif 'image' in content_type:
            original += '.jpg'
        elif 'application/pdf' in content_type:
            original += '.pdf'
        elif 'application/zip' in content_type or 'application/x-zip' in content_type:
            original += '.zip'
        elif 'application/vnd.android.package-archive' in content_type:
            original += '.apk'
        else:
            original += '.bin'
    return original

def extract_original_filename(url: str, response_head) -> str:
    if response_head:
        cd = response_head.headers.get('content-disposition', '')
        if cd:
            match = re.search(r'filename[^;]*=\s*["\']?([^"\']+)["\']?', cd, re.I)
            if match:
                return unquote(match.group(1))
    parsed = urlparse(url)
    path = unquote(parsed.path)
    name = os.path.basename(path)
    if name and '.' in name:
        return name
    return 'file'

# ============================================
# پرسش تامنیل برای ویرایش
# ============================================
async def ask_thumbnail_choice_for_edit(client, message, user_id):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تامنیل سفارشی", callback_data="edit_thumb_yes"),
         InlineKeyboardButton("❌ خودکار", callback_data="edit_thumb_no")]
    ])
    await message.reply(
        "🖼️ آیا می‌خواهید تصویر تامنیل (بند انگشتی) سفارشی ارسال کنید؟\n(در صورت انتخاب «خودکار»، از ویدیو ساخته می‌شود)",
        reply_markup=keyboard
    )

# ============================================
# هندلر دکمه‌های شیشه‌ای
# ============================================
@app.on_callback_query()
async def handle_callbacks(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    data = callback_query.data
    await callback_query.answer()
    
    if user_id not in user_states:
        await callback_query.edit_message_text("❌ لطفاً دوباره /start را بزنید.")
        return
    
    state = user_states[user_id]
    
    if data.startswith("quality_"):
        format_id = data.split("_")[1]
        selected_format = None
        for f in state.get('formats', []):
            if f['format_id'] == format_id:
                selected_format = f
                break
        if not selected_format:
            await callback_query.edit_message_text("❌ فرمت انتخاب شده نامعتبر است.")
            return
        state['selected_format'] = selected_format
        state['step'] = 'processing'
        await callback_query.edit_message_text(f"✅ کیفیت {selected_format['height']}p انتخاب شد. در حال پردازش...")
        await start_processing(client, callback_query.message, user_id, callback_query.from_user)
        return
    
    if data == "default_yes":
        await callback_query.edit_message_text("✅ شروع پردازش با نام اصلی...")
        state['step'] = 'processing'
        await start_processing(client, callback_query.message, user_id, callback_query.from_user)
    
    elif data == "edit_file":
        state['step'] = 'awaiting_new_filename'
        await callback_query.edit_message_text(
            "✏️ نام جدید فایل را وارد کنید (همراه با پسوند، مثل `myvideo.mp4`):\nبرای استفاده از نام فعلی، کلمه `skip` را وارد کنید."
        )
    
    elif data == "edit_thumb_yes":
        state['step'] = 'awaiting_new_thumbnail'
        await callback_query.edit_message_text(
            "🖼️ لطفاً تصویر تامنیل را به صورت عکس (Photo) یا فایل تصویری (Document) ارسال کنید."
        )
    
    elif data == "edit_thumb_no":
        state['step'] = 'processing'
        await callback_query.edit_message_text("✅ تامنیل از ویدیو ساخته می‌شود.")
        await start_processing(client, callback_query.message, user_id, callback_query.from_user)
    
    elif data == "cancel_download" or data == "cancel_upload":
        if user_id in cancel_events:
            cancel_events[user_id].set()
            await callback_query.edit_message_text("⏳ در حال لغو عملیات...")
        else:
            await callback_query.edit_message_text("❌ عملیات لغو در دسترس نیست.")

# ============================================
# دریافت تامنیل سفارشی
# ============================================
@app.on_message(filters.photo & ~filters.command("start"))
async def handle_edit_thumbnail_photo(client, message):
    user_id = message.chat.id
    if user_id not in user_states or user_states[user_id].get('step') != 'awaiting_new_thumbnail':
        await message.reply("❌ شما در مرحله دریافت تامنیل نیستید.")
        return
    thumb_path = f"custom_thumb_{user_id}_{int(time.time())}.jpg"
    try:
        downloaded_path = await client.download_media(message.photo, file_name=thumb_path)
        if downloaded_path:
            user_states[user_id]['thumbnail_path'] = downloaded_path
            user_states[user_id]['step'] = 'processing'
            await message.reply("✅ تامنیل سفارشی دریافت شد. در حال پردازش...")
            await start_processing(client, message, user_id, message.from_user)
        else:
            raise Exception("دانلود تامنیل ناموفق بود")
    except Exception as e:
        await message.reply(f"❌ خطا در دریافت تامنیل: {str(e)}")
        user_states[user_id]['step'] = 'awaiting_new_thumbnail_choice'
        await ask_thumbnail_choice_for_edit(client, message, user_id)

@app.on_message(filters.document & ~filters.command("start"))
async def handle_edit_thumbnail_document(client, message):
    user_id = message.chat.id
    if user_id not in user_states or user_states[user_id].get('step') != 'awaiting_new_thumbnail':
        await message.reply("❌ شما در مرحله دریافت تامنیل نیستید.")
        return
    doc = message.document
    if doc.mime_type and doc.mime_type.startswith('image/'):
        thumb_path = f"custom_thumb_{user_id}_{int(time.time())}.jpg"
        try:
            downloaded_path = await client.download_media(doc, file_name=thumb_path)
            if downloaded_path:
                user_states[user_id]['thumbnail_path'] = downloaded_path
                user_states[user_id]['step'] = 'processing'
                await message.reply("✅ تامنیل سفارشی دریافت شد. در حال پردازش...")
                await start_processing(client, message, user_id, message.from_user)
            else:
                raise Exception("دانلود تامنیل ناموفق بود")
        except Exception as e:
            await message.reply(f"❌ خطا در دریافت تامنیل: {str(e)}")
            user_states[user_id]['step'] = 'awaiting_new_thumbnail_choice'
            await ask_thumbnail_choice_for_edit(client, message, user_id)
    else:
        await message.reply("❌ لطفاً یک فایل تصویری (عکس) ارسال کنید.")

# ============================================
# پردازش اصلی (دانلود و آپلود) با دکمه لغو در هر دو مرحله
# ============================================
async def start_processing(client, message, user_id, user):
    if user_id not in user_states:
        await message.reply("❌ خطا: اطلاعات کاربر یافت نشد.")
        return
    
    state = user_states[user_id]
    url = state['url']
    custom_filename = state.get('custom_filename')
    thumbnail_path = state.get('thumbnail_path')
    link_type = state.get('link_type', 'direct')
    
    if link_type == 'spotify':
        if custom_filename and custom_filename.strip() and custom_filename.lower() != 'skip':
            base_name = custom_filename.strip()
            if '.' not in base_name:
                final_filename = f"{base_name}.mp3"
            else:
                final_filename = base_name
        else:
            final_filename = f"spotify_song_{int(time.time())}.mp3"
        final_filename = re.sub(r'[<>:"/\\|?*]', '_', final_filename)
        use_ytdlp = False
        use_spotify = True
        format_id = None
    elif 'selected_format' in state:
        selected_format = state['selected_format']
        title = state.get('title', 'video')
        height = selected_format['height']
        ext = selected_format.get('ext', 'mp4')
        if custom_filename and custom_filename.strip() and custom_filename.lower() != 'skip':
            base_name = custom_filename.strip()
            if '.' not in base_name:
                final_filename = f"{base_name}_{height}p.{ext}"
            else:
                final_filename = base_name
        else:
            final_filename = f"{title}_{height}p.{ext}"
        final_filename = re.sub(r'[<>:"/\\|?*]', '_', final_filename)
        use_ytdlp = True
        use_spotify = False
        format_id = selected_format['format_id']
    else:
        original_filename = state.get('original_filename')
        if custom_filename and custom_filename.strip() and custom_filename.lower() != 'skip':
            if '.' not in custom_filename:
                ext = os.path.splitext(original_filename)[1]
                final_filename = custom_filename.strip() + ext
            else:
                final_filename = custom_filename.strip()
        else:
            final_filename = original_filename
        use_ytdlp = False
        use_spotify = False
        format_id = None
    
    cancel_event = asyncio.Event()
    cancel_events[user_id] = cancel_event
    
    cancel_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("❌ لغو عملیات", callback_data="cancel_download")]])
    
    if state.get('info_msg_id'):
        try:
            status_msg = await client.edit_message_text(
                chat_id=user_id,
                message_id=state['info_msg_id'],
                text="⌛ Processing Your Link...",
                reply_markup=cancel_keyboard
            )
        except Exception:
            status_msg = await message.reply("⌛ Processing Your Link...", reply_markup=cancel_keyboard)
    else:
        status_msg = await message.reply("⌛ Processing Your Link...", reply_markup=cancel_keyboard)
    state['status_msg_id'] = status_msg.id
    
    try:
        download_start_time = time.time()
        last_edit_time = time.time()
        
        async def progress_callback(percent, downloaded, total, speed):
            nonlocal last_edit_time
            now = time.time()
            if now - last_edit_time >= 1.5 or percent >= 100:
                last_edit_time = now
                elapsed = now - download_start_time
                text = make_progress_text(
                    title="📥 **Download Status**",
                    filename=final_filename,
                    percent=percent,
                    downloaded=downloaded,
                    total=total,
                    speed=speed,
                    elapsed=elapsed
                )
                try:
                    await status_msg.edit_text(text, reply_markup=cancel_keyboard)
                except Exception:
                    pass
        
        if use_spotify:
            await status_msg.edit_text("🎵 **Downloading from Spotify...**", reply_markup=cancel_keyboard)
            try:
                await download_spotify(url, final_filename, progress_callback, cancel_event)
            except Exception as e:
                error_msg = str(e)
                if "spotdl" in error_msg.lower() or "client" in error_msg.lower():
                    raise Exception("دانلود از اسپاتیفای نیاز به تنظیمات اضافی دارد. لطفاً از لینک مستقیم یا یوتیوب استفاده کنید.")
                raise e
        elif use_ytdlp:
            await download_with_ytdlp(url, format_id, final_filename, progress_callback, cancel_event)
        else:
            await download_file_with_aiohttp(url, final_filename, progress_callback, cancel_event)
        
        # بررسی اینکه فایل واقعاً دانلود شده است
        if not os.path.exists(final_filename) or os.path.getsize(final_filename) == 0:
            raise Exception("فایل دانلود نشد. ممکن است لینک نامعتبر باشد یا نیاز به احراز هویت داشته باشد.")
        
        cancel_keyboard_upload = InlineKeyboardMarkup([[InlineKeyboardButton("❌ لغو آپلود", callback_data="cancel_upload")]])
        await status_msg.edit_text("📥 **Download Status**\n✅ دانلود کامل شد!", reply_markup=cancel_keyboard_upload)
        
        is_video = is_video_file(final_filename)
        is_audio = is_audio_file(final_filename)
        thumb_to_use = None
        duration = None
        
        if is_video:
            if thumbnail_path and os.path.exists(thumbnail_path):
                thumb_to_use = thumbnail_path
            else:
                thumb_to_use = f"thumb_{os.path.splitext(final_filename)[0]}.jpg"
                if not generate_thumbnail(final_filename, thumb_to_use):
                    thumb_to_use = None
            duration = get_video_duration(final_filename)
        else:
            if thumbnail_path:
                await status_msg.edit_text(
                    "⚠️ توجه: تامنیل سفارشی فقط برای فایل‌های ویدیویی قابل استفاده است.\n"
                    "فایل شما به‌صورت معمولی ارسال می‌شود.",
                    reply_markup=cancel_keyboard_upload
                )
                await asyncio.sleep(2)
        
        upload_start_time = time.time()
        upload_last_edit_time = time.time()
        
        async def upload_progress(current, total, status_msg, filename, is_video):
            nonlocal upload_start_time, upload_last_edit_time
            now = time.time()
            elapsed = now - upload_start_time
            speed = current / elapsed if elapsed > 0 else 0
            percent = (current / total) * 100 if total else 0
            
            if cancel_event.is_set():
                raise asyncio.CancelledError("عملیات توسط کاربر لغو شد")
            
            if now - upload_last_edit_time >= 1.5 or percent >= 100:
                upload_last_edit_time = now
                text = make_progress_text(
                    title="📤 **Upload Status**",
                    filename=filename,
                    percent=percent,
                    downloaded=current,
                    total=total,
                    speed=speed,
                    elapsed=elapsed
                )
                try:
                    await status_msg.edit_text(text, reply_markup=cancel_keyboard_upload)
                except Exception:
                    pass
        
        await status_msg.edit_text("📤 **Upload Status**\n⏳ در حال آماده‌سازی...", reply_markup=cancel_keyboard_upload)
        
        if is_video:
            sent_msg = await client.send_video(
                chat_id=user_id,
                video=final_filename,
                thumb=thumb_to_use,
                duration=duration or 0,
                supports_streaming=True,
                caption="🎬 فایل ویدیویی شما",
                progress=upload_progress,
                progress_args=(status_msg, final_filename, True)
            )
        else:
            sent_msg = await client.send_document(
                chat_id=user_id,
                document=final_filename,
                caption="📄 فایل شما",
                progress=upload_progress,
                progress_args=(status_msg, final_filename, False)
            )
        
        await status_msg.edit_text("📋 ذخیره نسخه در کانال لاگ...")
        copied_msg = await client.copy_message(
            chat_id=LOG_CHANNEL,
            from_chat_id=user_id,
            message_id=sent_msg.id
        )
        
        user_name = user.first_name or "کاربر"
        if user.last_name:
            user_name += f" {user.last_name}"
        user_link = f'<a href="tg://user?id={user_id}">{user_name}</a>'
        log_text = (
            f"👤 **نام کاربر :** {user_link}\n"
            f"🆔 **آیدی کاربر :** `{user_id}`\n"
            f"📁 **نام فایل :** `{final_filename}`"
        )
        await client.send_message(
            chat_id=LOG_CHANNEL,
            text=log_text,
            parse_mode=ParseMode.HTML,
            reply_to_message_id=copied_msg.id
        )
        
        for f in [final_filename, thumbnail_path, thumb_to_use]:
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass
        
        await status_msg.edit_text("✅ **عملیات با موفقیت انجام شد!** فایل برای شما ارسال گردید و نسخه‌ای در لاگ ذخیره شد.")
    
    except asyncio.CancelledError:
        await status_msg.edit_text("❌ **عملیات لغو شد.** فایل دانلود نشد.")
        for f in [final_filename, thumbnail_path]:
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass
    except Exception as e:
        error_msg = str(e)
        await status_msg.edit_text(f"❌ خطا: {error_msg[:500]}...")
        for f in [final_filename, thumbnail_path]:
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass
    finally:
        if user_id in cancel_events:
            del cancel_events[user_id]
        if user_id in user_states:
            del user_states[user_id]

# ============================================
# اجرای ربات
# ============================================
print("🚀 در حال راه‌اندازی ربات...")
loop = asyncio.get_event_loop()
_ = loop.run_until_complete(app.start())
print("✅ ربات راه‌اندازی شد. منتظر پیام‌های شما...")

from pyrogram import idle
loop.run_until_complete(idle())
loop.run_until_complete(app.stop())