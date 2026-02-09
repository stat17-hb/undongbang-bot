"""
Google Sheets 연동 모듈
운동 인증 기록 저장 및 벌금 계산
"""
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import pytz
import os
import json

from config import (
    GOOGLE_SHEETS_ID, 
    CREDENTIALS_FILE, 
    TIMEZONE,
    WEEKLY_REQUIRED_COUNT,
    PENALTY_PER_MISS,
    WEEK_START_DAY
)

# Google Sheets 스코프
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]


class SheetsManager:
    """Google Sheets 관리 클래스"""
    
    def __init__(self):
        self.client = None
        self.spreadsheet = None
        self.tz = pytz.timezone(TIMEZONE)
        self._connect()
    
    def _connect(self):
        """Google Sheets 연결"""
        try:
            # 환경변수에서 credentials 읽기 (Render 배포용)
            creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
            if creds_json:
                creds_dict = json.loads(creds_json)
                creds = Credentials.from_service_account_info(
                    creds_dict, 
                    scopes=SCOPES
                )
            else:
                # 로컬 파일에서 읽기
                creds = Credentials.from_service_account_file(
                    CREDENTIALS_FILE, 
                    scopes=SCOPES
                )
            self.client = gspread.authorize(creds)
            self.spreadsheet = self.client.open_by_key(GOOGLE_SHEETS_ID)
            print("✅ Google Sheets 연결 성공")
        except Exception as e:
            print(f"❌ Google Sheets 연결 실패: {e}")
            raise
    
    def _get_or_create_sheet(self, title: str, headers: List[str]) -> gspread.Worksheet:
        """시트 가져오기 또는 생성"""
        try:
            sheet = self.spreadsheet.worksheet(title)
        except gspread.WorksheetNotFound:
            sheet = self.spreadsheet.add_worksheet(title=title, rows=1000, cols=20)
            sheet.append_row(headers)
            print(f"📝 '{title}' 시트 생성됨")
        return sheet
    
    def get_current_week_info(self) -> tuple[str, datetime, datetime]:
        """현재 주차 정보 반환 (주차명, 시작일, 종료일)"""
        now = datetime.now(self.tz)
        # 일요일 기준으로 주 시작
        days_since_sunday = (now.weekday() + 1) % 7
        week_start = now - timedelta(days=days_since_sunday)
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        
        week_name = week_start.strftime("%Y-W%W")
        return week_name, week_start, week_end
    
    def add_verification(
        self, 
        user_id: str, 
        user_name: str, 
        count: int, 
        image_url: Optional[str] = None,
        penalty_paid: int = 0,
        note: str = ""
    ) -> Dict[str, Any]:
        """운동 인증 기록 추가"""
        sheet = self._get_or_create_sheet("인증기록", [
            "날짜시간", "주차", "사용자ID", "사용자명", 
            "회차", "이미지URL", "벌금납부", "비고"
        ])
        
        now = datetime.now(self.tz)
        week_name, _, _ = self.get_current_week_info()
        
        # 시간 검증 (00:00 ~ 04:00 운동 불인정)
        if 0 <= now.hour < 4:
            return {
                "success": False,
                "message": "❌ 밤 12시 ~ 새벽 4시 사이 운동은 인정되지 않습니다."
            }
        
        row = [
            now.strftime("%Y-%m-%d %H:%M:%S"),
            week_name,
            user_id,  # 문자열로 저장
            user_name,
            count,
            image_url or "",
            penalty_paid,
            note
        ]
        sheet.append_row(row, value_input_option='USER_ENTERED')
        
        return {
            "success": True,
            "message": f"✅ {user_name}님 {count}회차 운동 인증 완료!",
            "week": week_name,
            "count": count
        }
    
    def get_user_weekly_count(self, user_id: str) -> int:
        """현재 주 사용자 인증 횟수 조회"""
        sheet = self._get_or_create_sheet("인증기록", [
            "날짜시간", "주차", "사용자ID", "사용자명", 
            "회차", "이미지URL", "벌금납부", "비고"
        ])
        
        week_name, _, _ = self.get_current_week_info()
        records = sheet.get_all_records()
        
        # 타입 변환하여 비교 (숫자/문자열 모두 대응)
        user_records = [
            r for r in records 
            if str(r["사용자ID"]) == str(user_id) and r["주차"] == week_name
        ]
        
        if not user_records:
            return 0
        
        return max(r["회차"] for r in user_records)
    
    def get_weekly_status(self) -> List[Dict[str, Any]]:
        """현재 주 전체 멤버 현황"""
        members_sheet = self._get_or_create_sheet("멤버", [
            "사용자ID", "사용자명", "누적벌금", "가입일"
        ])
        records_sheet = self._get_or_create_sheet("인증기록", [
            "날짜시간", "주차", "사용자ID", "사용자명", 
            "회차", "이미지URL", "벌금납부", "비고"
        ])
        
        week_name, _, _ = self.get_current_week_info()
        members = members_sheet.get_all_records()
        records = records_sheet.get_all_records()
        
        # 중복 제거: 사용자ID로 유니크하게
        seen_user_ids = set()
        unique_members = []
        for member in members:
            uid = str(member["사용자ID"])
            if uid not in seen_user_ids:
                seen_user_ids.add(uid)
                unique_members.append(member)
        
        status_list = []
        for member in unique_members:
            user_id = str(member["사용자ID"])
            user_name = member["사용자명"]
            
            # 타입 변환하여 비교
            user_records = [
                r for r in records 
                if str(r["사용자ID"]) == user_id and r["주차"] == week_name
            ]
            
            count = max((r["회차"] for r in user_records), default=0)
            remaining = max(0, WEEKLY_REQUIRED_COUNT - count)
            
            status_list.append({
                "user_id": user_id,
                "user_name": user_name,
                "count": count,
                "remaining": remaining,
                "completed": count >= WEEKLY_REQUIRED_COUNT
            })
        
        return status_list
    
    def register_member(self, user_id: str, user_name: str) -> Dict[str, Any]:
        """멤버 등록"""
        sheet = self._get_or_create_sheet("멤버", [
            "사용자ID", "사용자명", "누적벌금", "가입일"
        ])
        
        # 중복 확인 (타입 변환하여 비교)
        records = sheet.get_all_records()
        if any(str(r["사용자ID"]) == str(user_id) for r in records):
            return {"success": False, "message": "이미 등록된 멤버입니다."}
        
        now = datetime.now(self.tz)
        sheet.append_row([user_id, user_name, 0, now.strftime("%Y-%m-%d")], value_input_option='USER_ENTERED')
        
        return {"success": True, "message": f"✅ {user_name}님 멤버 등록 완료!"}
    
    def get_user_penalty(self, user_id: str) -> Dict[str, Any]:
        """사용자 벌금 현황 조회"""
        members_sheet = self._get_or_create_sheet("멤버", [
            "사용자ID", "사용자명", "누적벌금", "가입일"
        ])
        
        members = members_sheet.get_all_records()
        # 타입 변환하여 비교
        member = next((m for m in members if str(m["사용자ID"]) == str(user_id)), None)
        
        if not member:
            return {"success": False, "message": "등록되지 않은 멤버입니다."}
        
        week_count = self.get_user_weekly_count(user_id)
        remaining = max(0, WEEKLY_REQUIRED_COUNT - week_count)
        
        return {
            "success": True,
            "user_name": member["사용자명"],
            "total_penalty": member["누적벌금"],
            "weekly_count": week_count,
            "remaining": remaining,
            "potential_penalty": remaining * PENALTY_PER_MISS
        }
    
    def calculate_weekly_penalties(self) -> List[Dict[str, Any]]:
        """주간 벌금 계산 (일요일 00:00에 실행)"""
        status_list = self.get_weekly_status()
        
        penalties = []
        for status in status_list:
            if not status["completed"]:
                penalty = status["remaining"] * PENALTY_PER_MISS
                penalties.append({
                    "user_id": status["user_id"],
                    "user_name": status["user_name"],
                    "missed_count": status["remaining"],
                    "penalty": penalty
                })
        
        return penalties
    
    def apply_penalties(self, penalties: List[Dict[str, Any]]) -> None:
        """벌금 적용 (누적벌금에 추가)"""
        members_sheet = self._get_or_create_sheet("멤버", [
            "사용자ID", "사용자명", "누적벌금", "가입일"
        ])
        
        members = members_sheet.get_all_records()
        
        for penalty in penalties:
            user_id = str(penalty["user_id"])
            for i, member in enumerate(members):
                if str(member["사용자ID"]) == user_id:
                    new_total = member["누적벌금"] + penalty["penalty"]
                    # 행 번호는 1-indexed이고 헤더가 있으므로 +2
                    members_sheet.update_cell(i + 2, 3, new_total)
                    break


# 싱글톤 인스턴스
_sheets_manager = None

def get_sheets_manager() -> SheetsManager:
    """SheetsManager 싱글톤 반환"""
    global _sheets_manager
    if _sheets_manager is None:
        _sheets_manager = SheetsManager()
    return _sheets_manager
