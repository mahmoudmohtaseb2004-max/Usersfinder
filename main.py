
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
    """توليد يوزر صحيح - مع التأكد أن الطول 5 على الأقل"""
    
    # إذا الطول المطلوب أقل من 5، ارفعه لـ 5
    if length < 5:
        length = 5
    
    first_char = random.choice(string.ascii_lowercase)
    other_chars = string.ascii_lowercase + string.digits + '_'
    rest = ''.join(random.choices(other_chars, k=length-1))
    username = first_char + rest
    
    if username.endswith('_'):
        username = username[:-1] + random.choice(string.ascii_lowercase)
    
    return username

def search_usernames(chat_id, length, message_id):
    """دالة البحث - فقط يوزرات 5 أحرف فأكثر"""
    found = 0
    checked = 0
    skipped = 0
    active_searches[chat_id] = True
    start_time = time.time()
    
    while active_searches.get(chat_id, False):
        # توليد يوزر جديد
        username = generate_valid_username(length)
        
        # شرط مهم: إذا طول اليوزر أقل من 5، تجاهله فوراً
        if len(username) < 5:
            skipped += 1
            continue
        
        # هل مفحوص من قبل؟
        if is_username_checked(username):
            skipped += 1
            continue
        
        # فحص اليوزر
        is_available = check_telegram_username(username)
        checked += 1
        
        # تسجيل في MongoDB
        mark_username_checked(username, is_available)
        
        # نبعت فقط إذا كان متاح وطوله 5 أو أكثر
        if is_available and len(username) >= 5:
            found += 1
            elapsed = int(time.time() - start_time)
            
            # رسالة اليوزر المتاح
            bot.send_message(
                chat_id,
                f"🎉 **يوزر متاح!**\n"
                f"👤 @{username}\n"
                f"📏 {len(username)} أحرف (مجاني)\n"
                f"⏱ بعد {elapsed//60} دقيقة و {elapsed%60} ثانية\n"
                f"🔗 https://t.me/{username}",
                parse_mode='Markdown'
            )
        
        # تحديث الحالة كل 20 محاولة
        if checked % 20 == 0:
            elapsed = int(time.time() - start_time)
            total, total_available = get_stats()
            try:
                progress_msg = (
                    f"🔍 **بحث {length} أحرف**\n"
                    f"⏱ الوقت: {elapsed//60}:{elapsed%60:02d}\n"
                    f"📊 هذه الجلسة:\n"
                    f"   ✓ فحص: {checked}\n"
                    f"   🎯 وجد: {found}\n"
                    f"   🔄 تخطي: {skipped} (قصير/مكرر)\n\n"
                    f"💾 قاعدة البيانات:\n"
                    f"   📁 إجمالي مفحوص: {total:,}\n"
                    f"   ✨ إجمالي متاح: {total_available}"
                )
                bot.edit_message_text(progress_msg, chat_id, message_id, parse_mode='Markdown')
            except:
                pass
        
        time.sleep(0.4)
    
    # عند التوقف
    elapsed = int(time.time() - start_time)
    total, total_available = get_stats()
    
    final_msg = (
        f"🛑 **توقف البحث**\n"
        f"⏱ استمر: {elapsed//60} دقيقة\n\n"
        f"📊 إحصائيات الجلسة:\n"
        f"   ✓ فحص: {checked}\n"
        f"   🎯 وجد: {found}\n"
        f"   🔄 تخطي: {skipped}\n\n"
        f"💾 إجمالي في MongoDB:\n"
        f"   📁 كل اليوزرات: {total:,}\n"
        f"   ✨ المتاحة: {total_available}"
    )
    bot.edit_message_text(final_msg, chat_id, message_id, parse_mode='Markdown')

