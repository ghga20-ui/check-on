import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from utils import neis_click_btn, neis_go_menu, select_combobox_option_by_visible_text, open_neis_direct
import os
import sys
import re
import shutil
import config
import json
from logger_config import logger


driver = None

from tkinter import messagebox
from selenium.common import NoSuchWindowException
from selenium.common.exceptions import TimeoutException
#


def ensure_neis_session(skip_open=False, skip_click=False):
    """현재 앱 구조에서는 업무포털을 거치지 않고 NEIS로 직접 로그인한다."""
    if not skip_open:
        logger.info("나이스 직접 로그인으로 세션 준비")
        open_neis()
        return
    if not skip_click:
        logger.info("skip_click=False 요청이 있었지만 현재 직접 로그인 구조에서는 추가 탭 전환이 필요하지 않습니다.")


def move_latest_downloaded_file(target_dir, ext='.xlsx', start_time=None, max_retries=5, retry_delay=2):
    """
    다운로드 폴더에서 가장 최근 파일을 대상 폴더로 이동
    
    Args:
        target_dir: 이동할 대상 폴더
        ext: 파일 확장자 (기본: .xlsx)
        start_time: 다운로드 시작 시간 (이 시간 이후 파일만 대상)
        max_retries: 최대 재시도 횟수 (기본: 5)
        retry_delay: 재시도 간격 초 (기본: 2)
    """
    download_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
    
    for attempt in range(max_retries):
        # 다운로드 중인 파일들 제외하고 완료된 파일만 찾기
        completed_files = []
        for f in os.listdir(download_dir):
            if f.endswith(ext) and not f.endswith('.crdownload') and not f.endswith('.tmp'):
                file_path = os.path.join(download_dir, f)
                try:
                    # 파일이 완전히 다운로드되었는지 확인
                    file_size = os.path.getsize(file_path)
                    if file_size == 0:
                        continue
                    
                    # start_time이 지정되었으면 그 이후에 생성된 파일만 대상
                    if start_time is not None:
                        file_mtime = os.path.getmtime(file_path)
                        if file_mtime < start_time:
                            continue
                    
                    completed_files.append(file_path)
                except OSError:
                    continue  # 파일 접근 오류는 무시
        
        if not completed_files:
            if attempt < max_retries - 1:
                print(f"[대기] 다운로드 완료 대기 중... ({attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
                continue
            else:
                print("[오류] 다운로드 폴더에 완료된 파일이 없습니다.")
                return False
        
        # 가장 최근에 수정된 파일 선택
        latest_file = max(completed_files, key=os.path.getmtime)
        
        # 파일이 사용 중인지 확인
        try:
            with open(latest_file, 'rb') as test_file:
                pass
        except PermissionError:
            if attempt < max_retries - 1:
                print(f"[대기] 파일 사용 중, 재시도... ({attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
                continue
            else:
                print(f"[오류] 파일이 계속 사용 중: {os.path.basename(latest_file)}")
                return False
        
        # 파일 이동 시도
        target_path = os.path.join(target_dir, os.path.basename(latest_file))
        
        # 같은 이름 파일이 이미 있으면 덮어쓰기
        if os.path.exists(target_path):
            try:
                os.remove(target_path)
            except:
                pass
        
        try:
            shutil.move(latest_file, target_path)
            print(f"[이동 완료] {os.path.basename(latest_file)} → {target_dir}")
            return True
        except Exception as e:
            print(f"[경고] 이동 실패, 복사 시도: {e}")
            # 이동 실패 시 복사 후 삭제 시도
            try:
                shutil.copy2(latest_file, target_path)
                time.sleep(0.5)  # 복사 완료 대기
                os.remove(latest_file)
                print(f"[복사 완료] {os.path.basename(latest_file)} → {target_dir}")
                return True
            except Exception as copy_error:
                if attempt < max_retries - 1:
                    print(f"[대기] 복사도 실패, 재시도... ({attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f"[오류] 파일 이동/복사 실패: {copy_error}")
                    return False
    
    return False

# 메뉴 설정 로딩 (후방 호환 지원)
def load_neis_menus():
    """neis_menu.json에서 메뉴 프리셋을 읽어 반환한다.
    반환 형태: { 'absence': {level1..4}, 'tardiness': {level1..4}, 'monthly': {level1..4} }
    기존 단일 포맷(level1~4)도 지원하며 이 경우 모든 기능에 동일 값으로 채운다.
    오류 시 빈 딕셔너리를 반환한다.
    """
    menus = { 'absence': {}, 'tardiness': {}, 'monthly': {} }

    # PyInstaller 실행 시 올바른 경로 설정
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))

    path = os.path.join(application_path, 'neis_menu.json')
    if not os.path.exists(path):
        print("[경고] neis_menu.json 파일이 없습니다. UI의 config 메뉴를 사용합니다.")
        return menus
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # 신 포맷: 최상위에 absence/tardiness/monthly 존재
        if isinstance(data, dict) and ('absence' in data or 'tardiness' in data or 'monthly' in data):
            menus['absence'] = data.get('absence') or {}
            menus['tardiness'] = data.get('tardiness') or {}
            menus['monthly'] = data.get('monthly') or {}
            return menus
        # 구 포맷: level1~4 단일 세트
        if all(k in data for k in ['level1', 'level2', 'level3']):
            menus['absence'] = data
            menus['tardiness'] = data
            menus['monthly'] = data
            return menus
        print("[경고] neis_menu.json 형식이 예상과 다릅니다. UI의 config 메뉴를 사용합니다.")
        return menus
    except Exception as e:
        print(f"[경고] neis_menu.json 로드 실패: {e}. UI의 config 메뉴를 사용합니다.")
        return menus

# 주어진 메뉴 dict가 있으면 우선 사용, 없으면 config의 현재 값을 사용
def resolve_menu_levels(menu_dict):
    l1 = (menu_dict or {}).get('level1') or config.level1
    l2 = (menu_dict or {}).get('level2') or config.level2
    l3 = (menu_dict or {}).get('level3') or config.level3
    l4 = (menu_dict or {}).get('level4') or config.level4
    return l1, l2, l3, l4


def open_neis():
    """나이스에 직접 접속하여 로그인하는 함수 (경량화 버전)"""
    global driver
    
    # ➊ 웹드라이버 확인 및 생성
    if driver is not None:
        try:
            _ = driver.title
            # 이미 나이스에 접속되어 있는지 확인
            if '나이스' in driver.title or 'neis' in driver.current_url.lower():
                logger.info("이미 나이스에 접속되어 있습니다.")
                return
            logger.info("기존 드라이버 재사용")
        except Exception as e:
            logger.info(f"기존 드라이버 연결 끊김, 재시작: {e}")
            driver = None
    
    if driver is None:
        try:
            from selenium.webdriver.chrome.options import Options
            options = Options()
            
            # Chrome 프로필 디렉토리 설정
            profile_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'Chrome_NEIS_Profile')
            if not os.path.exists(profile_dir):
                os.makedirs(profile_dir)
            
            options.add_argument(f'--user-data-dir={profile_dir}')
            
            # Chrome 알림/권한 팝업 차단
            prefs = {
                "profile.default_content_setting_values.notifications": 2,
                "profile.default_content_setting_values.media_stream": 2,
                "profile.default_content_setting_values.geolocation": 2,
                "profile.default_content_setting_values.automatic_downloads": 1,
                "profile.content_settings.exceptions.local_network_access": {
                    "https://goe.neis.go.kr:443,*": {
                        "last_modified": "13000000000000000",
                        "setting": 1
                    }
                }
            }
            options.add_experimental_option("prefs", prefs)
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-notifications')
            options.add_argument('--disable-popup-blocking')
            options.add_argument('--disable-infobars')
            options.add_argument('--no-first-run')
            options.add_argument('--no-default-browser-check')
            options.add_argument('--disable-features=PrivacySandboxSettings4')
            options.add_argument('--disable-search-engine-choice-screen')
            options.add_argument('--disable-features=PrivateNetworkAccessSendPreflights,PrivateNetworkAccessRespectPreflightResults')
            
            logger.info("Chrome 브라우저 시작 중...")
            driver = webdriver.Chrome(options=options)
            logger.info("Chrome 브라우저 시작 성공")
        except Exception as e:
            messagebox.showerror("Chrome 드라이버 오류", 
                f"Chrome 브라우저를 시작할 수 없습니다.\n\n"
                f"해결 방법:\n"
                f"1. Chrome 브라우저가 설치되어 있는지 확인하세요\n"
                f"2. 인터넷 연결을 확인하세요\n\n"
                f"오류: {e}")
            raise
    
    # ➋ 나이스 직접 로그인 실행
    open_neis_direct(driver, config.user_password)


