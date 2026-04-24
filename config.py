# 담임용 설정 파일

# 전역 변수
user_password = ""
class_number = 1  # 담임 학급 번호 (UI용)
class_count = 1   # btn_commands.py 호환용 (담임용은 항상 1)
last_download_folder = None
selected_region = '경기'  # 선택된 교육청 (기본값: 경기)

# 기본 메뉴 경로 (대부분의 학교에서 사용하는 값)
DEFAULT_MENU = {
    "absence": {
        "level1": "학급담임",
        "level2": "교육활동신청관리",
        "level3": "출결관리",
        "level4": "결석신고서관리"
    },
    "tardiness": {
        "level1": "학급담임",
        "level2": "교육활동신청관리",
        "level3": "출결관리",
        "level4": "지각·조퇴·결과신고서관리"
    },
    "monthly": {
        "level1": "학급담임",
        "level2": "학적",
        "level3": "출결현황및통계",
        "level4": "출결현황및통계"
    }
}