@bot.message_handler(commands=['start'])
def start(message):
    total, available = get_stats()
    welcome_msg = (
        f"🎯 **بوت البحث عن يوزرات تليجرام المجانية**\n\n"
        f"📊 **إحصائيات عامة:**\n"
        f"💾 يوزرات مفحوصة: {total:,}\n"
        f"✨ يوزرات متاحة: {available}\n\n"
        f"⚠️ **مهم:**\n"
        f"• البوت يبحث فقط عن يوزرات **5 أحرف فأكثر** (المجانية)\n"
        f"• اليوزرات الأقل من 5 أحرف للبيع على Fragment فقط\n"
        f"• جميع اليوزرات المفحوصة **تُحفظ في قاعدة بيانات** لمنع التكرار\n\n"
        f"**الأوامر المتاحة:**\n"
        f"/search5 - 🔍 بحث عن يوزر خماسي (5 أحرف)\n"
        f"/search6 - 🔍 بحث عن يوزر سداسي (6 أحرف)\n"
        f"/search7 - 🔍 بحث عن يوزر سباعي (7 أحرف)\n"
        f"/stats - 📊 عرض الإحصائيات\n"
        f"/stop - 🛑 إيقاف البحث\n\n"
        f"✨ **البوت يعمل 24/7 على Railway مع MongoDB**"
    )
    bot.reply_to(message, welcome_msg, parse_mode='Markdown')

@bot.message_handler(commands=['stats'])
def stats(message):
    total, available = get_stats()
    
    # إحصائيات إضافية
    total_5 = checked_collection.count_documents({'length': 5})
    total_6 = checked_collection.count_documents({'length': 6})
    total_7 = checked_collection.count_documents({'length': 7})
    available_5 = checked_collection.count_documents({'length': 5, 'is_available': True})
    available_6 = checked_collection.count_documents({'length': 6, 'is_available': True})
    available_7 = checked_collection.count_documents({'length': 7, 'is_available': True})
    
    stats_msg = (
        f"📊 **إحصائيات MongoDB**\n\n"
        f"💾 **الإجمالي:**\n"
        f"• كل اليوزرات: {total:,}\n"
        f"• المتاحة: {available}\n\n"
        f"📏 **حسب الطول:**\n"
        f"• 5 أحرف: {total_5:,} مفحوص | {available_5} متاح\n"
        f"• 6 أحرف: {total_6:,} مفحوص | {available_6} متاح\n"
        f"• 7 أحرف: {total_7:,} مفحوص | {available_7} متاح\n\n"
        f"⚡️ **معلومات:**\n"
        f"• لا يوجد أي يوزر مكرر\n"
        f"• آخر تحديث: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    bot.reply_to(message, stats_msg, parse_mode='Markdown')

@bot.message_handler(commands=['search5', 'search6', 'search7'])
def search(message):
    chat_id = message.chat.id
    
    if active_searches.get(chat_id, False):
        bot.reply_to(message, "⚠️ في بحث نشط! استخدم /stop أولاً")
        return
    
    if message.text == '/search5':
        length = 5
        msg_text = "خماسي (5 أحرف)"
    elif message.text == '/search6':
        length = 6
        msg_text = "سداسي (6 أحرف)"
    else:
        length = 7
        msg_text = "سباعي (7 أحرف)"
    
    msg = bot.reply_to(
        message, 
        f"⏳ **بدء البحث عن يوزر {msg_text}**\n"
        f"📊 جاري التحميل...",
        parse_mode='Markdown'
    )
    
    thread = Thread(target=search_usernames, args=(chat_id, length, msg.message_id))
    thread.daemon = True
    thread.start()

@bot.message_handler(commands=['stop'])
def stop(message):
    chat_id = message.chat.id
    
    if active_searches.get(chat_id, False):
        active_searches[chat_id] = False
        bot.reply_to(message, "🛑 **جاري إيقاف البحث وحفظ التقدم...**", parse_mode='Markdown')
    else:
        bot.reply_to(message, "❌ **لا يوجد بحث نشط حالياً**", parse_mode='Markdown')

@bot.message_handler(func=lambda m: True)
def handle_all(message):
    bot.reply_to(
        message,
        "👀 **الأوامر المتاحة:**\n"
        "/search5 - بحث عن يوزر خماسي\n"
        "/search6 - بحث عن يوزر سداسي\n"
        "/search7 - بحث عن يوزر سباعي\n"
        "/stats - عرض الإحصائيات\n"
        "/stop - إيقاف البحث"
    )

if __name__ == '__main__':
    print("✅ البوت شغال مع MongoDB...")
    print("📊 يبحث فقط عن يوزرات 5 أحرف فأكثر (مجانية)")
    bot.infinity_polling()