def select_calendar_date(driver, year, month, day):
    # 달력 팝업에서 연/월 맞추기
    import time
    
    # 달력 팝업이 로드될 때까지 대기
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.cl-calendar-header-text"))
        )
        print("[디버깅] 달력 팝업 로드 완료")
    except Exception as e:
        print(f"[오류] 달력 팝업 로드 실패: {e}")
        return
    
    while True:
        try:
            header = driver.find_element(By.CSS_SELECTOR, "div.cl-calendar-header-text")
            current_ym = header.text.strip()  # 예: "2025 6월"
            print(f"[디버깅] 달력 헤더 텍스트: '{current_ym}'")
            
            # 텍스트 파싱 개선
            if ' ' in current_ym and '월' in current_ym:
                cur_year, cur_month = int(current_ym.split()[0]), int(current_ym.split()[1][:-1])
            else:
                print(f"[오류] 달력 헤더 텍스트 형식 오류: '{current_ym}'")
                return
                
            print(f"[디버깅] 달력 현재 연/월: {cur_year} {cur_month} / 목표: {year} {month}")
            
            if (cur_year, cur_month) == (year, month):
                break
            elif (cur_year, cur_month) < (year, month):
                next_btn = driver.find_element(By.CSS_SELECTOR, "div.cl-calendar-header-next")
                driver.execute_script("arguments[0].click();", next_btn)
            else:
                prev_btn = driver.find_element(By.CSS_SELECTOR, "div.cl-calendar-header-prev")
                driver.execute_script("arguments[0].click();", prev_btn)
            time.sleep(0.3)
        except Exception as e:
            print(f"[오류] 달력 연/월 변경 중 실패: {e}")
            return
    
    # 원하는 일자 클릭
    try:
        day_btns = driver.find_elements(By.CSS_SELECTOR, f"div.cl-calendar-content-day[data-value='{int(day)}']")
        print(f"[디버깅] {day}일 버튼 개수: {len(day_btns)}")
        
        for btn in day_btns:
            if btn.is_displayed():
                driver.execute_script("arguments[0].click();", btn)
                print(f"[디버깅] {day}일 버튼 클릭 완료")
                break
        else:
            print(f"[오류] {day}일 버튼을 찾을 수 없음")
            # 현재 달력의 모든 일자 버튼 출력
            all_days = driver.find_elements(By.CSS_SELECTOR, "div.cl-calendar-content-day")
            print(f"[디버깅] 현재 달력의 일자 버튼 개수: {len(all_days)}")
            for i, day_btn in enumerate(all_days[:10]):  # 처음 10개만 출력
                print(f"  일자 {i}: data-value='{day_btn.get_attribute('data-value')}', text='{day_btn.text}'")
    except Exception as e:
        print(f"[오류] {day}일 버튼 클릭 실패: {e}")

