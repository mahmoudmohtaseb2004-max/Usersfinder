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
    
    # إحصائيات حسب الطول
    total_5 = checked_collection.count_documents({'length': 5})
    total_6 = checked_collection.count_documents({'length': 6})
    total_7 = checked_collection.count_documents({'length': 7})
    total_8 = checked_collection.count_documents({'length': 8})
    
    available_5 = checked_collection.count_documents({'length': 5, 'is_available': True})
    available_6 = checked_collection.count_documents({'length': 6, 'is_available': True})
    available_7 = checked_collection.count_documents({'length': 7, 'is_available': True})
    available_8 = checked_collection.count_documents({'length': 8, 'is_available': True})
    
    return {
        'total': total,
        'available': available,
        'by_length': {
            5: {'total': total_5, 'available': available_5},
            6: {'total': total_6, 'available': available_6},
            7: {'total': total_7, 'available': available_7},
            8: {'total': total_8, 'available': available_8}
        }
    }

def check_telegram_username(username):
    """التحقق من توفر اليوزر"""
    try:
        url = f"https://t.me/{username}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=5)
        
        # تحليل الصفحة
        html = response.text.lower()
        
        # إذا كان اليوزر غير موجود
        if "tgme_page" not in html or "if you have telegram, you can contact" in html:
            return True  # متاح للتسجيل
            
        return False  # غير متاح
        
    except:
        return False

def generate_valid_username(length):
    """
    توليد يوزر صحيح - فقط للأطوال 5 فأكثر
    """
    # التأكد أن الطول 5 على الأقل
    if length < 5:
        length = 5
    
    # الحرف الأول: أحرف صغيرة فقط
    first_char = random.choice(string.ascii_lowercase)
    
    # باقي الأحرف: أحرف صغيرة + أرقام + underscore
    other_chars = string.ascii_lowercase + string.digits + '_'
    rest = ''.join(random.choices(other_chars, k=length-1))
    
    username = first_char + rest
    
    # التأكد من عدم الانتهاء بـ underscore
    if username.endswith('_'):
        username = username[:-1] + random.choice(string.ascii_lowercase)
    
    return username

def search_usernames(chat_id, length, message_id):
    """دالة البحث - فقط للأطوال 5 فأكثر"""
    
    # التأكد أن طول البحث 5 على الأقل
    if length < 5:
        length = 5
        bot.send_message(chat_id, "✅ تم تعديل البحث لـ 5 أحرف (الحد الأدنى)")
    
    found = 0
    checked = 0
    skipped_short = 0
    skipped_duplicate = 0
    active_searches[chat_id] = True
    start_time = time.time()
    
    while active_searches.get(chat_id, False):
        # توليد يوزر جديد (مضمون 5+ أحرف)
        username = generate_valid_username(length)
        
        # هل مفحوص من قبل؟
        if is_username_checked(username):
            skipped_duplicate += 1
            continue
        
        # فحص اليوزر
        is_available = check_telegram_username(username)
        checked += 1
        
        # تسجيل في MongoDB
        mark_username_checked(username, is_available)
        
        # إرسال إشعار إذا كان متاحاً
        if is_available:
            found += 1
            elapsed = int(time.time() - start_time)
            
            # رسالة اليوزر المتاح
            bot.send_message(
                chat_id,
                f"🎉 **يوزر متاح للتسجيل المجاني!**\n"
                f"👤 @{username}\n"
                f"📏 {len(username)} أحرف\n"
                f"⏱ بعد {elapsed//60} دقيقة و {elapsed%60} ثانية\n"
                f"🔗 https://t.me/{username}\n\n"
                f"⚠️ سارع بتسجيله قبل أي شخص!",
                parse_mode='Markdown'
            )
        
        # تحديث الحالة كل 20 محاولة
        if checked % 20 == 0:
            elapsed = int(time.time() - start_time)
            stats = get_stats()
            
            progress_msg = (
                f"🔍 **بحث عن يوزرات {length} أحرف**\n"
                f"⏱ الوقت المنقضي: {elapsed//60}:{elapsed%60:02d}\n\n"
                f"📊 **هذه الجلسة:**\n"
                f"   ✓ تم الفحص: {checked}\n"
                f"   🎯 تم العثور: {found}\n"
                f"   🔄 مكرر: {skipped_duplicate}\n\n"
                f"💾 **إحصائيات عامة:**\n"
                f"   📁 إجمالي المفحوص: {stats['total']:,}\n"
                f"   ✨ إجمالي المتاح: {stats['available']}\n\n"
                f"⚡️ السرعة: {checked//(elapsed+1)}/ثانية"
            )
            
            try:
                bot.edit_message_text(progress_msg, chat_id, message_id, parse_mode='Markdown')
            except:
                pass
        
        time.sleep(0.4)
    
    # عند التوقف
    elapsed = int(time.time() - start_time)
    stats = get_stats()
    
    final_msg = (
        f"🛑 **توقف البحث**\n"
        f"⏱ استمر لمدة: {elapsed//60} دقيقة\n\n"
        f"📊 **إحصائيات الجلسة:**\n"
        f"   ✓ تم الفحص: {checked}\n"
        f"   🎯 تم العثور: {found}\n"
        f"   🔄 مكرر: {skipped_duplicate}\n\n"
        f"💾 **إجمالي في قاعدة البيانات:**\n"
        f"   📁 كل اليوزرات: {stats['total']:,}\n"
        f"   ✨ المتاحة: {stats['available']}\n\n"
        f"✅ جميع اليوزرات المفحوصة 5 أحرف فأكثر"
    )
    
    try:
        bot.edit_message_text(final_msg, chat_id, message_id, parse_mode='Markdown')
    except:
        pass

