import subprocess
import time
import socket
import socks
import os
import json
import telebot
import threading
import logging
import sys
from pathlib import Path
from datetime import datetime
import signal

# ============== تنظیمات لاگ ==============
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ============== تنظیمات ربات ==============
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # توکن را اینجا وارد کنید

# ==========================================

class AetherManager:
    """مدیریت Aether با قابلیت پایدارسازی"""
    
    def __init__(self):
        self.proxy_host = "127.0.0.1"
        self.proxy_port = 1819
        self.process = None
        self.is_running = False
        self.reconnect_thread = None
        self.stop_reconnect = False
        self.config = self.load_config()
        self.aether_token = self.load_token()
        
    def load_config(self):
        """بارگذاری تنظیمات"""
        config_file = "aether_config.json"
        default_config = {
            "protocol": 1,
            "mode": 2,
            "aether_token": None,
            "auto_connect": True,
            "max_retries": 10,
            "retry_delay": 30,
            "health_check_interval": 60
        }
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    return json.load(f)
            except:
                return default_config
        return default_config
    
    def save_config(self):
        """ذخیره تنظیمات"""
        with open("aether_config.json", 'w') as f:
            json.dump(self.config, f, indent=4)
    
    def load_token(self):
        """بارگذاری توکن"""
        token_file = Path.home() / '.aether_token'
        if token_file.exists():
            try:
                with open(token_file, 'r') as f:
                    return f.read().strip()
            except:
                return None
        return None
    
    def save_token(self, token):
        """ذخیره توکن"""
        token_file = Path.home() / '.aether_token'
        with open(token_file, 'w') as f:
            f.write(token.strip())
        os.chmod(token_file, 0o600)
        self.aether_token = token
        self.config['aether_token'] = token
        self.save_config()
        logger.info("✅ توکن با موفقیت ذخیره شد")
    
    def start_aether(self):
        """راه‌اندازی Aether"""
        if not self.aether_token:
            logger.error("❌ توکن موجود نیست")
            return False
            
        try:
            # اگر قبلاً در حال اجراست، متوقف کن
            if self.process:
                self.stop_aether()
            
            logger.info("🚀 در حال راه‌اندازی Aether...")
            
            # روش اول: استفاده از فایل تنظیمات
            if os.path.exists("aether_config.json"):
                process = subprocess.Popen(
                    ['aether', '--config', 'aether_config.json', '--token', self.aether_token],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )
            else:
                # روش دوم: ورودی تعاملی
                process = subprocess.Popen(
                    ['aether'],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )
                
                inputs = [
                    str(self.config.get('protocol', 1)) + "\n",
                    str(self.config.get('mode', 2)) + "\n",
                    self.aether_token + "\n",
                    "y\n"
                ]
                
                for inp in inputs:
                    process.stdin.write(inp)
                    process.stdin.flush()
                    time.sleep(0.5)
            
            self.process = process
            self.is_running = True
            
            # منتظر بمان تا اتصال برقرار شود
            time.sleep(5)
            
            if self.check_connection():
                logger.info("✅ Aether با موفقیت راه‌اندازی شد")
                return True
            else:
                logger.warning("⚠️ Aether راه‌اندازی شد اما اتصال برقرار نیست")
                return False
                
        except Exception as e:
            logger.error(f"❌ خطا در راه‌اندازی Aether: {e}")
            return False
    
    def stop_aether(self):
        """متوقف کردن Aether"""
        try:
            if self.process:
                self.process.terminate()
                time.sleep(2)
                if self.process.poll() is None:
                    self.process.kill()
                self.process = None
                self.is_running = False
                logger.info("🛑 Aether متوقف شد")
                return True
        except Exception as e:
            logger.error(f"❌ خطا در توقف Aether: {e}")
        return False
    
    def check_connection(self):
        """بررسی اتصال پراکسی"""
        try:
            sock = socks.socksocket()
            sock.set_proxy(socks.SOCKS5, self.proxy_host, self.proxy_port)
            sock.settimeout(5)
            sock.connect(("8.8.8.8", 53))
            sock.close()
            return True
        except Exception as e:
            logger.debug(f"⚠️ خطا در بررسی اتصال: {e}")
            return False
    
    def health_check(self):
        """بررسی سلامت اتصال با بازیابی خودکار"""
        if not self.check_connection():
            logger.warning("⚠️ اتصال قطع شده است، در حال بازیابی...")
            self.restart_aether()
            return False
        return True
    
    def restart_aether(self):
        """راه‌اندازی مجدد Aether با بازیابی"""
        logger.info("🔄 در حال راه‌اندازی مجدد Aether...")
        self.stop_aether()
        time.sleep(5)
        return self.start_aether()
    
    def start_health_monitor(self):
        """شروع مانیتورینگ سلامت"""
        if self.reconnect_thread and self.reconnect_thread.is_alive():
            return
            
        self.stop_reconnect = False
        
        def monitor():
            logger.info("🔄 مانیتورینگ سلامت شروع شد")
            while not self.stop_reconnect:
                try:
                    if self.is_running:
                        if not self.health_check():
                            logger.warning("⚠️ مشکل در اتصال، تلاش برای بازیابی...")
                    else:
                        logger.info("🔄 Aether خاموش است، تلاش برای راه‌اندازی...")
                        self.start_aether()
                    
                    # منتظر بمان تا دوباره بررسی کند
                    delay = self.config.get('health_check_interval', 60)
                    time.sleep(delay)
                    
                except Exception as e:
                    logger.error(f"❌ خطا در مانیتورینگ: {e}")
                    time.sleep(10)
            
            logger.info("🔄 مانیتورینگ سلامت متوقف شد")
        
        self.reconnect_thread = threading.Thread(target=monitor, daemon=True)
        self.reconnect_thread.start()
    
    def stop_health_monitor(self):
        """متوقف کردن مانیتورینگ"""
        self.stop_reconnect = True
        if self.reconnect_thread:
            self.reconnect_thread.join(timeout=5)
    
    def get_status(self):
        """دریافت وضعیت کامل"""
        status = {
            "is_running": self.is_running,
            "proxy_available": self.check_connection(),
            "proxy_host": self.proxy_host,
            "proxy_port": self.proxy_port,
            "protocol": self.config.get('protocol', 1),
            "mode": self.config.get('mode', 2),
            "has_token": bool(self.aether_token),
            "monitor_active": bool(self.reconnect_thread and self.reconnect_thread.is_alive())
        }
        return status