def select_class_combobox(driver, class_num):
    # 1. '반' 콤보박스가 나타날 때까지 대기 및 필터링
    try:
        combos = WebDriverWait(driver, 10).until(
            lambda d: [c for c in d.find_elements(By.CSS_SELECTOR, "div.cl-control.cl-combobox")
                       if c.find_element(By.CSS_SELECTOR, ".cl-text").get_attribute("aria-label").startswith("반")]
        )
        combo = combos[0]
        print(f"[디버깅] 콤보박스 aria-label: {combo.find_element(By.CSS_SELECTOR, '.cl-text').get_attribute('aria-label')}")
    except Exception as e:
        print(f"[오류] '반' 콤보박스 대기/탐색 실패: {e}")
        return
    # 2. 콤보박스 버튼 클릭 (드롭다운 오픈)
    combo_btn = combo.find_element(By.CSS_SELECTOR, ".cl-combobox-button")
    combo_btn.click()
    print("[디버깅] 콤보박스 버튼 클릭 완료")
    time.sleep(0.3)
    # 3. 드롭다운 항목 모두 출력
    items = driver.find_elements(By.CSS_SELECTOR, "div.cl-combobox-item")
    print("[디버깅] 드롭다운 항목:")
    for item in items:
        print(f" - '{item.text.strip()}' (aria-label: {item.get_attribute('aria-label')})")
    # 4. 원하는 반 항목 클릭
    found = False
    for item in items:
        if item.text.strip() == str(class_num):
            item.click()
            print(f"[디버깅] {class_num}반 항목 클릭 완료")
            found = True
            break
    if not found:
        print(f"[오류] {class_num}반 항목을 찾을 수 없음")
        return
    time.sleep(0.3)
    # 5. 선택 후 aria-label 확인
    print(f"[디버깅] 선택 후 콤보박스 aria-label: {combo.find_element(By.CSS_SELECTOR, '.cl-text').get_attribute('aria-label')}")