@bot.message_handler(commands=['start'])
def start(message):
    stats = get_stats()
    
    welcome_msg = (
        f"🎯 **بوت البحث عن يوزرات تليجرام**\n\n"
        f"📊 **إحصائيات عامة:**\n"
        f"📁 إجمالي المفحوص: {stats['total']:,}\n"
        f"✨ إجمالي المتاح: {stats['available']}\n\n"
        f"📏 **حسب الطول:**\n"
        f"• 5 أحرف: {stats['by_length'][5]['total']} مفحوص | {stats['by_length'][5]['available']} متاح\n"
        f"• 6 أحرف: {stats['by_length'][6]['total']} مفحوص | {stats['by_length'][6]['available']} متاح\n"
        f"• 7 أحرف: {stats['by_length'][7]['total']} مفحوص | {stats['by_length'][7]['available']} متاح\n"
        f"• 8 أحرف: {stats['by_length'][8]['total']} مفحوص | {stats['by_length'][8]['available']} متاح\n\n"
        f"⚠️ **ملاحظة مهمة:**\n"
        f"• البوت يبحث فقط عن يوزرات **5 أحرف فأكثر** (المجانية)\n"
        f"• اليوزرات الأقل من 5 أحرف للبيع على Fragment ولا يتم البحث عنها\n\n"
        f"**الأوامر المتاحة:**\n"
        f"/search5 - 🔍 بحث عن يوزر خماسي (5 أحرف)\n"
        f"/search6 - 🔍 بحث عن يوزر سداسي (6 أحرف)\n"
        f"/search7 - 🔍 بحث عن يوزر سباعي (7 أحرف)\n"
        f"/search8 - 🔍 بحث عن يوزر ثماني (8 أحرف)\n"
        f"/stats - 📊 عرض الإحصائيات\n"
        f"/stop - 🛑 إيقاف البحث"
    )
    
    bot.reply_to(message, welcome_msg, parse_mode='Markdown')

@bot.message_handler(commands=['stats'])
def stats(message):
    stats_data = get_stats()
    
    stats_msg = (
        f"📊 **إحصائيات قاعدة البيانات**\n\n"
        f"💾 **الإجمالي:**\n"
        f"• كل اليوزرات: {stats_data['total']:,}\n"
        f"• المتاحة: {stats_data['available']}\n\n"
        f"📏 **حسب الطول:**\n"
        f"• 5 أحرف: {stats_data['by_length'][5]['total']} مفحوص | {stats_data['by_length'][5]['available']} متاح\n"
        f"• 6 أحرف: {stats_data['by_length'][6]['total']} مفحوص | {stats_data['by_length'][6]['available']} متاح\n"
        f"• 7 أحرف: {stats_data['by_length'][7]['total']} مفحوص | {stats_data['by_length'][7]['available']} متاح\n"
        f"• 8 أحرف: {stats_data['by_length'][8]['total']} مفحوص | {stats_data['by_length'][8]['available']} متاح\n\n"
        f"✅ **معلومة:** جميع اليوزرات المخزنة 5 أحرف فأكثر\n"
        f"⚡️ آخر تحديث: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    
    bot.reply_to(message, stats_msg, parse_mode='Markdown')

@bot.message_handler(commands=['search5', 'search6', 'search7', 'search8'])
def search(message):
    chat_id = message.chat.id
    
    if active_searches.get(chat_id, False):
        bot.reply_to(message, "⚠️ في بحث نشط! استخدم /stop أولاً")
        return
    
    # تحديد طول البحث
    if message.text == '/search5':
        length = 5
        msg_text = "خماسي (5 أحرف)"
    elif message.text == '/search6':
        length = 6
        msg_text = "سداسي (6 أحرف)"
    elif message.text == '/search7':
        length = 7
        msg_text = "سباعي (7 أحرف)"
    else:  # search8
        length = 8
        msg_text = "ثماني (8 أحرف)"
    
    msg = bot.reply_to(
        message, 
        f"⏳ **بدء البحث عن يوزرات {msg_text}**\n"
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
        "/search5 - بحث عن يوزرات خماسية\n"
        "/search6 - بحث عن يوزرات سداسية\n"
        "/search7 - بحث عن يوزرات سباعية\n"
        "/search8 - بحث عن يوزرات ثمانية\n"
        "/stats - عرض الإحصائيات\n"
        "/stop - إيقاف البحث"
    )

if __name__ == '__main__':
    print("✅ البوت شغال مع MongoDB...")
    print("📊 يبحث فقط عن يوزرات 5 أحرف فأكثر (مجانية)")
    print("⛔ لا يبحث عن يوزرات ثنائية أو ثلاثية أو رباعية")
    bot.infinity_polling()