# ============== ربات تلگرام ==============
class AetherTelegramBot:
    def __init__(self, token):
        self.bot = telebot.TeleBot(token)
        self.aether = AetherManager()
        self.setup_handlers()
        self.running = True
        
        # ثبت سیگنال برای خروج ایمن
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """مدیریت سیگنال‌ها برای خروج ایمن"""
        logger.info("📨 دریافت سیگنال خروج")
        self.running = False
        self.aether.stop_health_monitor()
        self.aether.stop_aether()
        sys.exit(0)
    
    def setup_handlers(self):
        """تنظیم هندلرهای ربات"""
        
        @self.bot.message_handler(commands=['start'])
        def start(message):
            welcome = """
🤖 **ربات مدیریت Aether v2.0**

سلام! من یک ربات پایدار برای مدیریت Aether هستم.

📋 **دستورات موجود:**

🔹 **مدیریت:**
/status - بررسی وضعیت اتصال
/connect - اتصال به Aether
/disconnect - قطع اتصال
/restart - راه‌اندازی مجدد

🔹 **تنظیمات:**
/set_token [توکن] - تنظیم توکن
/protocol [masque|wireguard|warp] - تغییر پروتکل
/mode [turbo|balanced|thorough|stealth] - تغییر حالت

🔹 **اطلاعات:**
/help - راهنما
/logs - مشاهده لاگ‌ها
/ping - بررسی زنده بودن ربات

🔗 **آدرس پراکسی:**
`socks://127.0.0.1:1819`

💡 **ربات به صورت خودکار اتصال را حفظ میکند**
            """
            self.bot.reply_to(message, welcome, parse_mode='Markdown')
        
        @self.bot.message_handler(commands=['ping'])
        def ping(message):
            """بررسی زنده بودن ربات"""
            self.bot.reply_to(message, "🏓 **پنگ!** ربات فعال است ✅")
        
        @self.bot.message_handler(commands=['status'])
        def status(message):
            status = self.aether.get_status()
            
            status_text = f"""
📊 **وضعیت Aether**

🔹 **وضعیت:** {'✅ آنلاین' if status['proxy_available'] else '❌ آفلاین'}
🔹 **در حال اجرا:** {'✅' if status['is_running'] else '❌'}
🔹 **مانیتورینگ:** {'✅ فعال' if status['monitor_active'] else '❌ غیرفعال'}

🔹 **آدرس پراکسی:** `{status['proxy_host']}:{status['proxy_port']}`
🔹 **پروتکل:** {self._get_protocol_name(status['protocol'])}
🔹 **حالت:** {self._get_mode_name(status['mode'])}
🔹 **توکن:** {'✅ موجود' if status['has_token'] else '❌ وجود ندارد'}

📝 **آدرس کامل:**
`socks://Og@127.0.0.1:1819#hamvex`
            """
            self.bot.reply_to(message, status_text, parse_mode='Markdown')
        
        @self.bot.message_handler(commands=['connect'])
        def connect(message):
            msg = self.bot.reply_to(message, "🔄 در حال اتصال به Aether...")
            
            if self.aether.start_aether():
                self.aether.start_health_monitor()
                
                time.sleep(3)
                if self.aether.check_connection():
                    self.bot.edit_message_text(
                        "✅ **اتصال با موفقیت برقرار شد!**\n\n"
                        "🔗 پراکسی: `127.0.0.1:1819`\n"
                        "🔄 مانیتورینگ خودکار فعال شد\n"
                        "📝 آدرس پراکسی:\n"
                        "`socks://Og@127.0.0.1:1819#hamvex`",
                        chat_id=message.chat.id,
                        message_id=msg.message_id,
                        parse_mode='Markdown'
                    )
                else:
                    self.bot.edit_message_text(
                        "⚠️ **اتصال ناقص**\n"
                        "Aether راه‌اندازی شد اما پراکسی در دسترس نیست.\n"
                        "لطفا توکن را بررسی کنید.",
                        chat_id=message.chat.id,
                        message_id=msg.message_id
                    )
            else:
                self.bot.edit_message_text(
                    "❌ **خطا در راه‌اندازی**\n"
                    "لطفا توکن را تنظیم کنید: `/set_token [توکن]`",
                    chat_id=message.chat.id,
                    message_id=msg.message_id
                )
        
        @self.bot.message_handler(commands=['disconnect'])
        def disconnect(message):
            self.aether.stop_health_monitor()
            if self.aether.stop_aether():
                self.bot.reply_to(message, "❌ **اتصال قطع شد**\n🔄 مانیتورینگ غیرفعال شد")
            else:
                self.bot.reply_to(message, "⚠️ **هیچ اتصالی وجود ندارد**")
        
        @self.bot.message_handler(commands=['restart'])
        def restart(message):
            msg = self.bot.reply_to(message, "🔄 در حال راه‌اندازی مجدد...")
            
            self.aether.stop_health_monitor()
            self.aether.stop_aether()
            time.sleep(3)
            
            if self.aether.start_aether():
                self.aether.start_health_monitor()
                self.bot.edit_message_text(
                    "✅ **راه‌اندازی مجدد با موفقیت انجام شد**",
                    chat_id=message.chat.id,
                    message_id=msg.message_id
                )
            else:
                self.bot.edit_message_text(
                    "❌ **راه‌اندازی مجدد ناموفق**",
                    chat_id=message.chat.id,
                    message_id=msg.message_id
                )
        
        @self.bot.message_handler(commands=['set_token'])
        def set_token(message):
            try:
                token = message.text.split(' ', 1)[1]
                if token and len(token) > 10:
                    self.aether.save_token(token)
                    self.bot.reply_to(
                        message,
                        f"✅ **توکن با موفقیت تنظیم شد**\n\n"
                        f"🔑 توکن: `{token[:10]}...`\n"
                        f"💡 حالا میتونید با `/connect` متصل شوید"
                    )
                else:
                    self.bot.reply_to(
                        message,
                        "❌ **توکن نامعتبر**\n"
                        "لطفا توکن معتبر وارد کنید"
                    )
            except IndexError:
                self.bot.reply_to(
                    message,
                    "❌ **فرمت اشتباه**\n"
                    "استفاده: `/set_token [توکن شما]`"
                )
        
        @self.bot.message_handler(commands=['protocol'])
        def set_protocol(message):
            try:
                protocol = message.text.split(' ', 1)[1].lower()
                protocols = {'masque': 1, 'wireguard': 2, 'warp': 3}
                if protocol in protocols:
                    self.aether.config['protocol'] = protocols[protocol]
                    self.aether.save_config()
                    self.bot.reply_to(
                        message,
                        f"✅ **پروتکل به {protocol.upper()} تغییر یافت**\n"
                        f"🔄 برای اعمال تغییرات: `/restart`"
                    )
                else:
                    self.bot.reply_to(
                        message,
                        "❌ **پروتکل نامعتبر**\n"
                        "گزینه‌ها: `masque`, `wireguard`, `warp`"
                    )
            except:
                self.bot.reply_to(
                    message,
                    "❌ **فرمت اشتباه**\n"
                    "استفاده: `/protocol [masque|wireguard|warp]`"
                )
        
        @self.bot.message_handler(commands=['mode'])
        def set_mode(message):
            try:
                mode = message.text.split(' ', 1)[1].lower()
                modes = {'turbo': 1, 'balanced': 2, 'thorough': 3, 'stealth': 4}
                if mode in modes:
                    self.aether.config['mode'] = modes[mode]
                    self.aether.save_config()
                    self.bot.reply_to(
                        message,
                        f"✅ **حالت به {mode.upper()} تغییر یافت**\n"
                        f"🔄 برای اعمال تغییرات: `/restart`"
                    )
                else:
                    self.bot.reply_to(
                        message,
                        "❌ **حالت نامعتبر**\n"
                        "گزینه‌ها: `turbo`, `balanced`, `thorough`, `stealth`"
                    )
            except:
                self.bot.reply_to(
                    message,
                    "❌ **فرمت اشتباه**\n"
                    "استفاده: `/mode [turbo|balanced|thorough|stealth]`"
                )
        
        @self.bot.message_handler(commands=['logs'])
        def get_logs(message):
            try:
                if os.path.exists("bot.log"):
                    with open("bot.log", 'r') as f:
                        logs = f.read().split('\n')[-50:]  # آخرین 50 خط
                        log_text = "📋 **آخرین لاگ‌ها:**\n```\n" + "\n".join(logs) + "\n```"
                        
                        if len(log_text) > 4000:
                            log_text = "📋 **لاگ‌ها (قسمتی):**\n```\n" + "\n".join(logs[-20:]) + "\n```"
                        
                        self.bot.reply_to(message, log_text, parse_mode='Markdown')
                else:
                    self.bot.reply_to(message, "❌ فایل لاگ وجود ندارد")
            except Exception as e:
                self.bot.reply_to(message, f"❌ خطا در خواندن لاگ: {e}")
        
        @self.bot.message_handler(commands=['help'])
        def help_command(message):
            help_text = """
📚 **راهنمای کامل ربات**

**دستورات مدیریت:**
- `/start` - شروع و خوش‌آمدگویی
- `/status` - بررسی وضعیت اتصال
- `/connect` - اتصال به Aether
- `/disconnect` - قطع اتصال
- `/restart` - راه‌اندازی مجدد

**تنظیمات:**
- `/set_token [توکن]` - تنظیم توکن Aether
- `/protocol [masque|wireguard|warp]` - تغییر پروتکل
- `/mode [turbo|balanced|thorough|stealth]` - تغییر حالت

**اطلاعات:**
- `/help` - این راهنما
- `/logs` - مشاهده لاگ‌ها
- `/ping` - بررسی زنده بودن ربات

**🔧 ویژگی‌های پایدارسازی:**
- ✅ مانیتورینگ خودکار اتصال
- ✅ راه‌اندازی مجدد خودکار در صورت قطعی
- ✅ ذخیره و بازیابی تنظیمات
- ✅ مدیریت خطا و لاگ‌گیری

**🔗 آدرس پراکسی:**
`socks://Og@127.0.0.1:1819#hamvex`
            """
            self.bot.reply_to(message, help_text, parse_mode='Markdown')
        
        # هندلر خطا
        @self.bot.message_handler(func=lambda msg: True)
        def handle_all(message):
            self.bot.reply_to(
                message,
                "🤖 برای مشاهده دستورات از /help استفاده کنید"
            )
    
    def _get_protocol_name(self, protocol_id):
        """دریافت نام پروتکل"""
        protocols = {1: 'MASQUE', 2: 'WireGuard', 3: 'WARP-in-WARP'}
        return protocols.get(protocol_id, 'نامشخص')
    
    def _get_mode_name(self, mode_id):
        """دریافت نام حالت"""
        modes = {1: 'Turbo', 2: 'Balanced', 3: 'Thorough', 4: 'Stealth'}
        return modes.get(mode_id, 'نامشخص')
    
    def run(self):
        """اجرای پایدار ربات"""
        logger.info("="*60)
        logger.info("🤖 راه‌اندازی ربات Aether v2.0")
        logger.info("="*60)
        
        # شروع مانیتورینگ خودکار اگر توکن موجود باشد
        if self.aether.aether_token:
            logger.info("🔑 توکن موجود است، راه‌اندازی خودکار...")
            if self.aether.start_aether():
                self.aether.start_health_monitor()
                logger.info("✅ Aether راه‌اندازی شد")
        else:
            logger.warning("⚠️ توکن موجود نیست، لطفا با /set_token تنظیم کنید")
        
        logger.info("📱 ربات در حال اجراست...")
        logger.info("🔄 مانیتورینگ خودکار فعال است")

        # اجرای ربات با مدیریت خطا
        while self.running:
            try:
                self.bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
            except Exception as e:
                logger.error(f"❌ خطا در polling: {e}")
                logger.info("🔄 تلاش مجدد در 5 ثانیه...")
                time.sleep(5)
        
        logger.info("👋 خروج از برنامه")


# ============== اجرای اصلی ==============
if __name__ == "__main__":
    # بررسی توکن
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("\n" + "="*50)
        print("⚠️  **توکن ربات تنظیم نشده است!**")
        print("="*50)
        print("\n📝 روش‌های تنظیم توکن:\n")
        print("1️⃣ **ویرایش کد:**")
        print("   در خط 25، توکن را جایگزین کنید:")
        print("   TELEGRAM_BOT_TOKEN = 'your_token_here'")
        print("\n2️⃣ **متغیر محیطی:**")
        print("   export TELEGRAM_BOT_TOKEN='your_token_here'")
        print("\n3️⃣ **ورودی مستقیم:**")
        
        token_input = input("\n🔑 لطفا توکن ربات را وارد کنید: ").strip()
        if token_input:
            TELEGRAM_BOT_TOKEN = token_input
            print("✅ توکن با موفقیت دریافت شد")
        else:
            print("❌ توکن معتبر نیست")
            sys.exit(1)
    
    # اجرای ربات
    bot = AetherTelegramBot(TELEGRAM_BOT_TOKEN)
    bot.run()
