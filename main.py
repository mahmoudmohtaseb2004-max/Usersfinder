import os
import logging
import random
import uuid
from typing import Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram import InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, InlineQueryHandler, ContextTypes

# ------------------ الإعدادات ------------------
TOKEN = os.environ.get("BOT_TOKEN")

if not TOKEN:
    TOKEN = "ضع_التوكن_هنا_مباشرة_للتجربة"  # للتجربة فقط، بعدين شيلها

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تخزين الألعاب
games: Dict[str, dict] = {}

# ------------------ أمر /start (للخاص والمجموعات) ------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رسالة الترحيب."""
    user = update.effective_user
    
    # أزرار البداية
    keyboard = [
        [InlineKeyboardButton("🎲 العب روليت الآن", switch_inline_query="")],
        [InlineKeyboardButton("📢 مشاركة البوت", switch_inline_query="شارك البوت مع أصدقائك")],
        [InlineKeyboardButton("📝 شرح الاستخدام", callback_data="show_help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # رسالة الترحيب
    welcome_text = (
        f"🎯 *أهلاً بك {user.first_name}!*\n\n"
        f"✨ *بوت الروليت الذكي*\n"
        f"➖➖➖➖➖➖➖➖➖\n\n"
        f"🔹 *طريقة الاستخدام:*\n"
        f"𝟭️⃣ اكتب @{context.bot.username} في أي محادثة\n"
        f"𝟮️⃣ اختر نوع اللعبة من القائمة\n"
        f"𝟯️⃣ شارك اللعبة مع أصدقائك\n\n"
        f"🔹 *المميزات:*\n"
        f"✅ يعمل بدون إضافة للمجموعات\n"
        f"✅ أزرار تفاعلية سهلة\n"
        f"✅ اختيار فائز عشوائي\n\n"
        f"👇 اضغط على الزر لبدء اللعب"
    )
    
    await update.message.reply_text(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# ------------------ معالج Inline Mode ------------------
async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هذا اللي يخلي البوت يشتغل لما تكتب @username."""
    query = update.inline_query.query
    user = update.inline_query.from_user
    
    logger.info(f"استعلام Inline من {user.first_name}: {query}")
    
    # الألعاب المتاحة
    games_list = [
        {
            "id": "simple",
            "title": "🎲 روليت عادي",
            "description": "سحب فائز عشوائي",
            "emoji": "🎲"
        },
        {
            "id": "premium",
            "title": "🎯 روليت أحكام",
            "description": "مع عجلة حظ وأزرار تفاعلية",
            "emoji": "🎯"
        },
        {
            "id": "teams",
            "title": "👥 روليت فرق",
            "description": "قسّم المشاركين لفرق",
            "emoji": "👥"
        }
    ]
    
    results = []
    
    # تصفية حسب البحث
    filtered_games = games_list
    if query:
        filtered_games = [g for g in games_list if query.lower() in g['title'].lower()]
    
    # إنشاء النتائج
    for game in filtered_games:
        game_id = f"{game['id']}_{uuid.uuid4().hex[:8]}"
        
        # حفظ اللعبة
        games[game_id] = {
            "type": game['id'],
            "players": [],
            "players_names": [],
            "creator": user.id,
            "creator_name": user.first_name
        }
        
        # أزرار اللعبة
        keyboard = [
            [InlineKeyboardButton("✅ انضمام", callback_data=f"join_{game_id}")],
            [InlineKeyboardButton("👥 المشاركين", callback_data=f"list_{game_id}"),
             InlineKeyboardButton("🏆 سحب", callback_data=f"draw_{game_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # نص اللعبة
        game_text = (
            f"{game['emoji']} *{game['title']}*\n"
            f"➖➖➖➖➖➖➖\n"
            f"👤 المنشئ: {user.first_name}\n"
            f"👥 المشاركون: 0\n"
            f"➖➖➖➖➖➖➖\n"
            f"🕹️ اضغط انضمام للمشاركة"
        )
        
        results.append(
            InlineQueryResultArticle(
                id=game_id,
                title=game['title'],
                description=f"{game['description']} | 👥 0 مشارك",
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
    
    # شرح الاستخدام
    if data == "show_help":
        help_text = (
            "📝 *شرح مفصل للاستخدام:*\n\n"
            "1️⃣ *لبدء اللعبة:*\n"
            "   اكتب @username في أي محادثة\n\n"
            "2️⃣ *للمشاركة:*\n"
            "   اضغط على زر 'انضمام'\n\n"
            "3️⃣ *للسحب:*\n"
            "   أي مشرف يقدر يضغط 'سحب'\n\n"
            "💡 *ملاحظة:*\n"
            "   اللعبة تنتهي بعد السحب"
        )
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_start")]]
        await query.edit_message_text(
            help_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # رجوع للبداية
    if data == "back_to_start":
        keyboard = [
            [InlineKeyboardButton("🎲 العب روليت الآن", switch_inline_query="")],
            [InlineKeyboardButton("📝 شرح الاستخدام", callback_data="show_help")]
        ]
        await query.edit_message_text(
            "🎯 *مرحباً بك في بوت الروليت!*\n\nاختر ما تريد:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # معالجة أزرار اللعبة
    if "_" in data:
        action, game_id = data.split("_", 1)
        
        if game_id not in games:
            await query.edit_message_text("❌ اللعبة انتهت صلاحيتها")
            return
        
        game = games[game_id]
        
        # انضمام
        if action == "join":
            if user.id in game["players"]:
                await query.answer("أنت مشترك بالفعل!", show_alert=True)
                return
            
            game["players"].append(user.id)
            game["players_names"].append(user.first_name)
            
            # تحديث النص
            new_text = query.message.text.split("👥")[0] + f"👥 المشاركون: {len(game['players'])}\n➖➖➖➖➖➖➖\n🕹️ اضغط انضمام للمشاركة"
            
            await query.edit_message_text(
                new_text,
                parse_mode="Markdown",
                reply_markup=query.message.reply_markup
            )
            await query.answer(f"✅ تم انضمامك! العدد: {len(game['players'])}")
        
        # عرض المشاركين
        elif action == "list":
            if not game["players"]:
                players_text = "لا يوجد مشاركين"
            else:
                players_text = "\n".join([f"• {name}" for name in game["players_names"]])
            
            text = f"👥 *المشاركين:*\n{players_text}\n\n📊 العدد: {len(game['players'])}"
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data=f"back_{game_id}")]]
            
            await query.edit_message_text(
                text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        # سحب الفائز
        elif action == "draw":
            if len(game["players"]) == 0:
                await query.answer("لا يوجد مشاركين!", show_alert=True)
                return
            
            winner_index = random.randint(0, len(game["players"]) - 1)
            winner_id = game["players"][winner_index]
            winner_name = game["players_names"][winner_index]
            
            result = (
                f"🎉 *تم السحب!*\n\n"
                f"🏆 *الفائز:* [{winner_name}](tg://user?id={winner_id})\n"
                f"👥 عدد المشاركين: {len(game['players'])}"
            )
            
            # حذف اللعبة
            del games[game_id]
            
            await query.edit_message_text(
                result,
                parse_mode="Markdown"
            )
        
        # رجوع للعبة
        elif action == "back":
            game = games[game_id]
            keyboard = [
                [InlineKeyboardButton("✅ انضمام", callback_data=f"join_{game_id}")],
                [InlineKeyboardButton("👥 المشاركين", callback_data=f"list_{game_id}"),
                 InlineKeyboardButton("🏆 سحب", callback_data=f"draw_{game_id}")]
            ]
            
            await query.edit_message_text(
                f"🎯 *لعبة روليت*\n\n👥 المشاركون: {len(game['players'])}",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

# ------------------ معالج الأخطاء ------------------
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تسجيل الأخطاء."""
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
    
    # تشغيل البوت
    print("🤖 البوت شغال... جرب تكتب @username في أي محادثة")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
