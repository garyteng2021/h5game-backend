import os
import psycopg2
from flask import Flask, request, jsonify
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from threading import Thread

# Telegram Bot
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes
)

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

app = Flask(__name__)
CORS(app)

def get_conn():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    with get_conn() as conn, conn.cursor() as c:
        with open('schema.sql', encoding='utf-8') as f:
            c.execute(f.read())
        conn.commit()

# ---- Flask RESTful API ----

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    user_id = data.get('user_id')
    username = data.get('username')
    phone = data.get('phone')
    invited_by = data.get('invited_by')
    if not user_id:
        return jsonify({"status": "error", "msg": "缺少user_id"}), 400
    with get_conn() as conn, conn.cursor() as c:
        c.execute("SELECT 1 FROM users WHERE user_id=%s", (user_id,))
        if c.fetchone():
            return jsonify({"status": "already_exists"})
        c.execute("""
            INSERT INTO users (user_id, username, phone, token, points, plays, created_at, invited_by)
            VALUES (%s, %s, %s, 5, 0, 0, NOW(), %s)
        """, (user_id, username, phone, invited_by))
        if invited_by:
            c.execute("UPDATE users SET invite_count = invite_count + 1 WHERE user_id = %s", (invited_by,))
        conn.commit()
    return jsonify({"status": "ok"})

@app.route('/api/profile')
def api_profile():
    user_id = request.args.get('user_id')
    with get_conn() as conn, conn.cursor() as c:
        c.execute("SELECT user_id, username, points, token, plays FROM users WHERE user_id=%s", (user_id,))
        row = c.fetchone()
    if row:
        return jsonify({
            "user_id": row[0], "username": row[1], "points": row[2], "token": row[3], "plays": row[4]
        })
    else:
        return jsonify({"error": "not_found"}), 404

@app.route('/api/invite_reward', methods=['POST'])
def invite_reward():
    data = request.json
    inviter_id = data.get('inviter_id')
    invitee_id = data.get('invitee_id')
    if not inviter_id or not invitee_id:
        return jsonify({"status": "error", "msg": "参数错误"}), 400
    with get_conn() as conn, conn.cursor() as c:
        c.execute("SELECT reward_given FROM invite_rewards WHERE inviter=%s AND invitee=%s", (inviter_id, invitee_id))
        row = c.fetchone()
        if row and row[0]:
            return jsonify({"status": "already_given"})
        c.execute("UPDATE users SET token=LEAST(token+2, 10) WHERE user_id=%s", (inviter_id,))
        c.execute("""
            INSERT INTO invite_rewards (inviter, invitee, reward_given)
            VALUES (%s, %s, TRUE)
            ON CONFLICT (inviter, invitee) DO UPDATE SET reward_given=TRUE
        """, (inviter_id, invitee_id))
        conn.commit()
    return jsonify({"status": "ok"})

@app.route('/api/report_game', methods=['POST'])
def report_game():
    data = request.json
    user_id = data.get('user_id')
    user_score = data.get('user_score', 0)
    points_change = data.get('points_change', 0)
    token_change = data.get('token_change', 0)
    game_type = data.get('game_type', None)
    level = data.get('level', None)
    result = data.get('result', '')
    remark = data.get('remark', '')
    if not user_id:
        return jsonify({"status": "error", "msg": "缺少user_id"}), 400
    with get_conn() as conn, conn.cursor() as c:
        c.execute("SELECT token, points, plays FROM users WHERE user_id=%s", (user_id,))
        row = c.fetchone()
        if not row:
            return jsonify({"status": "error", "msg": "用户不存在"}), 404
        token, points, plays = row
        new_token = min(10, max(0, token + token_change))
        if new_token < 0 or (token + token_change) < 0:
            return jsonify({"status": "error", "msg": "token不足"}), 400
        c.execute(
            """
            INSERT INTO game_history 
            (user_id, created_at, user_score, points_change, token_change, game_type, level, result, remark)
            VALUES (%s, NOW(), %s, %s, %s, %s, %s, %s, %s)
            """,
            (user_id, user_score, points_change, token_change, game_type, level, result, remark)
        )
        c.execute(
            """
            UPDATE users
            SET 
                points = points + %s,
                token = %s,
                plays = plays + 1,
                last_play = NOW()
            WHERE user_id = %s
            """,
            (points_change, new_token, user_id)
        )
        c.execute("SELECT points, token, plays FROM users WHERE user_id=%s", (user_id,))
        up = c.fetchone()
        conn.commit()
    return jsonify({
        "status": "ok",
        "user": {
            "user_id": user_id,
            "points": up[0],
            "token": up[1],
            "plays": up[2]
        }
    })

