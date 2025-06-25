# H5 Game Fullstack Backend

后端：Flask + APScheduler + Telegram Bot  
数据库：Postgres（推荐 Railway）  
前端管理：dashboard.html / game_history.html  
H5 游戏对接 API：见 api_docs.md 和 frontend_demo/api_demo.js

## 启动方式

1. `pip install -r requirements.txt`
2. 配置 `.env`
3. `python main.py`

管理页面：  
- dashboard.html 适配 Flask/Jinja2 渲染  
- game_history.html 可独立展示历史记录

API文档见 `api_docs.md`
