import telebot
import requests
import random
import string
import time
import os
from threading import Thread

BOT_TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)

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

def generate_valid_username(length):
    """
    توليد يوزر صحيح 100%:
    - يبدأ بحرف فقط (a-z)
    - باقي الأحرف: حروف صغيرة + أرقام + underscore
    - ما ينتهي بـ underscore
    """
    # الحرف الأول: فقط حروف صغيرة (a-z)
    first_char = random.choice(string.ascii_lowercase)
    
    # باقي الأحرف: حروف صغيرة + أرقام + underscore
    other_chars = string.ascii_lowercase + string.digits + '_'
    
    # توليد باقي الأحرف
    rest = ''.join(random.choices(other_chars, k=length-1))
    
    username = first_char + rest
    
    # التأكد من عدم الانتهاء بـ underscore
    if username.endswith('_'):
        # استبدال آخر حرف بحرف عشوائي
        username = username[:-1] + random.choice(string.ascii_lowercase)
    
    return username

def search_usernames(chat_id, length, message_id):
    """دالة البحث"""
    found_count = 0
    checked_count = 0
    active_searches[chat_id] = True
    
    while active_searches.get(chat_id, False):
        # توليد يوزر صحيح
        username = generate_valid_username(length)
        
        # فحص التوفر
        is_available = check_telegram_username(username)
        checked_count += 1
        
        if is_available:
            found_count += 1
            bot.send_message(
                chat_id,
                f"✅ **يوزر متاح!**\n"
                f"👤 @{username}\n"
                f"🔗 https://t.me/{username}\n"
                f"📏 {length} أحرف",
                parse_mode='Markdown'
            )
        
        # تحديث الحالة كل 20 محاولة
        if checked_count % 20 == 0:
            try:
                bot.edit_message_text(
                    f"🔍 بحث عن يوزر {length} أحرف\n"
                    f"📊 تم الفحص: {checked_count}\n"
                    f"🎯 تم العثور: {found_count}\n"
                    f"⚡️ السرعة: 2/ثانية",
                    chat_id,
                    message_id
                )
            except:
                pass
        
        time.sleep(0.5)  # سرعة مناسبة
    
    # عند التوقف
    bot.edit_message_text(
        f"🛑 توقف البحث\n"
        f"📊 إجمالي الفحص: {checked_count}\n"
        f"🎯 إجمالي المتاح: {found_count}",
        chat_id,
        message_id
    )

@bot.message_handler(commands=['start'])
def start(message):
    welcome = """
🎯 **بوت البحث عن يوزرات تليجرام**

✅ **المواصفات:**
• يبدأ بحرف (a-z) فقط
• لا يبدأ برقم أبداً
• لا ينتهي بـ _

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
    bot.reply_to(message, "👀 استخدم:\n/search4\n/search5\n/stop")

if __name__ == '__main__':
    print("✅ البوت شغال على Railway...")
    bot.infinity_polling()
