import os
import logging
from dotenv import load_dotenv
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)

load_dotenv()
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def start(update, context):
    update.message.reply_text("🎲 欢迎来到H5游戏！请输入 /bind 开始绑定手机号。")

def bind(update, context):
    if update.message.chat.type != "private":
        bot_name = context.bot.username
        update.message.reply_text(
            f"请点击这里私聊我绑定手机号：https://t.me/{bot_name}"
        )
        return
    contact_button = KeyboardButton("📱 发送手机号", request_contact=True)
    markup = ReplyKeyboardMarkup([[contact_button]], resize_keyboard=True, one_time_keyboard=True)
    update.message.reply_text("请点击下方按钮发送手机号完成绑定", reply_markup=markup)

# contact handler
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
        if data.get("status") != "ok":
            raise Exception(data.get("msg"))
    except Exception as e:
        logging.error(f"绑定手机号API失败: {e}")
        await update.message.reply_text("❌ 绑定失败，请稍后再试。")
        return

    game_url = f"https://dice-production-1f4e.up.railway.app/dice?uid={user_id}"
    await update.message.reply_text(
        f"✅ 手机号绑定成功！\n点击开始游戏：{game_url}",
        disable_web_page_preview=True
    )

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("bind", bind))
    application.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    application.run_polling()  # <-- 不要 await，也不用 async main

if __name__ == "__main__":
    main()
