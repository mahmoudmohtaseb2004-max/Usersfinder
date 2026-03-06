import os
import logging
import random
import uuid
import time
from typing import Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram import InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, InlineQueryHandler, ContextTypes

# ------------------ الإعدادات ------------------
TOKEN = os.environ.get("BOT_TOKEN")

if not TOKEN:
    TOKEN = "ضع_التوكن_هنا"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تخزين الألعاب
games: Dict[str, dict] = {}

# ------------------ نظام منع السبام (Rate Limit) ------------------
# قاموس لتخزين آخر وقت ضغط لكل مستخدم
last_click: Dict[int, float] = {}
SPAM_TIME = 2  # ثانيتين بين كل ضغطة

def check_spam(user_id: int) -> bool:
    """تفحص إذا المستخدم يسبام أو لا."""
    current_time = time.time()
    if user_id in last_click:
        time_diff = current_time - last_click[user_id]
        if time_diff < SPAM_TIME:
            return True  # هذا سبام
    
    # تحديث آخر وقت ضغط
    last_click[user_id] = current_time
    return False  # مش سبام

# ------------------ أمر /start ------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رسالة الترحيب."""
    user = update.effective_user
    
    keyboard = [
        [InlineKeyboardButton("🎲 العب روليت الآن", switch_inline_query="")],
        [InlineKeyboardButton("📝 قواعد اللعبة", callback_data="rules")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        f"🎯 *أهلاً بك {user.first_name}!*\n\n"
        f"✨ *بوت الروليت*\n"
        f"➖➖➖➖➖➖➖\n\n"
        f"🔹 *لبدء اللعب:*\n"
        f"اكتب @{context.bot.username} في أي محادثة\n\n"
        f"🔹 *القواعد:*\n"
        f"اضغط على زر القواعد للمزيد"
    )
    
    await update.message.reply_text(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# ------------------ معالج Inline Mode ------------------
async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هذا اللي يشتغل لما تكتب @userbot + كلمة."""
    query = update.inline_query.query.lower()
    user = update.inline_query.from_user
    
    logger.info(f"استعلام: {query} من {user.first_name}")
    
    results = []
    
    # إذا كتب "rules" أو "قواعد"
    if "rules" in query or "قواعد" in query:
        results.append(
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title="📝 قواعد اللعبة",
                description="اضغط لقراءة قواعد الروليت",
                input_message_content=InputTextMessageContent(
                    "📝 *قواعد لعبة الروليت:*\n\n"
                    "1️⃣ أي شخص يقدر يشارك بالضغط على انضمام\n"
                    "2️⃣ المشرف فقط يقدر يسحب الفائز\n"
                    "3️⃣ بعد السحب، تنتهي اللعبة\n"
                    "4️⃣ ممنوع الضغط المتكرر (السبام)\n\n"
                    "🎯 استمتع باللعبة!",
                    parse_mode="Markdown"
                )
            )
        )
    
    # إذا كتب "game" أو "لعبة" أو ما كتب شيء
    elif "game" in query or "لعبة" in query or query == "":
        games_list = [
            {
                "id": f"simple_{uuid.uuid4().hex[:8]}",
                "title": "🎲 روليت عادي",
                "description": "سحب فائز عشوائي",
                "emoji": "🎲"
            },
            {
                "id": f"premium_{uuid.uuid4().hex[:8]}",
                "title": "🎯 روليت أحكام",
                "description": "مع عجلة حظ متحركة",
                "emoji": "🎯"
            }
        ]
        
        for game_data in games_list:
            game_id = game_data['id']
            
            # حفظ اللعبة
            games[game_id] = {
                "type": game_data['title'],
                "players": [],
                "players_names": [],
                "creator": user.id,
                "creator_name": user.first_name,
                "created_at": time.time()
            }
            
            # أزرار اللعبة
            keyboard = [
                [InlineKeyboardButton("✅ انضمام", callback_data=f"join_{game_id}")],
                [InlineKeyboardButton("👥 المشاركين", callback_data=f"list_{game_id}"),
                 InlineKeyboardButton("🏆 سحب", callback_data=f"draw_{game_id}")]
            ]
            
            results.append(
                InlineQueryResultArticle(
                    id=game_id,
                    title=game_data['title'],
                    description=f"{game_data['description']} | 👥 0 مشارك",
                    input_message_content=InputTextMessageContent(
                        f"{game_data['emoji']} *{game_data['title']}*\n"
                        f"➖➖➖➖➖➖➖\n"
                        f"👤 المنشئ: {user.first_name}\n"
                        f"👥 المشاركون: 0\n"
                        f"➖➖➖➖➖➖➖\n"
                        f"🕹️ اضغط انضمام للمشاركة",
                        parse_mode="Markdown"
                    ),
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            )
    
    # أي كلمة ثانية
    else:
        results.append(
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title=f"🔍 لا توجد نتيجة لـ '{query}'",
                description="اضغط لرؤية الألعاب المتاحة",
                input_message_content=InputTextMessageContent(
                    f"❌ لا توجد لعبة بهذا الاسم: {query}\n\n"
                    f"جرب: game, rules, لعبة, قواعد",
                    parse_mode="Markdown"
                )
            )
        )
    
    await update.inline_query.answer(results, cache_time=0)

# ------------------ معالج الأزرار (بعد التعديل) ------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الضغط على الأزرار."""
    query = update.callback_query
    user = query.from_user  # 🔴 مهم: نعرف المستخدم
    await query.answer()
    
    # 🔴 نظام منع السبام
    if check_spam(user.id):
        await query.answer("⏳ تمهل! انتظر ثانيتين بين كل ضغطة", show_alert=True)
        return
    
    data = query.data
    
    # قواعد اللعبة
    if data == "rules":
        rules_text = (
            "📝 *قواعد لعبة الروليت:*\n\n"
            "1️⃣ *المشاركة:* أي عضو يقدر يشارك\n"
            "2️⃣ *السحب:* المشرف فقط يسحب الفائز\n"
            "3️⃣ *الانتهاء:* اللعبة تنتهي بعد السحب\n"
            "4️⃣ *العد:* كل مشارك له فرصة متساوية\n"
            "5️⃣ *السبام:* ممنوع الضغط المتكرر\n\n"
            "🎯 *استمتع وحظ سعيد!*"
        )
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_start")]]
        await query.edit_message_text(
            rules_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if data == "back_to_start":
        keyboard = [
            [InlineKeyboardButton("🎲 العب روليت", switch_inline_query="")],
            [InlineKeyboardButton("📝 القواعد", callback_data="rules")]
        ]
        await query.edit_message_text(
            "🎯 *مرحباً بك في بوت الروليت!*",
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
            # 🔴 هنا كنا نحتاج user والمعرفين
            if user.id in game["players"]:
                await query.answer("✅ أنت مشترك بالفعل!", show_alert=True)
                return
            
            # 🔴 منع السبام أيضاً للإضافة المتكررة
            if len(game["players"]) > 50:  # حد أقصى 50 مشارك
                await query.answer("❌ اللعبة اكتملت!", show_alert=True)
                return
            
            game["players"].append(user.id)
            game["players_names"].append(user.first_name)
            
            # تحديث النص
            new_text = (
                f"{query.message.text.split('👥')[0]}"
                f"👥 المشاركون: {len(game['players'])}\n"
                f"➖➖➖➖➖➖➖\n"
                f"🕹️ اضغط انضمام للمشاركة"
            )
            
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
                await query.answer("❌ لا يوجد مشاركين!", show_alert=True)
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
    logger.error(f"خطأ: {context.error}")

# ------------------ مهم: تنظيف الألعاب القديمة ------------------
async def clean_old_games():
    """تحذف الألعاب اللي مر عليها أكثر من ساعة."""
    while True:
        current_time = time.time()
        to_delete = []
        for game_id, game in games.items():
            if current_time - game.get("created_at", 0) > 3600:  # ساعة
                to_delete.append(game_id)
        
        for game_id in to_delete:
            del games[game_id]
        
        if to_delete:
            logger.info(f"تم حذف {len(to_delete)} لعبة قديمة")
        
        await asyncio.sleep(300)  # تشيك كل 5 دقائق

# ------------------ التشغيل ------------------
def main():
    import asyncio
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(InlineQueryHandler(inline_query))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_error_handler(error_handler)
    
    # تشغيل مهمة تنظيف الألعاب القديمة
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(clean_old_games())
    
    print("🤖 البوت شغال...")
    print("• التعديلات:")
    print("  ✅ تم إضافة user = query.from_user")
    print("  ✅ تم إضافة نظام منع السبام")
    print("  ✅ تم إضافة حد أقصى 50 مشارك")
    print("  ✅ تم إضافة تنظيف الألعاب القديمة")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
