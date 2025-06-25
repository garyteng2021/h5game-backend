# H5 Game Flask Backend

> Railway + PostgreSQL + Flask RESTful API + 管理后台

## 项目介绍

本项目是 H5 游戏（如消除类/Candy Crush）积分和用户管理的全栈后端。  
集成：
- 用户注册/登录/邀请
- Token 与积分经济体系
- 游戏结果上报、积分历史、排行榜
- APScheduler 定时任务（每日发放Token）
- Web管理后台页面（dashboard.html, game_history.html）
- 全部数据存储于 PostgreSQL

## 目录结构

main_flask.py # Flask 主程序 (API/调度)
requirements.txt # 依赖清单
schema.sql # 数据库结构
.env.example # 环境变量示例
api_docs.md # API接口文档
dashboard.html # 管理后台页面
game_history.html # 游戏历史页面
README.md # 项目说明

## 启动方式

1. `pip install -r requirements.txt`
2. 配置 `.env`
3. `python main.py`

管理页面：  
- dashboard.html 适配 Flask/Jinja2 渲染  
- game_history.html 可独立展示历史记录

API文档见 `api_docs.md`
