# 운동인증방 Discord Bot

Discord 기반 운동 인증 및 벌금 관리 시스템

## 기능
- `/인증` - 운동 인증
- `/벌금조회` - 벌금 현황
- `/주간현황` - 전체 현황
- `/멤버등록` - 멤버 등록

## 환경 변수
- `DISCORD_BOT_TOKEN`
- `DISCORD_GUILD_ID`
- `DISCORD_CHANNEL_ID`
- `GOOGLE_SHEETS_ID`
- `GOOGLE_CREDENTIALS_JSON` (credentials.json 내용)

## 실행
```bash
pip install -r requirements.txt
python bot.py
```
