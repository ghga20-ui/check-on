# 전국 시도교육청 NEIS URL 정보
# 17개 교육청 지원

REGIONS = {
    "서울": {"name": "서울특별시교육청", "url": "https://sen.neis.go.kr/"},
    "경기": {"name": "경기도교육청", "url": "https://goe.neis.go.kr/"},
    "인천": {"name": "인천광역시교육청", "url": "https://ice.neis.go.kr/"},
    "강원": {"name": "강원특별자치도교육청", "url": "https://kwe.neis.go.kr/"},
    "부산": {"name": "부산광역시교육청", "url": "https://pen.neis.go.kr/"},
    "대구": {"name": "대구광역시교육청", "url": "https://dge.neis.go.kr/"},
    "광주": {"name": "광주광역시교육청", "url": "https://gen.neis.go.kr/"},
    "대전": {"name": "대전광역시교육청", "url": "https://dje.neis.go.kr/"},
    "울산": {"name": "울산광역시교육청", "url": "https://use.neis.go.kr/"},
    "세종": {"name": "세종특별자치시교육청", "url": "https://sje.neis.go.kr/"},
    "경남": {"name": "경상남도교육청", "url": "https://gne.neis.go.kr/"},
    "경북": {"name": "경상북도교육청", "url": "https://gbe.neis.go.kr/"},
    "전남": {"name": "전라남도교육청", "url": "https://jne.neis.go.kr/"},
    "전북": {"name": "전라북도교육청", "url": "https://jbe.neis.go.kr/"},
    "충남": {"name": "충청남도교육청", "url": "https://cne.neis.go.kr/"},
    "충북": {"name": "충청북도교육청", "url": "https://cbe.neis.go.kr/"},
    "제주": {"name": "제주특별자치도교육청", "url": "https://jje.neis.go.kr/"}
}

# 교육청 목록 (드롭다운용)
REGION_LIST = list(REGIONS.keys())

# 기본 교육청
DEFAULT_REGION = "경기"


def get_neis_url(region_code):
    """교육청 코드로 NEIS URL 반환"""
    if region_code in REGIONS:
        return REGIONS[region_code]["url"]
    return REGIONS[DEFAULT_REGION]["url"]


def get_region_name(region_code):
    """교육청 코드로 교육청 전체 이름 반환"""
    if region_code in REGIONS:
        return REGIONS[region_code]["name"]
    return REGIONS[DEFAULT_REGION]["name"]
