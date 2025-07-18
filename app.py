from flask import Flask, render_template, request, jsonify
import psycopg2
import os
from dotenv import load_dotenv
from datetime import datetime
from flask_cors import CORS

load_dotenv()
app = Flask(__name__)

# ✅ 只保留这一行（限制允许跨域的前端地址）
CORS(app, origins=["https://candycrushvitebolt-production.up.railway.app"])

DATABASE_URL = os.getenv("DATABASE_URL")

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

@app.route("/user", methods=["POST"])
def get_user():
    user_id = request.form.get("user_id")
    
    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400
    
    conn = get_conn

@app.route("/api/profile", methods=["GET"])
def api_profile():
    user_id = request.args.get("user_id")

    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400

    user_id = str(user_id)  # 强制字符串类型
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT user_id, username, phone, points, token, plays 
        FROM users WHERE user_id::text = %s
    """, (user_id,))
    user = cur.fetchone()

    if not user:
        # 自动注册匿名用户（不建议生产用）
        username = f"user_{user_id[-4:]}"
        cur.execute("""
            INSERT INTO users (user_id, username, points, token, plays) 
            VALUES (%s, %s, 0, 10, 0)
        """, (user_id, username))
        conn.commit()
        user = (str(user_id), username, None, 0, 10, 0)

    cur.close()
    conn.close()

    return jsonify({
        "user_id": user[0],
        "username": user[1],
        "phone": user[2],
        "points": user[3],
        "token": user[4],
        "plays": user[5]
    })

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

@app.route("/api/game_history")
def game_history():
    user_id = request.args.get("user_id")
    page = int(request.args.get("page", 1))
    per_page = 10
    offset = (page - 1) * per_page

    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400

    conn = get_conn()
    cur = conn.cursor()

    # 强制 string 对比
    cur.execute("SELECT COUNT(*) FROM game_history WHERE user_id::text = %s", (str(user_id),))
    total = cur.fetchone()[0]

    cur.execute("""
        SELECT created_at, game_type, level, user_score, points_change, token_change, result, remark
        FROM game_history 
        WHERE user_id::text = %s
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
    """, (str(user_id), per_page, offset))
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify({
        "total": total,
        "per_page": per_page,
        "records": [
            {
                "created_at": r[0].strftime('%Y-%m-%d %H:%M') if r[0] else "",
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
    
@app.route("/api/report_game", methods=["POST"])
def report_game():
    try:
        data = request.get_json()
        user_id = str(data.get("user_id"))
        user_score = int(data.get("user_score", 0))
        points_change = int(data.get("points_change", 0))
        token_change = int(data.get("token_change", 0))
        game_type = data.get("game_type", "candy_crush")
        level = int(data.get("level", 1))
        result = data.get("result", "win")
        remark = data.get("remark", "")

        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        conn = get_conn()
        cur = conn.cursor()

        # ✅ 查询当前 token
        cur.execute("SELECT token FROM users WHERE user_id::text = %s", (user_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "User not found"}), 404

        current_token = row[0]
        if current_token < abs(token_change):  # 如果 token 不足（比如要减1，但剩下 0）
            return jsonify({"error": "Not enough tokens"}), 400

        # ✅ 写入 game_history
        cur.execute("""
            INSERT INTO game_history (user_id, game_type, level, user_score, points_change, token_change, result, remark)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, game_type, level, user_score, points_change, token_change, result, remark))

        # ✅ 更新用户数据
        cur.execute("""
            UPDATE users 
            SET points = points + %s, token = token + %s, plays = plays + 1, last_play = NOW()
            WHERE user_id::text = %s
        """, (points_change, token_change, user_id))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/game_history")
def get_game_history():
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
