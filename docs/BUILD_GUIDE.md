# 운동인증방 Discord Bot 구축 가이드

## 개요

카카오톡 운동인증방을 Discord + Google Sheets로 자동화한 시스템입니다.

## 시스템 구조

```
Discord 채널 ──▶ Discord Bot ──▶ Google Sheets
     │              │                 │
     │         (Python)               │
     │              │                 ▼
     ◀────── 슬래시 커맨드 ◀──── 인증/벌금 데이터
```

---

## 구축 순서

### 1. Discord 설정
1. [Discord Developer Portal](https://discord.com/developers/applications) 접속
2. New Application → Bot 생성
3. Bot Token 복사 (비공개 유지!)
4. MESSAGE CONTENT INTENT 활성화
5. OAuth2 → URL Generator로 봇 초대 링크 생성
6. 서버에 봇 초대

### 2. Google Cloud 설정
1. [Google Cloud Console](https://console.cloud.google.com) 접속
2. 새 프로젝트 생성
3. Google Sheets API + Google Drive API 활성화
4. 서비스 계정 생성 → JSON 키 다운로드 (`credentials.json`)

### 3. Google Sheets 설정
1. 새 스프레드시트 생성
2. 서비스 계정 이메일에 편집 권한 공유
3. 스프레드시트 ID 복사 (URL에서)

### 4. 코드 배포 (Railway)
1. GitHub에 코드 push
2. [Railway](https://railway.app) 가입 → GitHub 연동
3. 환경변수 5개 설정:
   - `DISCORD_BOT_TOKEN`
   - `DISCORD_GUILD_ID`
   - `DISCORD_CHANNEL_ID`
   - `GOOGLE_SHEETS_ID`
   - `GOOGLE_CREDENTIALS_JSON`

---

## 파일 구조

| 파일 | 설명 |
|------|------|
| `bot.py` | Discord Bot 메인 (슬래시 커맨드) |
| `sheets.py` | Google Sheets 연동 |
| `config.py` | 설정값 관리 |
| `requirements.txt` | Python 패키지 |
| `.env` | 환경변수 (Git 제외) |
| `credentials.json` | Google 인증 (Git 제외) |

---

## 운영

- **Railway**: 24시간 자동 운영 (월 $5 무료 크레딧)
- **주간 집계**: 매주 일요일 00:00 KST 자동 실행
- **모니터링**: Railway Dashboard → Deploy Logs

---

## 문의

GitHub Issues 또는 Discord 채널에서 문의