def set_absent_period(driver, start_date, end_date):
    # 시작일자
    start_input = driver.find_element(By.CSS_SELECTOR, "input.cl-text[aria-label='결석시작일자']")
    start_btn = start_input.find_element(By.XPATH, "../../div[contains(@class, 'cl-dateinput-button')]")
    start_btn.click()
    select_calendar_date(driver, int(start_date[:4]), int(start_date[4:6]), int(start_date[6:]))
    # 종료일자
    end_input = driver.find_element(By.CSS_SELECTOR, "input.cl-text[aria-label='결석종료일자']")
    end_btn = end_input.find_element(By.XPATH, "../../div[contains(@class, 'cl-dateinput-button')]")
    end_btn.click()
    select_calendar_date(driver, int(end_date[:4]), int(end_date[4:6]), int(end_date[6:]))
    print(f"[디버깅] 결석 기간 달력 선택 완료: {start_date} ~ {end_date}")

def set_tardiness_period(driver, start_date, end_date):
    # 시작일자
    start_input = driver.find_element(By.CSS_SELECTOR, "input.cl-text[aria-label='신고시작일자']")
    start_btn = start_input.find_element(By.XPATH, "../../div[contains(@class, 'cl-dateinput-button')]")
    start_btn.click()
    select_calendar_date(driver, int(start_date[:4]), int(start_date[4:6]), int(start_date[6:]))
    # 종료일자
    end_input = driver.find_element(By.CSS_SELECTOR, "input.cl-text[aria-label='신고종료일자']")
    end_btn = end_input.find_element(By.XPATH, "../../div[contains(@class, 'cl-dateinput-button')]")
    end_btn.click()
    select_calendar_date(driver, int(end_date[:4]), int(end_date[4:6]), int(end_date[6:]))
    print(f"[디버깅] 결석 기간 달력 선택 완료: {start_date} ~ {end_date}")

