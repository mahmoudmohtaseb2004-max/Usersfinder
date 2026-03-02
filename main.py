import telebot
import requests
import random
import string
import time
import os
from threading import Thread
from pymongo import MongoClient
from datetime import datetime, timedelta

BOT_TOKEN = os.environ.get('BOT_TOKEN')
MONGO_URI = os.environ.get('MONGO_URI')

bot = telebot.TeleBot(BOT_TOKEN)
active_searches = {}

client = MongoClient(MONGO_URI)
db = client['telegram_bot']
checked_collection = db['checked_usernames']

checked_collection.create_index('username', unique=True)
checked_collection.create_index('checked_at')

# ================= ADMIN =================
ADMIN_USERNAME = "iitsMahmoudi"  # غيرها لاسم المستخدم حقك

def is_admin(username):
    if not username:
        return False
    return username.lower() == ADMIN_USERNAME.lower()

# ================= DATABASE =================

def is_username_checked(username):
    return checked_collection.find_one({'username': username}) is not None

def mark_username_checked(username, is_available):
    try:
        checked_collection.insert_one({
            'username': username,
            'checked_at': datetime.now(),
            'is_available': is_available,
            'length': len(username)
        })
        return True
    except:
        return False

def get_stats():
    total = checked_collection.count_documents({})
    available = checked_collection.count_documents({'is_available': True})

    stats_by_length = {}
    for length in [5,6,7,8]:
        stats_by_length[length] = {
            'total': checked_collection.count_documents({'length': length}),
            'available': checked_collection.count_documents({'length': length, 'is_available': True})
        }

    return {
        'total': total,
        'available': available,
        'by_length': stats_by_length
    }

# ================= USERNAME =================

def generate_valid_username(length):
    length = max(5, int(length))

    while True:
        first_char = random.choice(string.ascii_lowercase)
        other_chars = string.ascii_lowercase + string.digits
        username = first_char + ''.join(random.choices(other_chars, k=length - 1))

        if len(username) >= 5:
            return username

