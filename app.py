from flask import Flask, render_template, request, jsonify
import psycopg2
import os
from dotenv import load_dotenv
from datetime import datetime
from flask_cors import CORS

load_dotenv()
app = Flask(__name__)
CORS(app)  # 允许所有跨域
DATABASE_URL = os.getenv("DATABASE_URL")
CORS(app, origins=["https://candycrushmatch3game-production.up.railway.app"])

def get_conn():
    return psycopg2.connect(DATABASE_URL)

@app.route("/admin")
def admin_dashboard():
    conn = get_conn()
    cur = conn.cursor()

    # 数据统计
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM users WHERE phone IS NOT NULL")
    authorized_users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM users WHERE is_blocked = 1")
    blocked_users = cur.fetchone()[0]
    cur.execute("SELECT SUM(points) FROM users")
    total_points = cur.fetchone()[0] or 0

    # 总积分排行榜
    cur.execute("SELECT username, phone, points FROM users ORDER BY points DESC LIMIT 10")
    total_rank = cur.fetchall()

    # 今日排行榜
    cur.execute("""
        SELECT u.username, u.phone, SUM(g.points_change) as score 
        FROM game_history g
        JOIN users u ON g.user_id = u.user_id
        WHERE g.created_at >= CURRENT_DATE
        GROUP BY u.username, u.phone
        ORDER BY score DESC
        LIMIT 10
    """)
    today_rank = cur.fetchall()

    # 用户信息
    cur.execute("""
        SELECT u.user_id, u.username, u.phone, u.points, u.token, u.plays,
               u.created_at, u.last_play, u.invite_count, ir.reward_given, u.is_blocked, u.invited_by
        FROM users u
        LEFT JOIN invite_rewards ir ON ir.invitee = u.user_id
        ORDER BY u.created_at DESC
    """)
    users = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("dashboard.html", stats={
        'total_users': total_users,
        'authorized_users': authorized_users,
        'blocked_users': blocked_users,
        'total_points': total_points
    }, total_rank=total_rank, today_rank=today_rank, users=users)

@app.route("/update_user", methods=["POST"])
def update_user():
    data = request.form
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE users 
        SET points=%s, token=%s, plays=%s, is_blocked=%s 
        WHERE user_id=%s
    """, (data["points"], data["token"], data["plays"], data["is_blocked"], data["user_id"]))
    conn.commit()
    cur.close()
    conn.close()
    return "ok"

@app.route("/delete_user", methods=["POST"])
def delete_user():
    user_id = request.form["user_id"]
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE user_id=%s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()
    return "ok"
    
@app.route("/game/game.html")
def game_page():
    conn = get_conn()
    cur = conn.cursor()

    # 查询排行榜数据
    cur.execute("SELECT username, phone, points FROM users ORDER BY points DESC LIMIT 10")
    total_rank = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("game.html", total_rank=total_rank)
    
@app.route("/play", methods=["POST"])
def play_game():
    user_id = request.form.get("user_id")
    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT token, points, plays FROM users WHERE user_id=%s", (user_id,))
    row = cur.fetchone()
    if not row:
        return jsonify({"error": "User not found"}), 404

    token, points, plays = row
    if token <= 0:
        return jsonify({"error": "No tokens left"}), 403

    # 模拟游戏
    import random
    score = random.randint(1, 10)
    points += score
    token -= 1
    plays += 1

    # 更新用户积分
    cur.execute("""
        UPDATE users 
        SET points=%s, token=%s, plays=%s, last_play=NOW()
        WHERE user_id=%s
    """, (points, token, plays, user_id))

    # 插入历史
    cur.execute("""
        INSERT INTO game_history (user_id, user_score, points_change, token_change, game_type, level, result, remark)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (user_id, score, score, -1, 'demo', 1, 'win' if score >= 5 else 'lose', '测试H5小游戏'))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({
        "score": score,
        "points": points,
        "token": token,
        "plays": plays,
        "result": "win" if score >= 5 else "lose"
    })

@app.route("/api/rank")
def api_rank():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT username, phone, points FROM users ORDER BY points DESC LIMIT 10")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify([
        {"username": r[0], "phone": r[1], "points": r[2]} for r in rows
    ])

@app.route("/api/game_history")
def game_history():
    user_id = request.args.get("user_id")
    page = int(request.args.get("page", 1))
    per_page = 10
    offset = (page - 1) * per_page

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM game_history WHERE user_id=%s", (user_id,))
    total = cur.fetchone()[0]

    cur.execute("""
        SELECT created_at, game_type, level, user_score, points_change, token_change, result, remark
        FROM game_history 
        WHERE user_id=%s
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
    """, (user_id, per_page, offset))
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify({
        "total": total,
        "per_page": per_page,
        "records": [
            {
                "created_at": r[0].strftime('%Y-%m-%d %H:%M'),
                "game_type": r[1],
                "level": r[2],
                "user_score": r[3],
                "points_change": r[4],
                "token_change": r[5],
                "result": r[6],
                "remark": r[7]
            }
            for r in rows
        ]
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
