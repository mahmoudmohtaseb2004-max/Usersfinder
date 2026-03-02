import telebot
import requests
import random
import string
import time
import os
from threading import Thread
from pymongo import MongoClient
from datetime import datetime

# التوكن من Railway variables
BOT_TOKEN = os.environ.get('BOT_TOKEN')
MONGO_URI = os.environ.get('MONGO_URI')

bot = telebot.TeleBot(BOT_TOKEN)
active_searches = {}

# الاتصال بـ MongoDB
client = MongoClient(MONGO_URI)
db = client['telegram_bot']
checked_collection = db['checked_usernames']

# إنشاء Index لمنع التكرار
checked_collection.create_index('username', unique=True)
checked_collection.create_index('checked_at')

def is_username_checked(username):
    """التحقق هل اليوزر مفحوص من قبل"""
    return checked_collection.find_one({'username': username}) is not None

def mark_username_checked(username, is_available):
    """تسجيل يوزر مفحوص في MongoDB"""
    try:
        checked_collection.insert_one({
            'username': username,
            'checked_at': datetime.now(),
            'is_available': is_available,
            'length': len(username)
        })
        return True
    except:
        return False  # مكرر

def get_stats():
    """إحصائيات من MongoDB"""
    total = checked_collection.count_documents({})
    available = checked_collection.count_documents({'is_available': True})
    return total, available

def check_telegram_username(username):
    """التحقق من توفر اليوزر"""
    try:
        url = f"https://t.me/{username}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=5)
        return 'tgme_page' not in response.text
    except:
        return False

def generate_valid_username(length):
    """توليد يوزر صحيح"""
    first_char = random.choice(string.ascii_lowercase)
    other_chars = string.ascii_lowercase + string.digits + '_'
    rest = ''.join(random.choices(other_chars, k=length-1))
    username = first_char + rest
    
    if username.endswith('_'):
        username = username[:-1] + random.choice(string.ascii_lowercase)
    
    return username

def search_usernames(chat_id, length, message_id):
    """دالة البحث"""
    found = 0
    checked = 0
    skipped = 0
    active_searches[chat_id] = True
    start_time = time.time()
    
    while active_searches.get(chat_id, False):
        # توليد يوزر جديد
        username = generate_valid_username(length)
        
        # هل مفحوص من قبل؟
        if is_username_checked(username):
            skipped += 1
            continue
        
        # فحص اليوزر
        is_available = check_telegram_username(username)
        checked += 1
        
        # تسجيل في MongoDB
        mark_username_checked(username, is_available)
        
        if is_available:
            found += 1
            elapsed = int(time.time() - start_time)
            bot.send_message(
                chat_id,
                f"🎉 **يوزر متاح!**\n@{username}\n🔗 https://t.me/{username}",
                parse_mode='Markdown'
            )
        
        # تحديث الحالة كل 20 محاولة
        if checked % 20 == 0:
            elapsed = int(time.time() - start_time)
            total, total_available = get_stats()
            try:
                bot.edit_message_text(
                    f"🔍 **بحث {length} أحرف**\n⏱ {elapsed//60}:{elapsed%60:02d}\n📊 الآن: {checked} | 🎯 {found}\n💾 إجمالي: {total:,} | ✨ {total_available}",
                    chat_id,
                    message_id,
                    parse_mode='Markdown'
                )
            except:
                pass
        
        time.sleep(0.4)
    
    # عند التوقف
    elapsed = int(time.time() - start_time)
    total, total_available = get_stats()
    bot.edit_message_text(
        f"🛑 **توقف البحث**\n⏱ {elapsed//60} دقيقة\n📊 فحص: {checked}\n🎯 وجد: {found}\n💾 في DB: {total:,}",
        chat_id,
        message_id,
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['start'])
def start(message):
    total, available = get_stats()
    bot.reply_to(
        message,
        f"🎯 **بوت البحث عن يوزرات تليجرام**\n\n"
        f"📊 إحصائيات:\n"
        f"💾 مفحوص: {total:,}\n"
        f"✨ متاح: {available}\n\n"
        f"⚠️ **ملاحظة مهمة:** تليجرام لا يقبل يوزرات أقل من 5 أحرف\n\n"
        f"**الأوامر:**\n"
        f"/search5 - بحث عن يوزر خماسي (5 أحرف)\n"
        f"/search6 - بحث عن يوزر سداسي (6 أحرف)\n"  
        f"/stats - إحصائيات\n"
        f"/stop - إيقاف البحث",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['stats'])
def stats(message):
    total, available = get_stats()
    bot.reply_to(
        message,
        f"📊 **إحصائيات MongoDB**\n"
        f"💾 إجمالي اليوزرات المفحوصة: {total:,}\n"
        f"✨ المتاحة: {available}\n"
        f"⚡️ بدون تكرار!",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['search5', 'search6'])
def search(message):
    chat_id = message.chat.id
    if active_searches.get(chat_id, False):
        bot.reply_to(message, "⚠️ في بحث نشط! استخدم /stop")
        return
    
    if message.text == '/search5':
        length = 5
        msg_text = "خماسي (5 أحرف)"
    else:
        length = 6
        msg_text = "سداسي (6 أحرف)"
    
    msg = bot.reply_to(message, f"⏳ بدأ البحث عن يوزر {msg_text}...")
    thread = Thread(target=search_usernames, args=(chat_id, length, msg.message_id))
    thread.daemon = True
    thread.start()

@bot.message_handler(commands=['stop'])
def stop(message):
    chat_id = message.chat.id
    if active_searches.get(chat_id, False):
        active_searches[chat_id] = False
        bot.reply_to(message, "🛑 جاري إيقاف البحث...")
    else:
        bot.reply_to(message, "❌ لا يوجد بحث نشط")

@bot.message_handler(func=lambda m: True)
def handle_all(message):
    bot.reply_to(
        message, 
        "👀 **الأوامر المتاحة:**\n"
        "/search5 - بحث عن يوزر خماسي (5 أحرف)\n"
        "/search6 - بحث عن يوزر سداسي (6 أحرف)\n"
        "/stats - عرض الإحصائيات\n"
        "/stop - إيقاف البحث"
    )

if __name__ == '__main__':
    print("✅ البوت شغال مع MongoDB...")
    print("📊 يدعم: 5 و 6 أحرف (حسب سياسة تليجرام)")
    bot.infinity_polling()
