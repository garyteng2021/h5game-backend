# file: bot_main.py

import os
import requests
import logging
import nest_asyncio
from dotenv import load_dotenv
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

nest_asyncio.apply()
load_dotenv()
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_URL = os.getenv("API_URL")  # 如 "https://your-backend-api.com"

# --- Command: /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎲 欢迎来到H5游戏！请输入 /bind 开始绑定手机号。")

# --- Command: /bind ---
async def bind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact_button = KeyboardButton("📱 发送手机号", request_contact=True)
    markup = ReplyKeyboardMarkup([[contact_button]], resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("请点击下方按钮发送手机号完成绑定", reply_markup=markup)

# --- Contact Handler ---
async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    user_id = update.message.from_user.id
    phone = contact.phone_number
    username = update.message.from_user.username

    # 请求后端API进行绑定
    payload = {
        "user_id": user_id,
        "username": username,
        "phone": phone,
    }
    try:
        resp = requests.post(f"{API_URL}/api/user/bind", json=payload, timeout=5)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logging.error(f"绑定手机号API失败: {e}")
        await update.message.reply_text("❌ 绑定失败，请稍后再试。")
        return

    # 返回游戏链接
    game_url = f"https://dice-production-1f4e.up.railway.app/dice?uid={user_id}"
    await update.message.reply_text(
        f"✅ 手机号绑定成功！\n点击开始游戏：{game_url}",
        disable_web_page_preview=True
    )

# --- Command: /rank ---
async def show_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        resp = requests.get(f"{API_URL}/api/rank/top10", timeout=5)
        resp.raise_for_status()
        rows = resp.json().get("data", [])
    except Exception as e:
        logging.error(f"排行榜API失败: {e}")
        await update.message.reply_text("❌ 无法获取排行榜，请稍后再试。")
        return

    if not rows:
        await update.message.reply_text("暂无排行榜数据。")
        return

    msg = "🏆 当前积分排行榜：\n"
    for i, row in enumerate(rows, 1):
        name = row.get("username") or "匿名"
        pts = row.get("points", 0)
        msg += f"{i}. {name} - {pts} 分\n"
    await update.message.reply_text(msg)

# --- Entry Point ---
async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("bind", bind))
    application.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    application.add_handler(CommandHandler("rank", show_rank))
    await application.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.get_event_loop().run_until_complete(main())