@app.route('/api/rank')
def api_rank():
    with get_conn() as conn, conn.cursor() as c:
        c.execute("SELECT user_id, username, points FROM users ORDER BY points DESC LIMIT 10")
        rows = c.fetchall()
    data = [
        {"user_id": r[0], "username": r[1] or "匿名", "points": r[2]}
        for r in rows
    ]
    return jsonify({"rank": data})

@app.route('/api/game_history')
def api_game_history():
    user_id = request.args.get('user_id')
    page = int(request.args.get('page', 1))
    per_page = 20
    offset = (page - 1) * per_page
    with get_conn() as conn, conn.cursor() as c:
        if user_id:
            c.execute("SELECT COUNT(*) FROM game_history WHERE user_id=%s", (user_id,))
            total = c.fetchone()[0]
            c.execute("""
                SELECT user_id, created_at, user_score, points_change, token_change, game_type, level, result, remark
                FROM game_history WHERE user_id=%s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """, (user_id, per_page, offset))
        else:
            c.execute("SELECT COUNT(*) FROM game_history")
            total = c.fetchone()[0]
            c.execute("""
                SELECT user_id, created_at, user_score, points_change, token_change, game_type, level, result, remark
                FROM game_history
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """, (per_page, offset))
        records = c.fetchall()
    result = [
        {
            "user_id": r[0],
            "created_at": r[1].strftime('%Y-%m-%d %H:%M:%S'),
            "user_score": r[2],
            "points_change": r[3],
            "token_change": r[4],
            "game_type": r[5],
            "level": r[6],
            "result": r[7],
            "remark": r[8],
        } for r in records
    ]
    return jsonify({
        "records": result,
        "page": page,
        "per_page": per_page,
        "total": total
    })

# 每日自动+3token，上限10
def daily_token_job():
    with get_conn() as conn, conn.cursor() as c:
        c.execute("UPDATE users SET token = LEAST(token + 3, 10)")
        conn.commit()

# --- Telegram Bot核心逻辑 ---
from telegram.ext import ApplicationBuilder

async def tg_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # 注册到数据库
    with get_conn() as conn, conn.cursor() as c:
        c.execute("""
            INSERT INTO users (user_id, username, created_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (user_id) DO NOTHING
        """, (user.id, user.username))
        conn.commit()
    # 发送H5游戏链接
    h5_url = f"https://yourgame.com/?user_id={user.id}"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 进入H5游戏", url=h5_url)]
    ])
    await update.message.reply_text(
        "欢迎！请点击下方按钮开始H5游戏～",
        reply_markup=keyboard
    )

async def tg_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    with get_conn() as conn, conn.cursor() as c:
        c.execute("SELECT points, token FROM users WHERE user_id=%s", (user.id,))
        row = c.fetchone()
    msg = "积分：%d\nToken：%d" % (row[0], row[1]) if row else "未找到你的账号。"
    await update.message.reply_text(msg)

def start_bot():
    app_bot = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", tg_start))
    app_bot.add_handler(CommandHandler("profile", tg_profile))
    app_bot.run_polling()

if __name__ == '__main__':
    init_db()
    scheduler = BackgroundScheduler()
    scheduler.add_job(daily_token_job, "cron", hour=0, minute=0)
    scheduler.start()
    Thread(target=start_bot, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
