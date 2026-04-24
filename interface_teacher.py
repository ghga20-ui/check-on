
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import os
import sys
import json
import threading
import shutil
import calendar
from datetime import datetime
import win32com.client
import win32crypt
import pythoncom
from CTkMessagebox import CTkMessagebox
import queue

# 경로 설정 (개발 환경 및 PyInstaller 빌드 모두 지원)
if getattr(sys, 'frozen', False):
    APPLICATION_PATH = os.path.dirname(sys.executable)
else:
    APPLICATION_PATH = os.path.dirname(os.path.abspath(__file__))

# 로컬 모듈 import (teacher 폴더 내 파일들만 사용 - 완전 독립)
import config
from btn_commands import (open_neis, neis_attendace_v2, download_tardiness_report_v2,
                          download_monthly_attendance)
from regions import REGION_LIST, DEFAULT_REGION
from logger_config import logger

# --- 설정 및 상수 ---
# Solarized Light Palette
SOLARIZED = {
    "base03": "#002b36",
    "base02": "#073642",
    "base01": "#586e75",
    "base00": "#657b83",
    "base0":  "#839496",
    "base1":  "#93a1a1",
    "base2":  "#eee8d5",
    "base3":  "#fdf6e3",
    "yellow": "#b58900",
    "orange": "#cb4b16",
    "red":    "#dc322f",
    "magenta":"#d33682",
    "violet": "#6c71c4",
    "blue":   "#268bd2",
    "cyan":   "#2aa198",
    "green":  "#859900"
}

ctk.set_appearance_mode("Light")

PASSWORD_FILE = os.path.join(APPLICATION_PATH, "password.bin")
MENU_FILE = os.path.join(APPLICATION_PATH, "neis_menu_teacher.json")
EXCEL_FILE = os.path.join(APPLICATION_PATH, "Attendance Result.xlsm")

# --- 유틸리티 클래스 ---
class TextRedirector(object):
    def __init__(self, q):
        self.q = q

    def write(self, s):
        self.q.put(s)

    def flush(self):
        pass

