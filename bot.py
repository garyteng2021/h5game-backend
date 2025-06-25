import os, nest_asyncio, asyncio
import psycopg2
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

app = Flask(__name__)
CORS(app)

def get_conn():
    return psycopg2.connect(DATABASE_URL)
def init_db():
    with get_conn() as conn, conn.cursor() as c:
        with open('schema.sql', encoding='utf-8') as f:
            c.execute(f.read())
        conn.commit()

# Telegram Bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    with get_conn() as conn, conn.cursor() as c:
        c.execute("INSERT INTO users (user_id, username, created_at) VALUES (%s, %s, NOW()) ON CONFLICT DO NOTHING", (user.id, user.username))
        conn.commit()
    await update.message.reply_text(f"欢迎，{user.first_name}！")

def run_bot():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.run_polling()

if __name__ == '__main__':
    nest_asyncio.apply()
    loop = asyncio.get_event_loop()
    loop.create_task(asyncio.to_thread(run_bot))
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)))