def check_telegram_username(username):

    if len(username) < 5:
        return False

    try:
        response = requests.get(
            f"https://t.me/{username}",
            timeout=5,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        html = response.text.lower()

        if 'tgme_page_title' in html:
            return False

        if 'username not found' in html:
            return True

        if 'fragment' in html:
            return False

        return False

    except:
        return False

# ================= SEARCH =================

def search_usernames(chat_id, length, message_id):

    if length not in [5,6,7,8]:
        bot.send_message(chat_id, "❌ الطول غير مسموح")
        return

    found = 0
    checked = 0
    skipped_duplicate = 0
    active_searches[chat_id] = True
    start_time = time.time()

    while active_searches.get(chat_id, False):

        username = generate_valid_username(length)

        if len(username) < 5:
            continue

        if is_username_checked(username):
            skipped_duplicate += 1
            continue

        is_available = check_telegram_username(username)
        checked += 1

        mark_username_checked(username, is_available)

        if is_available:
            found += 1
            elapsed = int(time.time() - start_time)

            bot.send_message(
                chat_id,
                f"🎉 **يوزر متاح!**\n"
                f"👤 @{username}\n"
                f"📏 {len(username)} أحرف\n"
                f"⏱ بعد {elapsed//60} دقيقة و {elapsed%60} ثانية\n"
                f"🔗 https://t.me/{username}",
                parse_mode='Markdown'
            )

        if checked % 20 == 0:
            elapsed = int(time.time() - start_time)
            stats = get_stats()

            progress_msg = (
                f"🔍 بحث عن {length} أحرف\n"
                f"⏱ {elapsed//60}:{elapsed%60:02d}\n\n"
                f"✓ مفحوص: {checked}\n"
                f"🎯 متاح: {found}\n"
                f"🔄 مكرر: {skipped_duplicate}\n\n"
                f"💾 الإجمالي: {stats['total']:,}\n"
                f"✨ المتاح: {stats['available']}"
            )

            try:
                bot.edit_message_text(progress_msg, chat_id, message_id)
            except:
                pass

        time.sleep(0.7)

    elapsed = int(time.time() - start_time)
    bot.edit_message_text(
        f"🛑 توقف البحث\n"
        f"⏱ المدة: {elapsed//60} دقيقة\n"
        f"✓ مفحوص: {checked}\n"
        f"🎯 متاح: {found}",
        chat_id,
        message_id
    )

# ================= COMMANDS =================

@bot.message_handler(commands=['search5','search6','search7','search8'])
def search(message):

    chat_id = message.chat.id

    if active_searches.get(chat_id, False):
        bot.reply_to(message, "⚠️ في بحث نشط! استخدم /stop أولاً")
        return

    length = int(message.text.replace('/search',''))

    msg = bot.reply_to(message, f"⏳ بدء البحث عن {length} أحرف...")

    thread = Thread(target=search_usernames, args=(chat_id, length, msg.message_id))
    thread.daemon = True
    thread.start()

@bot.message_handler(commands=['stop'])
def stop(message):
    chat_id = message.chat.id
    active_searches[chat_id] = False
    bot.reply_to(message, "🛑 تم إيقاف البحث")

@bot.message_handler(commands=['stats'])
def stats(message):
    stats_data = get_stats()
    
    msg = (
        f"📊 **الإحصائيات العامة**\n\n"
        f"💾 إجمالي المفحوص: {stats_data['total']:,}\n"
        f"✨ المتاح: {stats_data['available']}\n\n"
        f"📏 **حسب الطول:**\n"
        f"• 5 أحرف: {stats_data['by_length'][5]['total']} مفحوص | {stats_data['by_length'][5]['available']} متاح\n"
        f"• 6 أحرف: {stats_data['by_length'][6]['total']} مفحوص | {stats_data['by_length'][6]['available']} متاح\n"
        f"• 7 أحرف: {stats_data['by_length'][7]['total']} مفحوص | {stats_data['by_length'][7]['available']} متاح\n"
        f"• 8 أحرف: {stats_data['by_length'][8]['total']} مفحوص | {stats_data['by_length'][8]['available']} متاح"
    )
    
    bot.reply_to(message, msg, parse_mode='Markdown')

# ================= ADMIN COMMANDS =================

@bot.message_handler(commands=['cleandb'])
def clean_database(message):
    if not is_admin(message.from_user.username):
        bot.reply_to(message, "❌ هذا الأمر للمشرف فقط")
        return
    
    result = checked_collection.delete_many({})
    checked_collection.create_index('username', unique=True)
    checked_collection.create_index('checked_at')
    
    bot.reply_to(
        message, 
        f"✅ **تم مسح قاعدة البيانات**\n"
        f"📊 عدد اليوزرات المحذوفة: {result.deleted_count}",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['cleanold'])
def clean_old_data(message):
    if not is_admin(message.from_user.username):
        bot.reply_to(message, "❌ هذا الأمر للمشرف فقط")
        return
    
    week_ago = datetime.now() - timedelta(days=7)
    result = checked_collection.delete_many({
        'checked_at': {'$lt': week_ago},
        'is_available': False
    })
    
    bot.reply_to(
        message,
        f"✅ **تم تنظيف البيانات القديمة**\n"
        f"📊 عدد اليوزرات المحذوفة: {result.deleted_count}",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['dbsize'])
def db_size(message):
    if not is_admin(message.from_user.username):
        bot.reply_to(message, "❌ هذا الأمر للمشرف فقط")
        return
    
    total = checked_collection.count_documents({})
    available = checked_collection.count_documents({'is_available': True})
    
    stats = db.command("dbstats")
    size_mb = stats['dataSize'] / (1024 * 1024)
    storage_mb = stats['storageSize'] / (1024 * 1024)
    
    bot.reply_to(
        message,
        f"📊 **حجم قاعدة البيانات**\n\n"
        f"📁 إجمالي اليوزرات: {total:,}\n"
        f"✨ المتاحة: {available}\n\n"
        f"📦 حجم البيانات: {size_mb:.2f} MB\n"
        f"💾 المساحة الفعلية: {storage_mb:.2f} MB\n"
        f"⚡️ 512 MB المتبقية: {max(0, 512 - storage_mb):.2f} MB",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['start'])
def start(message):
    stats_data = get_stats()
    username = message.from_user.username
    
    welcome_msg = (
        f"🎯 **بوت البحث عن يوزرات تليجرام**\n\n"
        f"📊 **إحصائيات:**\n"
        f"📁 إجمالي: {stats_data['total']:,}\n"
        f"✨ متاح: {stats_data['available']}\n\n"
        f"**الأوامر:**\n"
        f"/search5 - بحث عن 5 أحرف\n"
        f"/search6 - بحث عن 6 أحرف\n"
        f"/search7 - بحث عن 7 أحرف\n"
        f"/search8 - بحث عن 8 أحرف\n"
        f"/stats - الإحصائيات\n"
        f"/stop - إيقاف البحث"
    )
    
    if is_admin(username):
        welcome_msg += (
            f"\n\n👑 **أوامر المشرف:**\n"
            f"/cleandb - مسح الكل\n"
            f"/cleanold - تنظيف القديم\n"
            f"/dbsize - حجم قاعدة البيانات"
        )
    
    bot.reply_to(message, welcome_msg, parse_mode='Markdown')

@bot.message_handler(func=lambda m: True)
def handle_all(message):
    bot.reply_to(
        message,
        "👀 استخدم:\n"
        "/search5\n/search6\n/search7\n/search8\n/stats\n/stop"
    )

# ================= AUTO CLEAN =================

def auto_clean_task():
    while True:
        try:
            month_ago = datetime.now() - timedelta(days=30)
            result = checked_collection.delete_many({
                'checked_at': {'$lt': month_ago},
                'is_available': False
            })
            if result.deleted_count > 0:
                print(f"🧹 تنظيف تلقائي: حذف {result.deleted_count} يوزر")
            time.sleep(7 * 24 * 60 * 60)
        except:
            time.sleep(3600)

# ================= RUN =================

if __name__ == '__main__':
    print("✅ البوت شغال")
    print(f"👑 المشرف: @{ADMIN_USERNAME}")
    print("🔒 يبحث فقط عن 5 أحرف فأكثر")

    clean_thread = Thread(target=auto_clean_task)
    clean_thread.daemon = True
    clean_thread.start()

    bot.infinity_polling()
