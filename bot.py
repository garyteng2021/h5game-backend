# bot.py

import os
from dotenv import load_dotenv
import asyncio
from psycopg2.pool import SimpleConnectionPool
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# 1. 环境变量
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# 2. 数据库连接池
db_pool = SimpleConnectionPool(minconn=1, maxconn=5, dsn=DATABASE_URL)

def get_conn():
    return db_pool.getconn()

def put_conn(conn):
    db_pool.putconn(conn)

# 3. /start 指令
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = get_conn()
    try:
        with conn.cursor() as c:
            c.execute(
                "INSERT INTO users (user_id, username, created_at) VALUES (%s, %s, NOW()) ON CONFLICT (user_id) DO NOTHING",
                (user.id, user.username)
            )
        conn.commit()
    except Exception:
        await update.message.reply_text("数据库错误，请稍后再试。")
        return
    finally:
        put_conn(conn)
    await update.message.reply_text(f"欢迎，{user.first_name}！")

# 4. 启动 Bot
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()

if __name__ == "__main__":
    main()
