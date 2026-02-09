"""
운동인증방 봇 설정 파일
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Discord 설정
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))

# Google Sheets 설정
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID")
CREDENTIALS_FILE = "credentials.json"

# 운동 인증 규칙
WEEKLY_REQUIRED_COUNT = 3  # 주 3회 필수
PENALTY_PER_MISS = 5000    # 회당 벌금 5000원
RESPONSIBILITY_FEE = 1000  # 책임비용 1000원

# 벌금 할인 규칙
EARLY_DISCOUNT_RATE = 0.5   # 주 시작 전 납부시 50% 할인
TUESDAY_DISCOUNT = 2000     # 화요일 이전 납부시 2000원 할인

# 시간 설정 (KST)
TIMEZONE = "Asia/Seoul"
WEEK_START_DAY = 6  # 일요일 = 6 (Monday = 0)
INVALID_HOURS = (0, 4)  # 00:00 ~ 04:00 운동 불인정

# 운동 종류별 규칙
EXERCISE_RULES = {
    "런닝": {"min_minutes": 15, "min_speed_kmh": 7.5},
    "사이클": {"min_minutes": 30, "min_speed_kmh": 12},
    "홈트": {"min_minutes": 30, "requires_video": True},
    "헬스": {"min_minutes": 30, "requires_timestamp": True},
    "필라테스": {"min_minutes": 30, "requires_timestamp": True},
    "링피트": {"min_kcal": 100},
    "유산소": {"min_kcal": 200},
    "골프": {"max_per_week": 1},
}