def download_monthly_attendance(month, download_dir=None, skip_open=False, skip_click=False, menu=None):
    global driver
    try:
        print(f"[디버깅] download_monthly_attendance 함수 시작 - 입력 월: {month}")
        if not re.match(r"^20\d{2}-\d{2}$", month):
            messagebox.showerror("입력 오류", "월 입력은 YYYY-MM 형식이어야 합니다.")
            return
        year, mon = month.split('-')
        mon = str(int(mon))  # '06' -> '6'으로 변환
        ensure_neis_session(skip_open=skip_open, skip_click=skip_click)
        if driver is None:
            raise Exception("[오류] Selenium driver가 생성되지 않았습니다.")
        l1, l2, l3, l4 = resolve_menu_levels(menu)
        neis_go_menu(driver, l1, l2, l3, l4)
        time.sleep(1)
        # 월별 input 옆 달력 버튼 클릭
        try:
            month_input = driver.find_element(By.CSS_SELECTOR, "input.cl-text[aria-label='월별']")
            print(f"[디버깅] 월별 input outerHTML: {month_input.get_attribute('outerHTML')[:200]}")
            calendar_btn = month_input.find_element(By.XPATH, "../../div[contains(@class, 'cl-dateinput-button')]")
            print(f"[디버깅] 달력 버튼 outerHTML: {calendar_btn.get_attribute('outerHTML')[:200]}")
            print(f"[디버깅] 달력 버튼 is_displayed: {calendar_btn.is_displayed()}")
            driver.execute_script("arguments[0].scrollIntoView(true);", calendar_btn)
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//input[@aria-label='월별']/../../div[contains(@class, 'cl-dateinput-button')]")))
            calendar_btn.click()
            print("[디버깅] 월별 달력 버튼 클릭 완료")
        except Exception as e:
            print(f"[오류] 월별 달력 버튼 클릭 실패: {e}")
            try:
                print(f"[오류] 달력 버튼 outerHTML: {calendar_btn.get_attribute('outerHTML')[:300]}")
            except:
                print("[오류] 달력 버튼 outerHTML 추출 실패")
            return
        time.sleep(0.3)
        # (달력 팝업이 뜬 뒤) 연도 맞추기
        target_year = int(year)
        while True:
            try:
                header = driver.find_element(By.CSS_SELECTOR, "div.cl-calendar-header-text")
                current_ym = header.text.strip()
                print(f"[디버깅] 달력 헤더 텍스트: '{current_ym}'")
                
                cur_year = None
                # Case 1: "2025 6월" 형식
                if ' ' in current_ym and '월' in current_ym:
                    cur_year = int(current_ym.split()[0])
                # Case 2: "2025" 또는 "2025년" 형식 (월별 선택 달력일 경우 연도만 나올 수 있음)
                else:
                    match = re.search(r'(\d{4})', current_ym)
                    if match:
                        cur_year = int(match.group(1))
                
                if cur_year is None:
                    print(f"[오류] 달력 헤더 텍스트 파싱 실패: '{current_ym}'")
                    break
                
                print(f"[디버깅] 달력 현재 연도: {cur_year} / 목표: {target_year}")
                
                if cur_year == target_year:
                    break
                elif cur_year < target_year:
                    next_btn = driver.find_element(By.CSS_SELECTOR, "div.cl-calendar-header-next")
                    driver.execute_script("arguments[0].click();", next_btn)
                else:
                    prev_btn = driver.find_element(By.CSS_SELECTOR, "div.cl-calendar-header-prev")
                    driver.execute_script("arguments[0].click();", prev_btn)
                time.sleep(0.3)
            except Exception as e:
                print(f"[오류] 달력 연도 변경 중 실패: {e}")
                break

        # (달력 팝업이 뜬 뒤) 원하는 월 클릭
        try:
            month_texts = [el.text for el in driver.find_elements(By.CSS_SELECTOR, "div.cl-calendar-content-month .cl-text")]
            print(f"[디버깅] 달력 팝업 내 월 텍스트 목록: {month_texts}")
            found = False
            for el in driver.find_elements(By.CSS_SELECTOR, "div.cl-calendar-content-month .cl-text"):
                print(f"[디버깅] 달력 팝업 내 월 버튼: '{el.text.strip()}'")
                if el.text.strip() == mon:
                    el.click()
                    print(f"[디버깅] {mon}월 버튼 클릭 완료")
                    found = True
                    break
            if not found:
                print(f"[오류] {mon}월 버튼을 찾을 수 없음")
                return
        except Exception as e:
            print(f"[오류] 달력 팝업 내 월 버튼 클릭 실패: {e}")
            return
        # 이하 기존 1~12반 반복 처리 및 팝업/다운로드 등은 그대로 유지
        total_classes = config.class_count
        for class_num in range(1, total_classes + 1):
            try:
                progress = class_num * 100 // total_classes
                print(f"[진행] 월별 출결현황: {class_num}/{total_classes}반 처리 중... ({progress}% 완료)")
                # ➊ '반' 드롭다운에서 해당 반 선택
                print(f"[디버깅] {class_num}반 - 콤보박스 선택 시도")
                select_combobox_option_by_visible_text(driver, '반', class_num)
                # ➋ 조회 버튼 클릭
                print(f"[디버깅] {class_num}반 - 조회 버튼 클릭")
                neis_click_btn(driver, '조회')
                # ➌ 월별 출결현황 버튼 클릭
                print(f"[디버깅] {class_num}반 - 월별 출결현황 버튼 클릭")
                neis_click_btn(driver, '월별 출결현황')
                # ➍ 팝업창 셀병합 해제
                try:
                    merge_checkbox = driver.find_element(By.CSS_SELECTOR, "div.cl-checkbox-icon[aria-label='셀병합'][role='checkbox']")
                    if merge_checkbox.get_attribute('aria-checked') == 'true':
                        merge_checkbox.click()
                        print(f"[디버깅] {class_num}반 셀병합 체크 해제 완료")
                    else:
                        print(f"[디버깅] {class_num}반 셀병합 이미 해제됨")
                except Exception as e:
                    print(f"[오류] {class_num}반 셀병합 체크박스 처리 실패: {e}")
                # 팝업 내부 조회 버튼 명시적 대기 후 클릭
                try:
                    # 팝업이 완전히 로드될 때까지 대기
                    time.sleep(1)
                    # 모든 조회 버튼 찾기
                    search_btns = driver.find_elements(By.CSS_SELECTOR, "div[aria-label='조회'][role='button']")
                    print(f"[디버깅] {class_num}반 - 조회 버튼 개수: {len(search_btns)}")
                    
                    if len(search_btns) < 2:
                        print("[오류] 팝업 내부 조회 버튼을 찾을 수 없습니다.")
                        continue
                    
                    # 보이는 조회 버튼 중 마지막 것 선택 (팝업 내부 버튼)
                    visible_search_btns = [btn for btn in search_btns if btn.is_displayed()]
                    if not visible_search_btns:
                        print("[오류] 보이는 조회 버튼이 없습니다.")
                        continue
                    
                    popup_search_btn = visible_search_btns[-1]  # 마지막 보이는 버튼
                    print(f"[디버깅] {class_num}반 - 선택된 조회 버튼 aria-label: {popup_search_btn.get_attribute('aria-label')}")
                    
                    # 스크롤하여 버튼이 보이도록 함
                    driver.execute_script("arguments[0].scrollIntoView(true);", popup_search_btn)
                    time.sleep(0.5)
                    
                    # JavaScript로 클릭 (더 안정적)
                    driver.execute_script("arguments[0].click();", popup_search_btn)
                    print(f"[디버깅] {class_num}반 팝업 내부 조회 버튼 클릭 완료")
                    time.sleep(1)
                except Exception as e:
                    print(f"[오류] {class_num}반 팝업 조회 버튼 클릭 실패: {e}")
                    # 현재 화면의 모든 버튼 정보 출력
                    try:
                        all_btns = driver.find_elements(By.CSS_SELECTOR, "div[role='button']")
                        print(f"[디버깅] 현재 화면의 버튼 개수: {len(all_btns)}")
                        for i, btn in enumerate(all_btns[:5]):  # 처음 5개만 출력
                            print(f"  버튼 {i}: aria-label='{btn.get_attribute('aria-label')}', text='{btn.text}'")
                    except:
                        pass
                    continue
                try:
                    download_start_time = time.time()  # 다운로드 시작 시간 기록
                    excel_btn = driver.find_element(By.CSS_SELECTOR, "div[aria-label='엑셀다운로드'][role='button']")
                    excel_btn.click()
                    print(f"[디버깅] {class_num}반 엑셀다운로드 버튼 클릭 완료")
                except Exception as e:
                    print(f"[오류] {class_num}반 엑셀다운로드 버튼 클릭 실패: {e}")
                    download_start_time = time.time()  # 실패해도 시간 기록
                try:
                    confirm_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'cl-text') and text()='확인']/ancestor::div[@role='button']"))
                    )
                    confirm_btn.click()
                    print(f"[디버깅] {class_num}반 확인 버튼 클릭 완료")
                except Exception as e:
                    print(f"[오류] {class_num}반 확인 버튼 클릭 실패: {e}")
                    btns = driver.find_elements(By.CSS_SELECTOR, "div[role='button'] .cl-text")
                    print("[디버깅] 현재 화면의 버튼 텍스트 목록:", [b.text for b in btns])
                # 월별 출결현황 팝업 닫기 버튼 클릭 (팝업 내 하단 닫기 버튼만 명확하게)
                try:
                    # 1. 가장 최근에 뜬 월별 출결현황 팝업(dialog) 찾기
                    dialogs = driver.find_elements(By.CSS_SELECTOR, "div[role='dialog'][aria-label*='월별 출결 현황']")
                    print(f"[디버깅] 월별 출결현황 팝업(dialog) 개수: {len(dialogs)}")
                    if not dialogs:
                        print("[오류] 월별 출결현황 팝업(dialog) 없음")
                        continue
                    dialog = dialogs[-1]  # 최상단 팝업
                    # 2. 팝업 내 aria-label='닫기' & role='button'인 버튼 중 텍스트가 '닫기'인 것만 필터
                    close_btns = dialog.find_elements(By.CSS_SELECTOR, "[aria-label='닫기'][role='button']")
                    print(f"[디버깅] 팝업 내 닫기 버튼 개수: {len(close_btns)}")
                    found = False
                    for i, btn in enumerate(close_btns):
                        print(f"  [디버깅] 닫기 버튼 {i}: text='{btn.text}' outerHTML='{btn.get_attribute('outerHTML')[:80]}'")
                        if '닫기' in btn.text:
                            print(f"[디버깅] 하단 닫기 버튼 발견! 클릭 시도")
                            driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                            driver.execute_script("arguments[0].click();", btn)
                            found = True
                            break
                    if not found:
                        print("[오류] 팝업 내 하단 닫기 버튼을 찾을 수 없음")
                        continue
                    # 3. 닫기 버튼 클릭 후 오버레이가 사라질 때까지 대기
                    try:
                        WebDriverWait(driver, 5).until_not(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.cl-overlay"))
                        )
                        print("[디버깅] 닫기 버튼 클릭 후 오버레이 사라짐 확인")
                    except Exception as e:
                        print(f"[경고] 닫기 후 오버레이가 5초 내에 사라지지 않음: {e}")
                except Exception as e:
                    print(f"[오류] 월별 출결현황 팝업 닫기 버튼 클릭 실패: {e}")
                print(f"[완료] 월별 출결현황 {class_num}반 다운로드 완료!")
                if download_dir:
                    move_latest_downloaded_file(download_dir, ext='.xlsx', start_time=download_start_time)
            except Exception as e:
                print(f"[오류] {class_num}반 전체 처리 실패: {e}")
                continue
        print("[디버깅] 월별 출결 현황 다운로드 전체 완료")
    except Exception as e:
        print(f"[오류] 월별 출결 현황 다운로드 전체 실패: {e}")

