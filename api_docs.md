## 注册/登录
POST /api/register
{
  "user_id": 123456,
  "username": "张三",
  "phone": "1234567890",
  "invited_by": 654321
}

## 用户信息
GET /api/profile?user_id=123456

## 上报游戏成绩
POST /api/report_game
{
  "user_id": 123456,
  "user_score": 2000,
  "points_change": 30,
  "token_change": -1,
  "game_type": "消除",
  "level": 8,
  "result": "胜利",
  "remark": "过关奖励"
}

## 查询排行榜
GET /api/rank

## 查询历史
GET /api/game_history?user_id=123456&page=1

## 邀请奖励
POST /api/invite_reward
{
  "inviter_id": 654321,
  "invitee_id": 123456
}
