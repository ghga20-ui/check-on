from __future__ import annotations

import customtkinter as ctk

from logger_config import logger
from subject_teacher.gui.log_panel import LogPanel
from subject_teacher.gui.run_tab import RunTab
from subject_teacher.gui.setup_tab import SetupTab


APPLE_COLORS = {
    "base03": "#000000",
    "base02": "#1d1d1f",
    "base01": "#2c2c2e",
    "base00": "#6e6e73",
    "base0": "#86868b",
    "base1": "#d2d2d7",
    "base2": "#ffffff",
    "base3": "#f5f5f7",
    "blue": "#0071e3",
    "cyan": "#2997ff",
    "line": "#e5e5ea",
    "surface": "#fbfbfd",
    "surface_alt": "#f0f2f5",
    "success": "#34c759",
}

ctk.set_appearance_mode("Light")


class SubjectTeacherApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("나이스 출결관리 프로 - 교과교사용")
        self.geometry("1360x920")
        self.minsize(1220, 840)
        self.configure(fg_color=APPLE_COLORS["base3"])

        self.main_font = ("Noto Sans KR", 14)
        self.bold_font = ("Noto Sans KR", 14, "bold")
        self.header_font = ("Noto Sans KR", 40, "bold")
        self.section_font = ("Noto Sans KR", 24, "bold")
        self.tabview: ctk.CTkTabview | None = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_tabs()
        self._build_log_panel()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_header(self) -> None:
        header = ctk.CTkFrame(
            self,
            fg_color=APPLE_COLORS["base2"],
            corner_radius=28,
            border_width=1,
            border_color=APPLE_COLORS["line"],
        )
        header.grid(row=0, column=0, padx=24, pady=(22, 14), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        hero = ctk.CTkFrame(header, fg_color="transparent")
        hero.grid(row=0, column=0, padx=28, pady=(24, 18), sticky="ew")
        hero.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hero,
            text="나이스 출결관리 프로",
            font=self.header_font,
            text_color=APPLE_COLORS["base03"],
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            hero,
            text="교과교사용",
            font=("Noto Sans KR", 18),
            text_color=APPLE_COLORS["base00"],
        ).grid(row=1, column=0, pady=(4, 0), sticky="w")
        ctk.CTkLabel(
            hero,
            text="오늘 수업을 확인하고 Drive 데이터로 NEIS 출결을 차분하게 반영하세요.",
            font=("Noto Sans KR", 14),
            text_color=APPLE_COLORS["base00"],
        ).grid(row=2, column=0, pady=(14, 0), sticky="w")

        pill = ctk.CTkFrame(
            hero,
            fg_color=APPLE_COLORS["base03"],
            corner_radius=999,
        )
        pill.grid(row=0, column=1, rowspan=3, padx=(20, 0), sticky="e")
        ctk.CTkLabel(
            pill,
            text="실행 우선 워크플로우",
            font=("Noto Sans KR", 12),
            text_color=APPLE_COLORS["base2"],
        ).pack(padx=16, pady=8)

    def _build_tabs(self) -> None:
        tabview = ctk.CTkTabview(
            self,
            fg_color=APPLE_COLORS["base2"],
            segmented_button_fg_color=APPLE_COLORS["surface_alt"],
            segmented_button_selected_color=APPLE_COLORS["base03"],
            segmented_button_selected_hover_color=APPLE_COLORS["base01"],
            segmented_button_unselected_color=APPLE_COLORS["surface_alt"],
            segmented_button_unselected_hover_color=APPLE_COLORS["line"],
            text_color=APPLE_COLORS["base2"],
            text_color_disabled=APPLE_COLORS["base1"],
            corner_radius=28,
            border_width=1,
            border_color=APPLE_COLORS["line"],
        )
        tabview.grid(row=1, column=0, padx=24, pady=(0, 14), sticky="nsew")
        tabview._segmented_button.configure(font=("Noto Sans KR", 13, "bold"))
        self.tabview = tabview

        tabview.add("실행")
        tabview.add("설정")

        self.run_tab = RunTab(tabview.tab("실행"), self, APPLE_COLORS, self.main_font, self.bold_font)
        self.run_tab.pack(fill="both", expand=True, padx=4, pady=4)

        self.setup_tab = SetupTab(tabview.tab("설정"), self, APPLE_COLORS, self.main_font, self.bold_font)
        self.setup_tab.pack(fill="both", expand=True, padx=4, pady=4)

        tabview.set("실행")
        tabview._segmented_button.grid_remove()

    def select_tab(self, name: str) -> None:
        if self.tabview is not None:
            self.tabview.set(name)

    def current_tab(self) -> str:
        if self.tabview is None:
            return "실행"
        return str(self.tabview.get())

    def _build_log_panel(self) -> None:
        wrapper = ctk.CTkFrame(
            self,
            fg_color=APPLE_COLORS["base02"],
            corner_radius=24,
            border_width=1,
            border_color="#2f2f33",
        )
        wrapper.grid(row=2, column=0, padx=24, pady=(0, 22), sticky="ew")
        wrapper.grid_rowconfigure(1, weight=1)
        wrapper.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(wrapper, fg_color="transparent")
        header.grid(row=0, column=0, padx=20, pady=(16, 10), sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="실행 로그",
            font=("Noto Sans KR", 14, "bold"),
            text_color=APPLE_COLORS["base2"],
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="동기화와 저장 결과를 이곳에서 확인합니다.",
            font=("Noto Sans KR", 12),
            text_color=APPLE_COLORS["base1"],
        ).grid(row=1, column=0, pady=(2, 0), sticky="w")

        self.log_panel = LogPanel(wrapper, self.main_font, APPLE_COLORS)
        self.log_panel.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="ew")
        self.log_panel.attach(logger)

    def write_log(self, text: str) -> None:
        self.log_panel.write_line(text)

    def _on_close(self) -> None:
        try:
            self.log_panel.detach(logger)
        finally:
            self.destroy()