def neis_attendace_v2(start_date, end_date, download_dir=None, skip_open=False, skip_click=False, menu=None):
    """결석신고서 다운로드 v2 - 전체 학급을 한 번에 조회"""
    global driver
    try:
        logger.info("neis_attendace_v2 함수 시작 (전체 학급 버전)")
        ensure_neis_session(skip_open=skip_open, skip_click=skip_click)
        logger.info("3단계: 결석신고관리 메뉴로 이동")
        l1, l2, l3, l4 = resolve_menu_levels(menu)
        neis_go_menu(driver, l1, l2, l3, l4)
        logger.info("4단계: 결석 기간 달력 자동화")
        set_absent_period(driver, start_date, end_date)

        # 학급 드롭다운이 '전체'로 설정되어 있는지 확인 (기본값이 전체이므로 별도 선택 불필요)
        # 하지만 혹시 모르니 '전체' 선택 시도
        try:
            logger.info("5단계: 학급 드롭다운 '전체' 선택 시도")
            select_combobox_option_by_visible_text(driver, '반', '전체')
        except Exception as e:
            logger.warning(f"'전체' 선택 실패 (이미 전체로 설정되어 있을 수 있음): {e}")

        logger.info("6단계: 조회 버튼 클릭")
        neis_click_btn(driver, '조회')
        time.sleep(1)

        logger.info("7단계: 자료 내려받기 버튼 클릭")
        download_start_time = time.time()  # 다운로드 시작 시간 기록
        neis_click_btn(driver, '자료 내려받기')

        logger.info("8단계: 확인 버튼 클릭")
        neis_click_btn(driver, '확인')

        logger.info("결석신고서 전체 학급 다운로드 완료!")
        if download_dir:
            move_latest_downloaded_file(download_dir, ext='.xlsx', start_time=download_start_time)

        logger.info("neis_attendace_v2 전체 완료")
    except Exception as e:
        logger.error(f"neis_attendace_v2 함수 전체 오류: {e}")
        raise

