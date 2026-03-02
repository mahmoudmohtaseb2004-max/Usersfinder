import telebot
import requests
import random
import string
import time
import os
from threading import Thread

# توكن البوت من متغيرات البيئة
BOT_TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)

# تخزين حالات البحث
active_searches = {}

def check_telegram_username(username):
    """التحقق من توفر يوزر تليجرام"""
    try:
        url = f"https://t.me/{username}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=5)
        return 'tgme_page' not in response.text
    except:
        return False

def search_usernames(chat_id, length, message_id):
    """دالة البحث"""
    letters = string.ascii_lowercase + string.digits
    found_count = 0
    checked_count = 0
    active_searches[chat_id] = True
    
    while active_searches.get(chat_id, False):
        username = ''.join(random.choices(letters, k=length))
        is_available = check_telegram_username(username)
        checked_count += 1
        
        if is_available:
            found_count += 1
            bot.send_message(
                chat_id,
                f"✅ **يوزر متاح!**\n@{username}\n🔗 https://t.me/{username}",
                parse_mode='Markdown'
            )
        
        if checked_count % 20 == 0:
            try:
                bot.edit_message_text(
                    f"🔍 بحث {length} أحرف\n📊 فحص: {checked_count}\n🎯 وجد: {found_count}",
                    chat_id,
                    message_id
                )
            except:
                pass
        
        time.sleep(0.3)  # سرعة متوسطة
    
    # عند التوقف
    bot.edit_message_text(
        f"🛑 توقف البحث\n📊 إجمالي الفحص: {checked_count}\n🎯 تم العثور: {found_count}",
        chat_id,
        message_id
    )

@bot.message_handler(commands=['start'])
def start(message):
    welcome = """
🎯 **بوت البحث عن يوزرات تليجرام**

**الأوامر:**
🔹 /search4 - بحث عن يوزر رباعي
🔹 /search5 - بحث عن يوزر خماسي
🔹 /stop - إيقاف البحث

⚡️ يعمل 24/7 على Railway
"""
    bot.reply_to(message, welcome, parse_mode='Markdown')

@bot.message_handler(commands=['search4', 'search5'])
def search(message):
    chat_id = message.chat.id
    
    if active_searches.get(chat_id, False):
        bot.reply_to(message, "⚠️ في بحث نشط! استخدم /stop أولاً")
        return
    
    length = 4 if message.text == '/search4' else 5
    msg = bot.reply_to(message, f"⏳ بدأ البحث عن يوزر {length} أحرف...")
    
    thread = Thread(target=search_usernames, args=(chat_id, length, msg.message_id))
    thread.daemon = True
    thread.start()

@bot.message_handler(commands=['stop'])
def stop(message):
    chat_id = message.chat.id
    
    if active_searches.get(chat_id, False):
        active_searches[chat_id] = False
        bot.reply_to(message, "🛑 تم إيقاف البحث")
    else:
        bot.reply_to(message, "❌ لا يوجد بحث نشط")

@bot.message_handler(func=lambda m: True)
def handle_all(message):
    bot.reply_to(message, "👀 استخدم /search4 أو /search5")

if __name__ == '__main__':
    print("✅ البوت شغال على Railway...")
    bot.infinity_polling()
