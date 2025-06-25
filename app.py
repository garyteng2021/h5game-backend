import os
import random
import psycopg2
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
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
    # 此处应有写库逻辑
    return jsonify({"status": "ok", "msg": "绑定成功"})

if __name__ == "__main__":
    app.run()
