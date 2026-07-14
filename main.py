import os
import re
import telebot
import yt_dlp
from pathlib import Path

# ========== تنظیمات ==========
TOKEN = "8793482183:AAEaY4MKp_-CCURz3OK3cnJ-Av8f4MVSmDQ"

bot = telebot.TeleBot(TOKEN)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# ========== توابع کمکی ==========

def extract_instagram_url(text):
    """لینک اینستاگرام را از متن استخراج می‌کند"""
    pattern = r'(https?://(?:www\.)?instagram\.com/(?:reel|p|tv)/[A-Za-z0-9_-]+/?[^\s]*)'
    match = re.search(pattern, text)
    return match.group(0) if match else None

def download_instagram_video(url):
    """ویدیو را دانلود کرده و مسیر فایل را برمی‌گرداند"""
    ydl_opts = {
        'outtmpl': f'{DOWNLOAD_FOLDER}/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'merge_output_format': 'mp4',
        'cookiefile': 'cookies.txt',  # اگر کوکی دارید فعال کنید
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info.get('id')
            ext = info.get('ext', 'mp4')
            file_path = Path(DOWNLOAD_FOLDER) / f"{video_id}.{ext}"
            
            # چک کردن پسوندهای احتمالی
            for ext in ['mp4', 'mkv', 'webm']:
                temp_path = Path(DOWNLOAD_FOLDER) / f"{video_id}.{ext}"
                if temp_path.exists():
                    return str(temp_path)
            
            return str(file_path) if file_path.exists() else None
    
    except Exception as e:
        print(f"خطا در دانلود: {e}")
        return None

# ========== دستورات ربات ==========

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(
        message,
        "🎬 سلام! لینک ویدیوی اینستاگرام رو برام بفرست تا برات دانلود کنم.\n\n"
        "مثال:\n"
        "https://www.instagram.com/reel/XXXXX/\n"
        "https://www.instagram.com/p/XXXXX/"
    )

@bot.message_handler(func=lambda msg: True)
def handle_instagram_link(message):
    text = message.text
    
    # استخراج لینک
    url = extract_instagram_url(text)
    
    if not url:
        bot.reply_to(
            message,
            "❌ لینک معتبر اینستاگرام پیدا نشد!\n"
            "لطفاً لینک پست، ریل یا تی‌وی رو بفرست."
        )
        return
    
    # اعلام شروع دانلود
    status_msg = bot.reply_to(message, "⏳ در حال دانلود ویدیو... لطفاً صبر کنید.")
    
    # دانلود ویدیو
    file_path = download_instagram_video(url)
    
    if not file_path or not os.path.exists(file_path):
        bot.edit_message_text(
            "❌ دانلود ناموفق!\n"
            "ممکنه لینک اشتباه باشه یا اینستاگرام محدودیت زده.",
            chat_id=message.chat.id,
            message_id=status_msg.message_id
        )
        return
    
    # ارسال ویدیو به کاربر
    try:
        with open(file_path, 'rb') as video:
            bot.send_video(
                message.chat.id,
                video,
                caption="✅ ویدیوی شما آماده است! 🎥",
                supports_streaming=True
            )
        
        # پاک کردن پیام وضعیت
        bot.delete_message(message.chat.id, status_msg.message_id)
        
        # حذف فایل از سرور
        os.remove(file_path)
        
    except Exception as e:
        bot.edit_message_text(
            f"❌ خطا در ارسال ویدیو: {str(e)}",
            chat_id=message.chat.id,
            message_id=status_msg.message_id
        )

# ========== اجرا ==========
if __name__ == "__main__":
    print("🚀 ربات دانلود اینستاگرام روشن شد...")
    bot.infinity_polling()