def download_tardiness_report_v2(start_date, end_date, download_dir=None, skip_open=False, skip_click=False, menu=None):
    """지각,조퇴,결과신고서 다운로드 v2 - 전체 학급을 한 번에 조회"""
    global driver
    try:
        print("[디버깅] download_tardiness_report_v2 함수 시작 (전체 학급 버전)")
        ensure_neis_session(skip_open=skip_open, skip_click=skip_click)
        print("[디버깅] 3단계: 지각,조퇴,결과신고서 메뉴로 이동")
        l1, l2, l3, l4 = resolve_menu_levels(menu)
        neis_go_menu(driver, l1, l2, l3, l4)
        print("[디버깅] 4단계: 기간 달력 자동화")
        set_tardiness_period(driver, start_date, end_date)

        # 학급 드롭다운이 '전체'로 설정되어 있는지 확인 (기본값이 전체이므로 별도 선택 불필요)
        # 하지만 혹시 모르니 '전체' 선택 시도
        try:
            print("[디버깅] 5단계: 학급 드롭다운 '전체' 선택 시도")
            select_combobox_option_by_visible_text(driver, '반', '전체')
        except Exception as e:
            print(f"[경고] '전체' 선택 실패 (이미 전체로 설정되어 있을 수 있음): {e}")

        print("[디버깅] 6단계: 조회 버튼 클릭")
        neis_click_btn(driver, '조회')
        time.sleep(1)

        print("[디버깅] 7단계: 자료 내려받기 버튼 클릭")
        download_start_time = time.time()  # 다운로드 시작 시간 기록
        neis_click_btn(driver, '자료 내려받기')

        print("[디버깅] 8단계: 확인 버튼 클릭")
        neis_click_btn(driver, '확인')

        print("[완료] 지각·조퇴·결과신고서 전체 학급 다운로드 완료!")
        if download_dir:
            move_latest_downloaded_file(download_dir, ext='.xlsx', start_time=download_start_time)

        print("[디버깅] download_tardiness_report_v2 전체 완료")
    except Exception as e:
        print(f"[오류] download_tardiness_report_v2 함수 전체 오류: {e}")
        raise

