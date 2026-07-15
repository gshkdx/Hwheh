import subprocess
import time
import socket
import socks
import os
import json
import telebot
import threading
from pathlib import Path

# ============== تنظیمات ربات تلگرام ==============
# 🔑 توکن ربات خود را اینجا وارد کنید
TELEGRAM_BOT_TOKEN = "8793482183:AAFFhtwKqtZCNSGk4QjOFZut7RCOzUzzsxU"  # <--- توکن را اینجا جایگزین کنید

# یا از متغیر محیطی بخوانید
# TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

# ================================================

class AetherBot:
    def __init__(self, token=None):
        self.proxy_host = "127.0.0.1"
        self.proxy_port = 1819
        self.process = None
        self.aether_token = self.load_aether_token()
        self.config = self.load_config()
        
    def load_config(self):
        """بارگذاری تنظیمات"""
        config_file = "aether_config.json"
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                return json.load(f)
        return {
            "protocol": 1,
            "mode": 2,
            "aether_token": None,
            "auto_connect": True
        }
    
    def load_aether_token(self):
        """بارگذاری توکن Aether"""
        token_file = Path.home() / '.aether_token'
        if token_file.exists():
            with open(token_file, 'r') as f:
                return f.read().strip()
        return None
    
    def start_aether(self):
        """راه‌اندازی Aether"""
        if not self.aether_token:
            return False
            
        try:
            process = subprocess.Popen(
                ['aether'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # ارسال اطلاعات به Aether
            inputs = [
                str(self.config.get('protocol', 1)) + "\n",
                str(self.config.get('mode', 2)) + "\n",
                self.aether_token + "\n"
            ]
            
            for inp in inputs:
                process.stdin.write(inp)
                process.stdin.flush()
                time.sleep(0.5)
            
            self.process = process
            time.sleep(5)
            return True
        except Exception as e:
            print(f"❌ خطا: {e}")
            return False
    
    def check_connection(self):
        """بررسی اتصال"""
        try:
            sock = socks.socksocket()
            sock.set_proxy(socks.SOCKS5, self.proxy_host, self.proxy_port)
            sock.settimeout(5)
            sock.connect(("8.8.8.8", 53))
            sock.close()
            return True
        except:
            return False
    
    def get_status(self):
        """دریافت وضعیت"""
        if self.check_connection():
            return "✅ آنلاین - پراکسی فعال است"
        return "❌ آفلاین - پراکسی غیرفعال است"


# ============== ربات تلگرام ==============
class TelegramBot:
    def __init__(self, token):
        self.bot = telebot.TeleBot(token)
        self.aether = AetherBot()
        self.setup_handlers()
        
    def setup_handlers(self):
        """تنظیم هندلرهای ربات"""
        
        @self.bot.message_handler(commands=['start'])
        def start(message):
            welcome = """
🤖 **ربات مدیریت Aether**

سلام! من به شما کمک میکنم تا Aether رو مدیریت کنید.

📋 **دستورات موجود:**

/status - بررسی وضعیت اتصال
/connect - اتصال به Aether
/disconnect - قطع اتصال
/set_token [توکن] - تنظیم توکن Aether
/protocol [masque|wireguard|warp] - تغییر پروتکل
/mode [turbo|balanced|thorough|stealth] - تغییر حالت
/help - راهنما

🔗 **آدرس پراکسی:**
`socks://127.0.0.1:1819`
            """
            self.bot.reply_to(message, welcome, parse_mode='Markdown')
        
        @self.bot.message_handler(commands=['status'])
        def status(message):
            status_text = f"""
📊 **وضعیت Aether**

🔹 وضعیت: {self.aether.get_status()}
🔹 آدرس پراکسی: `127.0.0.1:1819`
🔹 پروتکل: {self.aether.config.get('protocol', 'MASQUE')}
🔹 حالت: {self.aether.config.get('mode', 'Balanced')}
            """
            self.bot.reply_to(message, status_text, parse_mode='Markdown')
        
        @self.bot.message_handler(commands=['connect'])
        def connect(message):
            msg = self.bot.reply_to(message, "🔄 در حال اتصال به Aether...")
            
            if self.aether.start_aether():
                time.sleep(3)
                if self.aether.check_connection():
                    self.bot.edit_message_text(
                        "✅ **اتصال برقرار شد!**\n\n"
                        "🔗 پراکسی: `127.0.0.1:1819`\n"
                        "📝 از آدرس زیر استفاده کنید:\n"
                        "`socks://Og@127.0.0.1:1819#hamvex`",
                        chat_id=message.chat.id,
                        message_id=msg.message_id,
                        parse_mode='Markdown'
                    )
                else:
                    self.bot.edit_message_text(
                        "❌ **اتصال ناموفق**\n"
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
            if self.aether.process:
                self.aether.process.terminate()
                self.bot.reply_to(message, "❌ **اتصال قطع شد**")
            else:
                self.bot.reply_to(message, "⚠️ هیچ اتصالی وجود ندارد")
        
        @self.bot.message_handler(commands=['set_token'])
        def set_token(message):
            try:
                # استخراج توکن از پیام
                token = message.text.split(' ', 1)[1]
                if token:
                    # ذخیره توکن
                    token_file = Path.home() / '.aether_token'
                    with open(token_file, 'w') as f:
                        f.write(token.strip())
                    os.chmod(token_file, 0o600)
                    
                    self.aether.aether_token = token
                    self.aether.config['aether_token'] = token
                    
                    self.bot.reply_to(
                        message,
                        f"✅ **توکن با موفقیت تنظیم شد**\n\n"
                        f"🔑 توکن: `{token[:10]}...`\n"
                        f"💡 حالا میتونید با دستور `/connect` متصل شوید"
                    )
                else:
                    self.bot.reply_to(
                        message,
                        "❌ **فرمت اشتباه**\n"
                        "استفاده: `/set_token [توکن شما]`"
                    )
            except IndexError:
                self.bot.reply_to(
                    message,
                    "❌ **توکن را وارد کنید**\n"
                    "استفاده: `/set_token [توکن شما]`"
                )
        
        @self.bot.message_handler(commands=['protocol'])
        def set_protocol(message):
            try:
                protocol = message.text.split(' ', 1)[1].lower()
                protocols = {
                    'masque': 1,
                    'wireguard': 2,
                    'warp': 3
                }
                if protocol in protocols:
                    self.aether.config['protocol'] = protocols[protocol]
                    self.bot.reply_to(
                        message,
                        f"✅ **پروتکل به {protocol.upper()} تغییر یافت**"
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
                modes = {
                    'turbo': 1,
                    'balanced': 2,
                    'thorough': 3,
                    'stealth': 4
                }
                if mode in modes:
                    self.aether.config['mode'] = modes[mode]
                    self.bot.reply_to(
                        message,
                        f"✅ **حالت به {mode.upper()} تغییر یافت**"
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
        
        @self.bot.message_handler(commands=['help'])
        def help_command(message):
            help_text = """
📚 **راهنمای کامل**

**دستورات مدیریت:**
- `/start` - شروع و خوش‌آمدگویی
- `/status` - بررسی وضعیت اتصال
- `/connect` - اتصال به Aether
- `/disconnect` - قطع اتصال

**تنظیمات:**
- `/set_token [توکن]` - تنظیم توکن Aether
- `/protocol [masque|wireguard|warp]` - تغییر پروتکل
- `/mode [turbo|balanced|thorough|stealth]` - تغییر حالت

**نحوه استفاده:**
1. ابتدا توکن را با `/set_token` تنظیم کنید
2. با `/connect` به Aether متصل شوید
3. پراکسی `127.0.0.1:1819` را در برنامه‌ها تنظیم کنید

🔗 **آدرس پراکسی:**
`socks://Og@127.0.0.1:1819#hamvex`
            """
            self.bot.reply_to(message, help_text, parse_mode='Markdown')
        
        # هندلر برای پیام‌های متنی ساده
        @self.bot.message_handler(func=lambda msg: True)
        def echo(message):
            self.bot.reply_to(
                message,
                "🤖 برای مشاهده دستورات از /help استفاده کنید"
            )
    
    def run(self):
        """اجرای ربات"""
        print("🤖 ربات تلگرام در حال اجراست...")
        print(f"🔑 توکن: {TELEGRAM_BOT_TOKEN[:10]}...")
        print("✅ برای شروع با ربات در تلگرام /start را بزنید")
        self.bot.polling(none_stop=True)


# ============== اجرای اصلی ==============
if __name__ == "__main__":
    # نصب پیش‌نیازها
    try:
        import telebot
    except ImportError:
        print("📦 نصب پیش‌نیازها...")
        subprocess.run(['pip', 'install', 'pyTelegramBotAPI', 'pysocks'], shell=True)
    
    # بررسی توکن
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("\n" + "="*50)
        print("⚠️  **توکن ربات تنظیم نشده است!**")
        print("="*50)
        print("\n📝 برای تنظیم توکن، یکی از روش‌ها را انجام دهید:\n")
        print("1️⃣ **ویرایش کد:**")
        print("   در خط 14 کد، توکن را جایگزین کنید:")
        print("   TELEGRAM_BOT_TOKEN = 'YOUR_BOT_TOKEN_HERE'")
        print("\n2️⃣ **متغیر محیطی:**")
        print("   export TELEGRAM_BOT_TOKEN='your_token_here'")
        print("\n3️⃣ **ورودی از کاربر:**")
        token_input = input("\n🔑 لطفا توکن ربات را وارد کنید: ").strip()
        if token_input:
            TELEGRAM_BOT_TOKEN = token_input
            print("✅ توکن با موفقیت دریافت شد")
        else:
            print("❌ توکن معتبر نیست")
            exit(1)
    
    # اجرای ربات
    bot = TelegramBot(TELEGRAM_BOT_TOKEN)
    
    try:
        bot.run()
    except KeyboardInterrupt:
        print("\n👋 خروج از برنامه")
    except Exception as e:
        print(f"❌ خطا: {e}")
