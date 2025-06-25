from flask import Flask, request, jsonify

app = Flask(__name__)

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
