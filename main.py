import os
import re
import logging
import telebot
import yt_dlp
from pathlib import Path

logging.basicConfig(level=logging.INFO)

TOKEN = "8793482183:AAEaY4MKp_-CCURz3OK3cnJ-Av8f4MVSmDQ"
bot = telebot.TeleBot(TOKEN)
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def extract_instagram_url(text):
    pattern = r'(https?://(?:www\.)?instagram\.com/(?:reel|p|tv)/[A-Za-z0-9_-]+/?[^\s]*)'
    match = re.search(pattern, text)
    return match.group(0) if match else None

def download_instagram_video(url):
    ydl_opts = {
        'outtmpl': f'{DOWNLOAD_FOLDER}/%(id)s.%(ext)s',
        'quiet': False,  # ↙️ تغییر به False برای دیدن جزئیات
        'no_warnings': False,
        'merge_output_format': 'mp4',
        # 'cookiefile': 'cookies.txt',  # اگه کوکی داری فعال کن
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info.get('id')
            
            # پیدا کردن فایل دانلود شده
            for ext in ['mp4', 'mkv', 'webm']:
                temp_path = Path(DOWNLOAD_FOLDER) / f"{video_id}.{ext}"
                if temp_path.exists():
                    return str(temp_path)
            return None
            
    except Exception as e:
        logging.error(f"❌ خطای دانلود: {e}")
        return None

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🎬 لینک اینستاگرام رو بفرست تا دانلود کنم.")

@bot.message_handler(func=lambda msg: True)
def handle(message):
    url = extract_instagram_url(message.text)
    
    if not url:
        bot.reply_to(message, "❌ لینک معتبر نیست!")
        return
    
    status = bot.reply_to(message, "⏳ دانلود...")
    
    file_path = download_instagram_video(url)
    
    if not file_path:
        bot.edit_message_text("❌ دانلود نشد! احتمالاً نیاز به کوکی داری.", 
                            message.chat.id, status.message_id)
        return
    
    try:
        with open(file_path, 'rb') as f:
            bot.send_video(message.chat.id, f, caption="✅ دانلود شد!")
        os.remove(file_path)
        bot.delete_message(message.chat.id, status.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {e}", message.chat.id, status.message_id)

if __name__ == "__main__":
    print("🚀 ربات روشن شد...")
    bot.infinity_polling()
