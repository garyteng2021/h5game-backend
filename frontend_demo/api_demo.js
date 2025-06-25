// 示例: H5前端调用API
const user_id = new URLSearchParams(window.location.search).get('user_id');
fetch('https://your-backend.com/api/profile?user_id='+user_id).then(r=>r.json()).then(console.log);
fetch('https://your-backend.com/api/report_game', {
  method: 'POST',
  headers: {'Content-Type':'application/json'},
  body: JSON.stringify({
    user_id: user_id,
    user_score: 1234,
    points_change: 12,
    token_change: -1,
    game_type: "消除",
    result: "胜利"
  })
});
