-- 用户表
CREATE TABLE IF NOT EXISTS users (
    user_id      BIGINT PRIMARY KEY,
    username     TEXT,
    phone        TEXT,
    token        INTEGER DEFAULT 5,
    points       INTEGER DEFAULT 0,
    plays        INTEGER DEFAULT 0,
    created_at   TIMESTAMP DEFAULT NOW(),
    last_play    TIMESTAMP,
    invited_by   BIGINT,
    invite_count INTEGER DEFAULT 0,
    is_blocked   INTEGER DEFAULT 0
);

-- 游戏历史表
CREATE TABLE IF NOT EXISTS game_history (
    id            SERIAL PRIMARY KEY,
    user_id       BIGINT NOT NULL,
    created_at    TIMESTAMP DEFAULT NOW(),
    user_score    INTEGER,
    points_change INTEGER,
    token_change  INTEGER,
    game_type     TEXT,
    level         INTEGER,
    result        TEXT,
    remark        TEXT
);

-- 邀请奖励表
CREATE TABLE IF NOT EXISTS invite_rewards (
    id            SERIAL PRIMARY KEY,
    inviter       BIGINT NOT NULL,
    invitee       BIGINT NOT NULL,
    reward_given  BOOLEAN DEFAULT FALSE,
    created_at    TIMESTAMP DEFAULT NOW(),
    UNIQUE (inviter, invitee)
);
