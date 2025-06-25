import os
import psycopg2
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

def get_conn():
    return psycopg2.connect(DATABASE_URL)

@app.route("/api/user/bind", methods=["POST"])
def bind():
    data = request.json
    user_id = data.get("user_id")
    username = data.get("username")
    phone = data.get("phone")

    if not user_id or not phone:
        return jsonify({"status": "fail", "msg": "参数缺失"}), 400

    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (user_id, username, phone)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE
                SET username = EXCLUDED.username, phone = EXCLUDED.phone
            """, (user_id, username, phone))
            conn.commit()
        return jsonify({"status": "ok", "msg": "绑定成功"})
    except Exception as e:
        # 日志建议写入日志系统
        print("DB Error:", e)
        return jsonify({"status": "fail", "msg": "数据库写入失败"}), 500

if __name__ == "__main__":
    app.run()
