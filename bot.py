import os
import random
import psycopg2
import asyncio
import logging
import nest_asyncio
from dotenv import load_dotenv
from telegram import (
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup，
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

nest_asyncio.apply()
load_dotenv()
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

# --- DB Helper ---
def get_conn():
    return psycopg2.connect(DATABASE_URL)


# --- /start 注册用户 ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username or ""
    args = context.args
    invited_by = int(args[0]) if args else None

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM users WHERE user_id=%s", (user_id,))
    exists = cur.fetchone()

    if not exists:
        cur.execute(
            "INSERT INTO users(user_id, username, invited_by, token) VALUES (%s, %s, %s, %s)",
            (user_id, username, invited_by, 5),
        )

        if invited_by:
            cur.execute("SELECT 1 FROM invite_rewards WHERE inviter=%s AND invitee=%s", (invited_by, user_id))
            if not cur.fetchone():
                cur.execute("UPDATE users SET token = token + 2, invite_count = invite_count + 1 WHERE user_id=%s", (invited_by,))
                cur.execute("INSERT INTO invite_rewards (inviter, invitee, reward_given) VALUES (%s, %s, %s)", (invited_by, user_id, True))

        conn.commit()

    cur.close()
    conn.close()

    text = f"👋 欢迎 {user.first_name}！\n"
    text += "你已成功进入积分系统。\n\n"
    text += "发送 /bind 可绑定手机号。\n"
    text += "发送 /rank 可查看排行榜。\n"
    text += "发送 /start [邀请ID] 可邀请好友注册。"

    await update.message.reply_text(text)


# --- /bind 获取手机号 ---
async def bind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    button = KeyboardButton("点击发送手机号 📱", request_contact=True)
    markup = ReplyKeyboardMarkup([[button]], resize_keyboard=True)
    await update.message.reply_text("请点击下面按钮发送你的手机号：", reply_markup=markup)


# --- 接收手机号 ---
async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    user_id = update.effective_user.id
    phone = contact.phone_number

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET phone=%s WHERE user_id=%s", (phone, user_id))
    conn.commit()
    cur.close()
    conn.close()

    await update.message.reply_text(f"✅ 已绑定手机号：{phone}")


# --- /rank 查看排行榜 ---
async def show_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT username, points FROM users ORDER BY points DESC LIMIT 10")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    text = "<b>🏆 当前排行榜前10名：</b>\n"
    for i, row in enumerate(rows, 1):
        text += f"{i}. {row[0] or '无名'} - {row[1]} 分\n"

    await update.message.reply_text(text, parse_mode="HTML")

async def game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 点击开始游戏", callback_game={"game_short_name": "test_game"})]
    ])
    await update.message.reply_game(game_short_name="test_game", reply_markup=keyboard)

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query.game_short_name == "test_game":
        await update.callback_query.answer(url="https://h5game-backend-production.up.railway.app/game/game.html")
    else:
        await update.callback_query.answer(text="找不到这个游戏", show_alert=True)
        
# --- Entry Point ---
async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("game", game))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("bind", bind))
    application.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    application.add_handler(CommandHandler("rank", show_rank))
    application.add_handler(MessageHandler(filters.UpdateType.CALLBACK_QUERY, callback_query_handler))

    await application.run_polling()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
