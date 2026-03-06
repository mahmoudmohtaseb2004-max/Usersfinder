import os
import math
import random
import logging
import imageio
from PIL import Image, ImageDraw
from typing import Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ------------------ الإعدادات ------------------

TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

games: Dict[int, dict] = {}

# ------------------ رسم عجلة الحظ ------------------

def draw_wheel(players, angle):

    size = 700
    center = size // 2
    radius = 300

    img = Image.new("RGB", (size, size), "white")
    draw = ImageDraw.Draw(img)

    total = len(players)
    slice_angle = 360 / total

    colors = [
        "#FF6B6B",
        "#FFD93D",
        "#6BCB77",
        "#4D96FF",
        "#B983FF",
        "#FF9F1C",
    ]

    start = angle

    for i, name in enumerate(players):

        end = start + slice_angle

        draw.pieslice(
            [center - radius, center - radius, center + radius, center + radius],
            start,
            end,
            fill=colors[i % len(colors)],
            outline="black",
        )

        mid = (start + end) / 2

        x = center + math.cos(math.radians(mid)) * radius * 0.6
        y = center + math.sin(math.radians(mid)) * radius * 0.6

        draw.text((x - 20, y - 10), name[:6], fill="black")

        start = end

    # مؤشر السهم
    draw.polygon(
        [(center, 50), (center - 20, 100), (center + 20, 100)],
        fill="black",
    )

    return img


# ------------------ إنشاء حركة دوران ------------------

def generate_spin(players):

    frames = []

    angle = 0

    for i in range(35):

        angle += random.randint(10, 25)

        frame = draw_wheel(players, angle)

        frames.append(frame)

    path = "wheel.gif"

    imageio.mimsave(path, frames, duration=0.07)

    return path


# ------------------ رسالة البداية ------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        [InlineKeyboardButton("🎡 بدء لعبة عجلة الحظ", callback_data="new_game")]
    ]

    await update.message.reply_text(
        "🎡 *مرحباً بك في بوت عجلة الحظ*\n\n"
        "يمكن للمشرفين بدء لعبة وسحب فائز عشوائي.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ------------------ بدء لعبة ------------------

async def new_game(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    chat = query.message.chat
    user = query.from_user

    admins = await chat.get_administrators()
    admin_ids = [admin.user.id for admin in admins]

    if user.id not in admin_ids:
        await query.answer("⛔ فقط المشرف يمكنه بدء اللعبة", show_alert=True)
        return

    if chat.id in games:
        await query.answer("⚠️ هناك لعبة جارية بالفعل", show_alert=True)
        return

    games[chat.id] = {
        "players": {}
    }

    keyboard = [
        [InlineKeyboardButton("✅ انضمام", callback_data="join")],
        [InlineKeyboardButton("👥 عرض المشاركين", callback_data="players")],
        [InlineKeyboardButton("🎡 تدوير العجلة", callback_data="spin")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel")],
    ]

    await query.edit_message_text(
        f"🎡 *لعبة عجلة الحظ*\n\n"
        f"👤 بدأها: {user.first_name}\n"
        f"👥 عدد المشاركين: 0\n\n"
        f"اضغط انضمام للمشاركة.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ------------------ الانضمام ------------------

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user = query.from_user
    chat = query.message.chat

    game = games.get(chat.id)

    if not game:
        return

    if user.id in game["players"]:
        await query.answer("أنت مشارك بالفعل", show_alert=True)
        return

    game["players"][user.id] = user.first_name

    keyboard = query.message.reply_markup

    await query.edit_message_text(
        f"🎡 *لعبة عجلة الحظ*\n\n"
        f"👥 المشاركون: {len(game['players'])}",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


# ------------------ عرض المشاركين ------------------

async def players(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    chat = query.message.chat
    game = games.get(chat.id)

    if not game:
        return

    if not game["players"]:
        text = "لا يوجد مشاركين بعد"
    else:
        text = "\n".join(
            [f"• {name}" for name in game["players"].values()]
        )

    await query.message.reply_text(
        f"👥 المشاركون:\n\n{text}"
    )


# ------------------ تدوير العجلة ------------------

async def spin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    chat = query.message.chat
    user = query.from_user

    admins = await chat.get_administrators()
    admin_ids = [a.user.id for a in admins]

    if user.id not in admin_ids:
        await query.answer("⛔ فقط المشرف يمكنه تدوير العجلة", show_alert=True)
        return

    game = games.get(chat.id)

    if not game or not game["players"]:
        await query.answer("لا يوجد مشاركين", show_alert=True)
        return

    players = list(game["players"].values())

    gif = generate_spin(players)

    winner_id = random.choice(list(game["players"].keys()))
    winner_name = game["players"][winner_id]

    await context.bot.send_animation(
        chat_id=chat.id,
        animation=open(gif, "rb"),
        caption=f"🎡 تدور العجلة...\n\n🏆 الفائز هو: {winner_name}",
    )

    del games[chat.id]


# ------------------ إلغاء اللعبة ------------------

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    chat = query.message.chat

    if chat.id in games:
        del games[chat.id]

    keyboard = [
        [InlineKeyboardButton("🎡 بدء لعبة جديدة", callback_data="new_game")]
    ]

    await query.edit_message_text(
        "تم إلغاء اللعبة.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ------------------ معالج الأزرار ------------------

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    data = update.callback_query.data

    if data == "new_game":
        await new_game(update, context)

    elif data == "join":
        await join(update, context)

    elif data == "players":
        await players(update, context)

    elif data == "spin":
        await spin(update, context)

    elif data == "cancel":
        await cancel(update, context)


# ------------------ التشغيل ------------------

def main():

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))

    print("🎡 Wheel Bot Running...")

    app.run_polling()


if __name__ == "__main__":
    main()