# --- 메인 앱 클래스 ---
import tkinter.font

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("나이스 출결관리 프로 - 담임용")
        self.geometry("700x650") 
        self.configure(fg_color=SOLARIZED["base3"]) 
        
        # 폰트 선택 로직
        available_fonts = set(tkinter.font.families())
        candidates = ["나눔바른고딕OTF", "NanumBarunGothicOTF", "나눔바른고딕", "NanumBarunGothic", "나눔고딕OTF", "Malgun Gothic"] 
        selected_font = "Malgun Gothic" 
        
        for font in candidates:
            if font in available_fonts:
                selected_font = font
                break

        self.main_font = (selected_font, 14) 
        self.bold_font = (selected_font, 14, "bold")
        self.header_font = (selected_font, 22, "bold")
        
        # Grid 설정
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)
        
        self.init_variables()
        self.create_header()
        self.create_settings_card()
        self.create_vertical_tabs() 
        self.create_action_buttons()
        self.create_status_label()
        self.create_status_bar()
        self.create_footer()

        self.load_data()
        self.select_tab("absence")
        
        # 필수 파일 체크
        self.after(500, self.check_dependencies)

    def check_dependencies(self):
        if not os.path.exists(EXCEL_FILE):
             CTkMessagebox(title="파일 누락", message="[주의] 'Attendance Result.xlsm' 파일이 없습니다.\n프로그램 실행에 문제가 생길 수 있습니다.", icon="warning")

    def init_variables(self):
        self.selected_year = ctk.StringVar(value=str(datetime.now().year))
        self.selected_month = ctk.StringVar(value=f"{datetime.now().month:02d}")
        self.class_number = ctk.IntVar(value=1)  # 담임 학급 번호
        self.region_var = ctk.StringVar(value=DEFAULT_REGION)  # 교육청 선택
        
        # 메뉴 변수 (기본값으로 초기화)
        self.absence_vars = [ctk.StringVar(value=config.DEFAULT_MENU["absence"].get(f"level{i+1}", "")) for i in range(4)]
        self.tardiness_vars = [ctk.StringVar(value=config.DEFAULT_MENU["tardiness"].get(f"level{i+1}", "")) for i in range(4)]
        self.monthly_vars = [ctk.StringVar(value=config.DEFAULT_MENU["monthly"].get(f"level{i+1}", "")) for i in range(4)]
        
        self.password_var = ctk.StringVar()
        self.password_var.trace_add("write", self.on_password_change)

    def on_password_change(self, *args):
        pw = self.password_var.get()
        config.user_password = pw
        if hasattr(self, '_pw_save_job'):
            self.after_cancel(self._pw_save_job)
        self._pw_save_job = self.after(300, self._save_password_to_file)

    def _save_password_to_file(self):
        pw = self.password_var.get()
        try:
            encrypted = win32crypt.CryptProtectData(pw.encode('utf-8'))
            with open(PASSWORD_FILE, "wb") as f:
                f.write(encrypted)
            return True
        except Exception as e:
            logger.warning(f"비밀번호 저장 실패: {e}")
            return False

    def create_header(self):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="ew")
        
        top_line = ctk.CTkFrame(header_frame, fg_color="transparent")
        top_line.pack(side="top", anchor="w")

        title_label = ctk.CTkLabel(top_line, text="나이스 출결관리 프로 - 담임용", font=self.header_font, text_color=SOLARIZED["base01"])
        title_label.pack(side="left")
        
        ver_label = ctk.CTkLabel(top_line, text="v1.0", font=self.main_font, text_color=SOLARIZED["base1"])
        ver_label.pack(side="left", padx=10, pady=(8, 0))
        
        slogan_label = ctk.CTkLabel(header_frame, text="우리반 출결 관리 클릭 한 번으로!", 
                                    font=(self.main_font[0], 13), text_color=SOLARIZED["base00"])
        slogan_label.pack(side="top", anchor="w", pady=(2, 0))

    def create_settings_card(self):
        card = ctk.CTkFrame(self, fg_color=SOLARIZED["base2"])
        card.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        card.grid_columnconfigure((1, 3, 5, 7, 9), weight=1)

        lbl_kwargs = {"font": self.bold_font, "text_color": SOLARIZED["base00"]}
        
        # 교육청 선택 (첫 번째)
        ctk.CTkLabel(card, text="교육청", **lbl_kwargs).grid(row=0, column=0, padx=10, pady=15, sticky="w")
        region_combo = ctk.CTkComboBox(card, variable=self.region_var, values=REGION_LIST, width=70,
                                       command=self.on_region_change,
                                       font=self.main_font, fg_color=SOLARIZED["base3"], border_color=SOLARIZED["base1"], text_color=SOLARIZED["base00"],
                                       button_color=SOLARIZED["base1"], button_hover_color=SOLARIZED["base0"], dropdown_fg_color=SOLARIZED["base3"])
        region_combo.grid(row=0, column=1, padx=5, pady=15, sticky="ew")
        
        ctk.CTkLabel(card, text="비밀번호", **lbl_kwargs).grid(row=0, column=2, padx=5, pady=15, sticky="e")
        pw_entry = ctk.CTkEntry(card, textvariable=self.password_var, show="*", width=100, 
                                font=self.main_font, fg_color=SOLARIZED["base3"], border_color=SOLARIZED["base1"], text_color=SOLARIZED["base00"])
        pw_entry.grid(row=0, column=3, padx=5, pady=15, sticky="ew")

        ctk.CTkLabel(card, text="연도", **lbl_kwargs).grid(row=0, column=4, padx=5, pady=15, sticky="e")
        year_combo = ctk.CTkComboBox(card, variable=self.selected_year, values=[str(y) for y in range(2020, 2031)], width=70,
                                     font=self.main_font, fg_color=SOLARIZED["base3"], border_color=SOLARIZED["base1"], text_color=SOLARIZED["base00"],
                                     button_color=SOLARIZED["base1"], button_hover_color=SOLARIZED["base0"], dropdown_fg_color=SOLARIZED["base3"])
        year_combo.grid(row=0, column=5, padx=5, pady=15, sticky="ew")

        ctk.CTkLabel(card, text="월", **lbl_kwargs).grid(row=0, column=6, padx=5, pady=15, sticky="e")
        month_combo = ctk.CTkComboBox(card, variable=self.selected_month, values=[f"{m:02d}" for m in range(1, 13)], width=55,
                                      font=self.main_font, fg_color=SOLARIZED["base3"], border_color=SOLARIZED["base1"], text_color=SOLARIZED["base00"],
                                      button_color=SOLARIZED["base1"], button_hover_color=SOLARIZED["base0"], dropdown_fg_color=SOLARIZED["base3"])
        month_combo.grid(row=0, column=7, padx=5, pady=15, sticky="ew")

        # 내 반 번호 (담임용 추가)
        ctk.CTkLabel(card, text="반", **lbl_kwargs).grid(row=0, column=8, padx=5, pady=15, sticky="e")
        class_combo = ctk.CTkComboBox(card, variable=self.class_number, values=[str(i) for i in range(1, 16)], width=55,
                                      font=self.main_font, fg_color=SOLARIZED["base3"], border_color=SOLARIZED["base1"], text_color=SOLARIZED["base00"],
                                      button_color=SOLARIZED["base1"], button_hover_color=SOLARIZED["base0"], dropdown_fg_color=SOLARIZED["base3"])
        class_combo.grid(row=0, column=9, padx=(5, 10), pady=15, sticky="ew")

    def on_region_change(self, value):
        """교육청 변경 시 설정 업데이트"""
        config.selected_region = value
        self.save_menus()

    def create_vertical_tabs(self):
        self.tab_container = ctk.CTkFrame(self, fg_color=SOLARIZED["base2"])
        self.tab_container.grid(row=2, column=0, padx=20, pady=5, sticky="nsew")
        
        self.tab_container.grid_columnconfigure(1, weight=1)
        self.tab_container.grid_rowconfigure(0, weight=1)

        self.left_col = ctk.CTkFrame(self.tab_container, fg_color="transparent", width=120)
        self.left_col.grid(row=0, column=0, sticky="ns", padx=(10, 5), pady=10)
        
        self.tab_btn_abs = self.create_tab_btn(self.left_col, "결석 신고", "absence", 0)
        self.tab_btn_tard = self.create_tab_btn(self.left_col, "지각 조퇴", "tardiness", 1)
        self.tab_btn_mon = self.create_tab_btn(self.left_col, "월별 출결", "monthly", 2)

        self.right_col = ctk.CTkFrame(self.tab_container, fg_color="transparent")
        self.right_col.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.right_col.grid_rowconfigure(0, weight=1)
        self.right_col.grid_columnconfigure(0, weight=1)

        self.frame_absence = self.create_menu_inputs_frame(self.right_col, self.absence_vars)
        self.frame_tardiness = self.create_menu_inputs_frame(self.right_col, self.tardiness_vars)
        self.frame_monthly = self.create_menu_inputs_frame(self.right_col, self.monthly_vars)

    def create_tab_btn(self, parent, text, code, row):
        btn = ctk.CTkButton(parent, text=text, command=lambda: self.select_tab(code),
                            font=self.bold_font, height=40, anchor="w",
                            fg_color="transparent", text_color=SOLARIZED["base00"],
                            hover_color=SOLARIZED["base3"])
        btn.pack(fill="x", pady=2)
        return btn

    def select_tab(self, code):
        for btn in [self.tab_btn_abs, self.tab_btn_tard, self.tab_btn_mon]:
            btn.configure(fg_color="transparent", text_color=SOLARIZED["base00"])
        
        if code == "absence":
            self.tab_btn_abs.configure(fg_color=SOLARIZED["base3"], text_color=SOLARIZED["blue"])
            self.frame_absence.tkraise()
        elif code == "tardiness":
            self.tab_btn_tard.configure(fg_color=SOLARIZED["base3"], text_color=SOLARIZED["blue"])
            self.frame_tardiness.tkraise()
        elif code == "monthly":
            self.tab_btn_mon.configure(fg_color=SOLARIZED["base3"], text_color=SOLARIZED["blue"])
            self.frame_monthly.tkraise()

    def create_menu_inputs_frame(self, parent, vars_list):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_columnconfigure(1, weight=1)
        
        labels = ["1차 메뉴", "2차 메뉴", "3차 메뉴", "4차 메뉴"]
        for i, (lbl, var) in enumerate(zip(labels, vars_list)):
            ctk.CTkLabel(frame, text=lbl, font=self.main_font, text_color=SOLARIZED["base00"]).grid(row=i, column=0, padx=15, pady=8, sticky="e")
            ctk.CTkEntry(frame, textvariable=var, font=self.main_font, 
                         fg_color=SOLARIZED["base3"], border_color=SOLARIZED["base1"], text_color=SOLARIZED["base01"]).grid(row=i, column=1, padx=15, pady=8, sticky="ew")
        return frame

    def create_action_buttons(self):
        self._action_buttons = []
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=3, column=0, padx=20, pady=5, sticky="ew")
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)

        unified_color = SOLARIZED["base1"] 
        unified_hover = SOLARIZED["base0"]
        highlight_color = SOLARIZED["blue"]
        highlight_hover = SOLARIZED["violet"]
        
        # 메인 버튼 (원스톱 자동화)
        self._action_buttons.append(self.add_btn(btn_frame, "🚀 원스톱 자동화 (다운+엑셀)", self.run_onestop_teacher, 0, 0, fg_color=highlight_color, hover_color=highlight_hover, colspan=2))

        # 기본 도구
        self._action_buttons.append(self.add_btn(btn_frame, "신고서만 다운로드", self.run_download_reports, 1, 0, fg_color=unified_color, hover_color=unified_hover))
        self._action_buttons.append(self.add_btn(btn_frame, "월별 출결만 다운로드", self.run_download_monthly, 1, 1, fg_color=unified_color, hover_color=unified_hover))

        self._action_buttons.append(self.add_btn(btn_frame, "엑셀 자동화만 실행", self.run_only_excel_macro, 2, 0, fg_color=unified_color, hover_color=unified_hover))
        self._action_buttons.append(self.add_btn(btn_frame, "나이스 접속", open_neis, 2, 1, fg_color=unified_color, hover_color=unified_hover))

    def add_btn(self, parent, text, command, r, c, fg_color=None, hover_color=None, colspan=1):
        btn = ctk.CTkButton(parent, text=text, command=command, 
                            height=45, font=self.bold_font, text_color=SOLARIZED["base3"],
                            fg_color=fg_color, hover_color=hover_color)
        btn.grid(row=r, column=c, columnspan=colspan, padx=10, pady=4, sticky="ew")
        return btn

    def create_status_label(self):
        self.step_label = ctk.CTkLabel(self, text="", font=self.main_font,
                                       text_color=SOLARIZED["blue"])
        self.step_label.grid(row=4, column=0, padx=20, pady=(2, 0), sticky="w")

    def create_status_bar(self):
        self.status_box = ctk.CTkTextbox(self, height=80, fg_color=SOLARIZED["base02"], text_color=SOLARIZED["cyan"], font=(self.main_font[0], 12))
        self.status_box.grid(row=5, column=0, padx=20, pady=(5, 10), sticky="ew")
        self.status_box.configure(state='disabled')
        
        self.log_queue = queue.Queue()
        sys.stdout = TextRedirector(self.log_queue)
        self.check_log_queue()

    def check_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.status_box.configure(state='normal')
                self.status_box.insert('end', msg)
                self.status_box.see('end')
                self.status_box.configure(state='disabled')
        except queue.Empty:
            pass
        finally:
            self.after(100, self.check_log_queue)

    def create_footer(self):
        footer = ctk.CTkLabel(self, text="© 2025 박세준. All rights reserved.", text_color=SOLARIZED["base1"], font=(self.main_font[0], 11))
        footer.grid(row=6, column=0, pady=(0, 10))

    # --- Logic Methods ---
    def load_data(self):
        # 구 파일(password.txt) 마이그레이션
        old_password_file = os.path.join(APPLICATION_PATH, "password.txt")
        if os.path.exists(old_password_file):
            try:
                with open(old_password_file, 'r', encoding='utf-8') as f:
                    plain = f.read().strip()
                config.user_password = plain
                self.password_var.set(plain)  # UI 업데이트 (on_password_change의 디바운싱은 무시)
                if self._save_password_to_file():  # 동기 저장 직접 호출, 반환값으로 성공 확인
                    os.remove(old_password_file)
                    logger.info("password.txt → password.bin 마이그레이션 완료")
                else:
                    logger.warning("암호화 저장 실패 — password.txt 유지")
            except Exception as e:
                logger.warning(f"비밀번호 마이그레이션 실패: {e}")
        elif os.path.exists(PASSWORD_FILE):
            try:
                with open(PASSWORD_FILE, 'rb') as f:
                    _, decrypted = win32crypt.CryptUnprotectData(f.read())
                    self.password_var.set(decrypted.decode('utf-8'))
            except Exception as e:
                logger.warning(f"비밀번호 불러오기 실패: {e}")
        if os.path.exists(MENU_FILE):
            try:
                with open(MENU_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                def set_vars(target_vars, data_dict):
                    if not data_dict: return
                    for i in range(4):
                        val = data_dict.get(f"level{i+1}", "")
                        if val:
                            target_vars[i].set(val)
                if isinstance(data, dict):
                     # 교육청 불러오기
                     if "region" in data:
                         self.region_var.set(data["region"])
                         config.selected_region = data["region"]
                     set_vars(self.absence_vars, data.get("absence", {}))
                     set_vars(self.tardiness_vars, data.get("tardiness", {}))
                     set_vars(self.monthly_vars, data.get("monthly", {}))
                     if "class_number" in data:
                         self.class_number.set(data["class_number"])
            except Exception as e:
                logger.warning(f"설정 불러오기 실패: {e}")

    def save_menus(self):
        data = {
            "region": self.region_var.get(),
            "absence": {f"level{i+1}": v.get() for i, v in enumerate(self.absence_vars)},
            "tardiness": {f"level{i+1}": v.get() for i, v in enumerate(self.tardiness_vars)},
            "monthly": {f"level{i+1}": v.get() for i, v in enumerate(self.monthly_vars)},
            "class_number": self.class_number.get()
        }
        try:
            with open(MENU_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"메뉴 저장 실패: {e}")

    def get_period(self):
        y = self.selected_year.get()
        m = self.selected_month.get()
        last_day = calendar.monthrange(int(y), int(m))[1]
        start_date = f"{y}{m}01"
        end_date = f"{y}{m}{last_day:02d}"
        return start_date, end_date, f"{y}-{m}"

    def select_download_folder(self):
        initial_dir = config.last_download_folder if config.last_download_folder and os.path.exists(config.last_download_folder) else None
        folder = filedialog.askdirectory(title="다운로드 폴더 선택", initialdir=initial_dir)
        if folder:
            config.last_download_folder = folder
        return folder

    def get_menu_dict(self, vars_list):
        return {f"level{i+1}": v.get() for i, v in enumerate(vars_list)}

    def _set_buttons_state(self, state):
        for btn in self._action_buttons:
            btn.configure(state=state)

    def _show_messagebox(self, title, message, icon):
        try:
            self.after(0, lambda: CTkMessagebox(title=title, message=message, icon=icon))
        except Exception:
            pass

    def run_worker(self, task_func, task_name):
        self._set_buttons_state("disabled")  # 메인 스레드에서 즉시 비활성화
        def wrapper():
            print(f"[시작] {task_name} 시작합니다...")
            try:
                task_func()
                print(f"[완료] {task_name} 완료되었습니다.")
                self._show_messagebox("완료", f"{task_name} 작업이 완료되었습니다!", "check")
            except Exception as e:
                print(f"[오류] {task_name} 실패: {e}")
                self._show_messagebox("오류", f"작업 중 오류가 발생했습니다.\n{e}", "cancel")
            finally:
                try:
                    self.after(0, lambda: self.step_label.configure(text=""))
                    self.after(0, lambda: self._set_buttons_state("normal"))  # 메인 스레드로 복원 위임
                except Exception:
                    pass  # 창이 이미 종료된 경우 TclError 방어
        thread = threading.Thread(target=wrapper, daemon=True)
        thread.start()

    def run_onestop_teacher(self):
        """담임용 원스톱 자동화 - 단일 학급"""
        folder = self.select_download_folder()
        if not folder: return
        self.backup_files(folder)
        self.save_menus()
        start, end, month = self.get_period()
        class_num = self.class_number.get()
        
        menu_abs = self.get_menu_dict(self.absence_vars)
        menu_tard = self.get_menu_dict(self.tardiness_vars)
        menu_mon = self.get_menu_dict(self.monthly_vars)
        
        def task():
            # 단일 학급 모드로 실행 (config.class_count = 1로 설정)
            import btn_commands as cmd
            original_class_count = getattr(config, 'class_count', 12)
            config.class_count = 1  # 단일 학급

            print(f"[정보] {class_num}반 출결 자동화를 시작합니다.")

            self.after(0, lambda: self.step_label.configure(text="[1/5] 나이스 로그인 중..."))
            open_neis()

            self.after(0, lambda: self.step_label.configure(text="[2/5] 결석 신고서 다운로드 중..."))
            neis_attendace_v2(start, end, download_dir=folder, skip_open=True, skip_click=True, menu=menu_abs)

            self.after(0, lambda: self.step_label.configure(text="[3/5] 지각·조퇴 신고서 다운로드 중..."))
            download_tardiness_report_v2(start, end, download_dir=folder, skip_open=True, skip_click=True, menu=menu_tard)

            self.after(0, lambda: self.step_label.configure(text="[4/5] 월별 출결 다운로드 중..."))
            download_monthly_attendance(month, download_dir=folder, skip_open=True, skip_click=True, menu=menu_mon)

            self.after(0, lambda: self.step_label.configure(text="[5/5] 엑셀 처리 중..."))
            self.run_excel_macro_direct(folder)

            config.class_count = original_class_count
            
        self.run_worker(task, f"{class_num}반 원스톱 자동화")

    def run_download_reports(self):
        """신고서만 다운로드"""
        folder = self.select_download_folder()
        if not folder: return
        start_date, end_date, _ = self.get_period()
        self.save_menus()
        menu_abs = self.get_menu_dict(self.absence_vars)
        menu_tard = self.get_menu_dict(self.tardiness_vars)
        def task():
            self.after(0, lambda: self.step_label.configure(text="[1/3] 나이스 로그인 중..."))
            open_neis()
            self.after(0, lambda: self.step_label.configure(text="[2/3] 결석 신고서 다운로드 중..."))
            neis_attendace_v2(start_date, end_date, download_dir=folder, skip_open=True, skip_click=True, menu=menu_abs)
            self.after(0, lambda: self.step_label.configure(text="[3/3] 지각·조퇴 신고서 다운로드 중..."))
            download_tardiness_report_v2(start_date, end_date, download_dir=folder, skip_open=True, skip_click=True, menu=menu_tard)
        self.run_worker(task, "신고서 다운로드")

    def run_download_monthly(self):
        """월별 출결현황만 다운로드"""
        folder = self.select_download_folder()
        if not folder: return
        _, _, month_str = self.get_period()
        self.save_menus()
        menu = self.get_menu_dict(self.monthly_vars)
        def task():
            self.after(0, lambda: self.step_label.configure(text="[1/2] 나이스 로그인 중..."))
            open_neis()
            self.after(0, lambda: self.step_label.configure(text="[2/2] 월별 출결 다운로드 중..."))
            download_monthly_attendance(month_str, download_dir=folder, skip_open=True, skip_click=True, menu=menu)
        self.run_worker(task, "월별 출결현황 다운로드")

    def run_only_excel_macro(self):
        """엑셀 자동화만 실행"""
        folder = self.select_download_folder()
        if not folder: return
        def task():
            self.after(0, lambda: self.step_label.configure(text="[1/1] 엑셀 처리 중..."))
            self.run_excel_macro_direct(folder)
        self.run_worker(task, "엑셀 자동화")

    def backup_files(self, folder):
        backup_folder = os.path.join(folder, "backup")
        if not os.path.exists(backup_folder):
            os.makedirs(backup_folder)
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            if os.path.isfile(file_path) and filename != "backup":
                try:
                    shutil.move(file_path, os.path.join(backup_folder, filename))
                except Exception as e:
                    logger.warning(f"파일 백업 실패 ({filename}): {e}")

    def run_excel_macro_direct(self, folder_path):
        if not folder_path.endswith("\\"): folder_path += "\\"
        pythoncom.CoInitialize()
        try:
            excel = win32com.client.Dispatch("Excel.Application")
            excel.Visible = True
            excel.Application.AutomationSecurity = 1  # msoAutomationSecurityLow: 매크로 차단 경고 없이 실행
            wb = excel.Workbooks.Open(os.path.abspath(EXCEL_FILE))
            excel.Application.Run("Module1.Run_All_Processes", folder_path)
            wb = None
            excel = None
        finally:
            pythoncom.CoUninitialize()
    
    def open_local_excel(self):
        if os.path.exists(EXCEL_FILE):
            os.startfile(EXCEL_FILE)
        else:
            CTkMessagebox(title="오류", message="엑셀 파일이 없습니다.", icon="warning")

if __name__ == "__main__":
    app = App()
    app.mainloop()

