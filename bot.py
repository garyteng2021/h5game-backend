import os
import asyncio
import asyncpg
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import ParseMode

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or "你的BotToken"
DATABASE_URL = os.getenv("DATABASE_URL") or "你的Postgres链接"

bot = Bot(token=TELEGRAM_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(bot)

# 全局数据库连接池
db_pool = None

async def get_db():
    global db_pool
    if db_pool is None:
        db_pool = await asyncpg.create_pool(DATABASE_URL)
    return db_pool

# 数据库初始化函数（首次部署可调用一次）
async def init_db():
    pool = await get_db()
    async with pool.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            invited_by BIGINT,
            tokens INT DEFAULT 0,
            points INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS invites (
            user_id BIGINT,
            invited_id BIGINT,
            invite_time TIMESTAMP DEFAULT NOW()
        );
        """)

# 用户注册/查找
async def register_user(user_id, username, invited_by=None):
    pool = await get_db()
    async with pool.acquire() as conn:
        exists = await conn.fetchval("SELECT 1 FROM users WHERE user_id=$1", user_id)
        if not exists:
            await conn.execute(
                "INSERT INTO users(user_id, username, invited_by, token) VALUES ($1, $2, $3, $4)",
                user_id, username, invited_by, 5  # 注册奖励5Token
            )
            if invited_by:
                # 只奖励一次
                already_rewarded = await conn.fetchval(
                    "SELECT 1 FROM invite_rewards WHERE inviter=$1 AND invitee=$2",
                    invited_by, user_id
                )
                if not already_rewarded:
                    await conn.execute(
                        "UPDATE users SET token = token + 2, invite_count = invite_count + 1 WHERE user_id=$1",
                        invited_by
                    )
                    await conn.execute(
                        "INSERT INTO invite_rewards(inviter, invitee, reward_given) VALUES ($1, $2, $3)",
                        invited_by, user_id, True
                    )
            return True
        return False

# 查询积分/Token
async def get_user_info(user_id):
    pool = await get_db()
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            "SELECT token, points, invited_by FROM users WHERE user_id=$1", user_id
        )

# 查询排行榜
async def get_leaderboard(limit=10):
    pool = await get_db()
    async with pool.acquire() as conn:
        return await conn.fetch(
            "SELECT username, points FROM users ORDER BY points DESC LIMIT $1", limit
        )

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    # 检查是否带邀请参数
    args = message.get_args()
    invited_by = int(args) if args.isdigit() else None
    user = message.from_user
    is_new = await register_user(user.id, user.username, invited_by)
    text = f"👋 欢迎{'新用户' if is_new else '回来'}，<b>{user.first_name}</b>！\n\n"
    text += "🎮 <b>Bot积分体系已开启！</b>\n\n"
    if is_new and invited_by:
        text += "你通过邀请链接注册，已获得注册奖励，邀请人也已获得奖励。\n"
    text += "\n输入 /me 查询积分，/invite 获取你的专属邀请链接。\n"
    await message.answer(text)

@dp.message_handler(commands=['me'])
async def cmd_me(message: types.Message):
    user_id = message.from_user.id
    info = await get_user_info(user_id)
    if info:
        text = f"👤 <b>你的数据</b>\n"
        text += f"Token：{info['tokens']}\n"
        text += f"积分：{info['points']}\n"
        text += f"邀请人：{'无' if not info['invited_by'] else info['invited_by']}\n"
        await message.answer(text)
    else:
        await message.answer("未查到你的数据，请先 /start 注册。")

@dp.message_handler(commands=['invite'])
async def cmd_invite(message: types.Message):
    user_id = message.from_user.id
    link = f"https://t.me/{(await bot.me).username}?start={user_id}"
    await message.answer(
        f"🔗 <b>你的邀请链接：</b>\n{link}\n\n"
        "每邀请1人注册，你与对方都能获得奖励Token！"
    )

@dp.message_handler(commands=['leaderboard'])
async def cmd_leaderboard(message: types.Message):
    board = await get_leaderboard()
    text = "<b>🏆 排行榜（前10名）</b>\n"
    for i, row in enumerate(board, 1):
        text += f"{i}. {row['username'] or '无名'} - {row['points']} 分\n"
    await message.answer(text)

# 管理员推送示例（只允许某管理员ID推送）
ADMIN_ID = 123456789

@dp.message_handler(commands=['push'])
async def cmd_push(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    # /push 你的内容
    content = message.get_args()
    if not content:
        await message.reply("请在命令后加内容：/push 消息内容")
        return
    # 群发给所有用户
    pool = await get_db()
    async with pool.acquire() as conn:
        users = await conn.fetch("SELECT user_id FROM users")
        for user in users:
            try:
                await bot.send_message(user['user_id'], f"📢 <b>公告：</b>{content}")
                await asyncio.sleep(0.05)  # 防封号
            except Exception:
                continue
        await message.reply("已推送。")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_db())
    executor.start_polling(dp, skip_updates=True)
