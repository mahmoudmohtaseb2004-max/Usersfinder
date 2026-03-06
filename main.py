import os
import logging
import random
import uuid
from typing import Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram import InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, InlineQueryHandler, ContextTypes

# ------------------ الإعدادات من Railway ------------------
TOKEN = os.environ.get("BOT_TOKEN")

# التأكد من وجود التوكن
if not TOKEN:
    raise ValueError("❌ لم يتم تعيين BOT_TOKEN في متغيرات Railway!")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تخزين الألعاب النشطة
games: Dict[str, dict] = {}

# ------------------ رسالة الترحيب ------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رسالة الترحيب والتعليمات."""
    keyboard = [
        [InlineKeyboardButton("🎲 إنشاء لعبة جديدة", switch_inline_query="")],
        [InlineKeyboardButton("📝 شرح الاستخدام", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🎯 *مرحباً بك في بوت الروليت!*\n\n"
        "✨ *طريقة الاستخدام:*\n"
        "1️⃣ اكتب @username في أي محادثة (اسم البوت تلقائياً)\n"
        "2️⃣ اختر 'إنشاء روليت جديد'\n"
        "3️⃣ شارك اللعبة مع أصدقائك\n\n"
        "⚡ البوت يعمل بدون إضافته للمجموعات!",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# ------------------ معالج Inline Mode ------------------
async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الاستعلامات المضمنة."""
    query = update.inline_query.query
    results = []
    
    # الألعاب المتاحة
    games_list = [
        {
            "id": "roulette_simple",
            "title": "🎲 روليت عادي",
            "description": "سحب فائز عشوائي من المشاركين",
            "emoji": "🎲"
        },
        {
            "id": "roulette_premium",
            "title": "🎯 روليت أحكام",
            "description": "مع عجلة حظ متحركة وأزرار تفاعلية",
            "emoji": "🎯"
        }
    ]
    
    # فلترة حسب البحث إذا كان المستخدم كتب شيء
    filtered_games = games_list
    if query:
        filtered_games = [g for g in games_list if query.lower() in g['title'].lower() or query.lower() in g['description'].lower()]
    
    # إنشاء النتائج
    for game in filtered_games:
        # إنشاء معرف فريد للعبة
        game_id = str(uuid.uuid4())
        
        # حفظ اللعبة في الذاكرة
        games[game_id] = {
            "type": game['id'],
            "players": [],
            "players_names": [],
            "created_at": None  # راح نضيف الوقت لاحقاً
        }
        
        # أزرار اللعبة
        keyboard = [
            [InlineKeyboardButton("✅ انضمام إلى السحب", callback_data=f"join_{game_id}")],
            [InlineKeyboardButton("👥 عرض المشاركين", callback_data=f"players_{game_id}")],
            [InlineKeyboardButton("🏆 سحب الفائز", callback_data=f"winner_{game_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # نص اللعبة
        game_text = (
            f"{game['emoji']} *{game['title']}*\n\n"
            f"📝 {game['description']}\n"
            f"👥 عدد المشاركين: 0\n\n"
            f"اضغط على الأزرار للمشاركة!"
        )
        
        # إضافة النتيجة
        results.append(
            InlineQueryResultArticle(
                id=game_id,
                title=game['title'],
                description=game['description'],
                input_message_content=InputTextMessageContent(
                    game_text,
                    parse_mode="Markdown"
                ),
                reply_markup=reply_markup
            )
        )
    
    # إرسال النتائج
    await update.inline_query.answer(results, cache_time=0)

# ------------------ معالج الأزرار ------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الضغط على الأزرار."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user = query.from_user
    
    # استخراج نوع الزر ومعرف اللعبة
    if "_" in data:
        action, game_id = data.split("_", 1)
    else:
        action = data
        game_id = None
    
    # معالج المساعدة
    if action == "help":
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back")]]
        await query.edit_message_text(
            "📝 *شرح استخدام البوت:*\n\n"
            "1️⃣ اكتب @username في أي محادثة\n"
            "2️⃣ اختر نوع اللعبة اللي تبيها\n"
            "3️⃣ شارك اللعبة مع الأصدقاء\n"
            "4️⃣ المشرفين يقدرون يسحبون الفائز\n\n"
            "⚡ البوت يعمل في أي مكان!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # التحقق من وجود اللعبة
    if not game_id or game_id not in games:
        await query.edit_message_text("❌ اللعبة انتهت صلاحيتها أو تم حذفها.")
        return
    
    game = games[game_id]
    
    # انضمام للعبة
    if action == "join":
        if user.id in game["players"]:
            await query.answer("✅ أنت مشترك بالفعل!", show_alert=True)
            return
        
        game["players"].append(user.id)
        game["players_names"].append(user.first_name)
        
        # تحديث النص
        new_text = query.message.text.split("\n\n")[0] + f"\n\n👥 عدد المشاركين: {len(game['players'])}\n\nاضغط على الأزرار للمشاركة!"
        
        await query.edit_message_text(
            new_text,
            parse_mode="Markdown",
            reply_markup=query.message.reply_markup
        )
        await query.answer(f"✅ تم انضمامك! العدد: {len(game['players'])}")
    
    # عرض المشاركين
    elif action == "players":
        if not game["players"]:
            players_list = "لا يوجد مشاركين بعد"
        else:
            players_list = "\n".join([f"👤 {name}" for name in game["players_names"]])
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data=f"back_{game_id}")]]
        
        await query.edit_message_text(
            f"👥 *المشاركين:*\n\n{players_list}\n\n📊 العدد: {len(game['players'])}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # سحب الفائز
    elif action == "winner":
        if len(game["players"]) < 1:
            await query.answer("❌ لا يوجد مشاركين!", show_alert=True)
            return
        
        winner_index = random.randint(0, len(game["players"]) - 1)
        winner_id = game["players"][winner_index]
        winner_name = game["players_names"][winner_index]
        
        result_text = (
            f"🎉 *تم اختيار الفائز!* 🎉\n\n"
            f"🏆 *الفائز:* [{winner_name}](tg://user?id={winner_id})\n"
            f"📊 عدد المشاركين: {len(game['players'])}"
        )
        
        # حذف اللعبة بعد السحب
        del games[game_id]
        
        await query.edit_message_text(
            result_text,
            parse_mode="Markdown"
        )
    
    # رجوع للعبة
    elif action == "back":
        if game_id not in games:
            await query.edit_message_text("❌ اللعبة انتهت")
            return
        
        game = games[game_id]
        
        keyboard = [
            [InlineKeyboardButton("✅ انضمام", callback_data=f"join_{game_id}")],
            [InlineKeyboardButton("👥 عرض المشاركين", callback_data=f"players_{game_id}")],
            [InlineKeyboardButton("🏆 سحب الفائز", callback_data=f"winner_{game_id}")]
        ]
        
        await query.edit_message_text(
            f"🎯 *لعبة روليت*\n\n👥 عدد المشاركين: {len(game['players'])}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ------------------ معالج الأخطاء ------------------
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"حدث خطأ: {context.error}")

# ------------------ التشغيل الرئيسي ------------------
def main():
    """تشغيل البوت."""
    # إنشاء التطبيق
    application = Application.builder().token(TOKEN).build()
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(InlineQueryHandler(inline_query))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_error_handler(error_handler)
    
    # بدء البوت
    print("🚀 بوت الروليت يعمل...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
