from flask import Flask, render_template
import os

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("dashboard.html")

if __name__ == "__main__":
    # 关键：Railway 必须监听 0.0.0.0 并读取 PORT 环境变量
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
