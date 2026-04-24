from __future__ import annotations

import threading
from datetime import date as date_type, datetime

import customtkinter as ctk
from CTkMessagebox import CTkMessagebox

from subject_teacher.app_service import prepare_run_context, run_day
from subject_teacher.auth.google_oauth import authorize_interactive
from subject_teacher.scripts.seed_sample import main as seed_sample_main
from subject_teacher.state import build_store, load_local_password, save_local_password, summarize_day


class RunTab(ctk.CTkFrame):
    def __init__(
        self,
        master,
        app,
        colors: dict[str, str],
        main_font: tuple[str, int],
        bold_font: tuple[str, int, str],
    ):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.colors = colors
        self.main_font = main_font
        self.bold_font = bold_font

        self.date_var = ctk.StringVar(value=date_type.today().isoformat())
        self.password_var = ctk.StringVar(value=load_local_password())
        self.close_var = ctk.BooleanVar(value=True)

        self.run_button: ctk.CTkButton | None = None
        self.rail_status_label: ctk.CTkLabel | None = None
        self.summary_rows_frame: ctk.CTkScrollableFrame | None = None
        self.metric_value_labels: dict[str, ctk.CTkLabel] = {}
        self.metric_note_labels: dict[str, ctk.CTkLabel] = {}
        self.nav_buttons: dict[str, ctk.CTkButton] = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build()

    def _build(self) -> None:
        shell = self._window_shell(self)
        shell.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")
        shell.grid_columnconfigure(1, weight=1)
        shell.grid_rowconfigure(0, weight=1)

        self._build_side_rail(shell)
        self._build_main(shell)
        self._set_active_nav("실행")
        self.refresh_summary()

    def _build_side_rail(self, parent) -> None:
        rail = ctk.CTkFrame(parent, fg_color="#fbfbfc", corner_radius=0, width=178)
        rail.grid(row=0, column=0, sticky="nsw")
        rail.grid_propagate(False)
        rail.grid_columnconfigure(0, weight=1)
        rail.grid_rowconfigure(5, weight=1)

        ctk.CTkLabel(
            rail,
            text="작업",
            font=("Noto Sans KR", 12, "bold"),
            text_color=self.colors["base00"],
        ).grid(row=0, column=0, padx=18, pady=(22, 10), sticky="w")

        nav = ctk.CTkFrame(rail, fg_color="transparent")
        nav.grid(row=1, column=0, padx=12, sticky="ew")
        nav.grid_columnconfigure(0, weight=1)

        for row, name in enumerate(("설정", "실행")):
            button = self._rail_button(nav, name, lambda tab=name: self._navigate_to_tab(tab))
            button.grid(row=row, column=0, pady=4, sticky="ew")
            self.nav_buttons[name] = button

        divider = ctk.CTkFrame(rail, fg_color=self.colors["line"], height=1)
        divider.grid(row=2, column=0, padx=18, pady=18, sticky="ew")

        actions = ctk.CTkFrame(rail, fg_color="transparent")
        actions.grid(row=3, column=0, padx=12, sticky="ew")
        actions.grid_columnconfigure(0, weight=1)
        self._secondary_button(actions, "Google Drive", self.refresh_summary).grid(row=0, column=0, pady=4, sticky="ew")
        self._secondary_button(actions, "OAuth 재인증", self.run_authorize).grid(row=1, column=0, pady=4, sticky="ew")
        self._secondary_button(actions, "샘플 데이터", self.seed_sample).grid(row=2, column=0, pady=4, sticky="ew")

        footer = ctk.CTkFrame(rail, fg_color="transparent")
        footer.grid(row=5, column=0, padx=18, pady=18, sticky="sew")
        footer.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            footer,
            text="v1.0.0",
            font=("Noto Sans KR", 11),
            text_color=self.colors["base00"],
        ).grid(row=0, column=0, sticky="w")
        self.rail_status_label = ctk.CTkLabel(
            footer,
            text="연결 확인 전",
            font=("Noto Sans KR", 12),
            text_color=self.colors["base00"],
        )
        self.rail_status_label.grid(row=1, column=0, pady=(8, 0), sticky="w")

    def _build_main(self, parent) -> None:
        main = ctk.CTkFrame(parent, fg_color="transparent")
        main.grid(row=0, column=1, padx=24, pady=24, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(3, weight=1)

        self._build_header(main)
        self._build_control_row(main)
        self._build_metrics(main)
        self._build_summary_board(main)

    def _build_header(self, parent) -> None:
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=0)

        intro = ctk.CTkFrame(header, fg_color="transparent")
        intro.grid(row=0, column=0, sticky="w")
        intro.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            intro,
            text="실행",
            font=("Noto Sans KR", 31, "bold"),
            text_color=self.colors["base03"],
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            intro,
            text="오늘의 수업을 확인하고 Drive 기록을 NEIS에 반영합니다.",
            font=("Noto Sans KR", 13),
            text_color=self.colors["base00"],
        ).grid(row=1, column=0, pady=(5, 0), sticky="w")

        utilities = ctk.CTkFrame(header, fg_color="transparent")
        utilities.grid(row=0, column=1, rowspan=2, sticky="e")
        utilities.grid_columnconfigure((0, 1), weight=1)
        self._secondary_button(utilities, "오늘 새로고침", self.refresh_summary).grid(row=0, column=0, padx=(0, 8), sticky="ew")
        self._secondary_button(utilities, "샘플 데이터", self.seed_sample).grid(row=0, column=1, sticky="ew")

    def _build_control_row(self, parent) -> None:
        controls = self._card(parent)
        controls.grid(row=1, column=0, pady=(18, 16), sticky="ew")
        controls.grid_columnconfigure((0, 1), weight=1)

        self._field_label(controls, "날짜 선택", 0, 0)
        self._field_label(controls, "교사 비밀번호", 0, 1)
        self._entry(controls, self.date_var).grid(row=1, column=0, padx=(18, 10), pady=(0, 12), sticky="ew")
        self._entry(controls, self.password_var, show="*").grid(row=1, column=1, padx=(10, 18), pady=(0, 12), sticky="ew")

        ctk.CTkCheckBox(
            controls,
            text="출결마감까지 자동 실행",
            variable=self.close_var,
            font=("Noto Sans KR", 12),
            text_color=self.colors["base01"],
            fg_color=self.colors["blue"],
            hover_color="#0066cc",
            checkmark_color=self.colors["base2"],
        ).grid(row=2, column=0, columnspan=2, padx=18, pady=(0, 14), sticky="w")

    def _build_metrics(self, parent) -> None:
        metrics = ctk.CTkFrame(parent, fg_color="transparent")
        metrics.grid(row=2, column=0, pady=(0, 16), sticky="ew")
        for col in range(4):
            metrics.grid_columnconfigure(col, weight=1)

        cards = [
            ("연결 상태", "연결 확인 전", "Google Drive"),
            ("오늘 수업", "0건", "표시된 수업"),
            ("NEIS 반영", "0건", "미반영 0건"),
            ("마지막 동기화", "--:--", "새로고침 기준"),
        ]
        for idx, (title, value, note) in enumerate(cards):
            card = self._card(metrics)
            card.grid(row=0, column=idx, padx=(0 if idx == 0 else 10, 0), sticky="ew")
            ctk.CTkLabel(
                card,
                text=title,
                font=("Noto Sans KR", 12, "bold"),
                text_color=self.colors["base01"],
            ).pack(anchor="w", padx=16, pady=(15, 8))
            value_label = ctk.CTkLabel(
                card,
                text=value,
                font=("Noto Sans KR", 24, "bold"),
                text_color=self.colors["base03"],
            )
            value_label.pack(anchor="w", padx=16)
            note_label = ctk.CTkLabel(
                card,
                text=note,
                font=("Noto Sans KR", 11),
                text_color=self.colors["base00"],
            )
            note_label.pack(anchor="w", padx=16, pady=(4, 15))
            self.metric_value_labels[title] = value_label
            self.metric_note_labels[title] = note_label

    def _build_summary_board(self, parent) -> None:
        board = self._card(parent)
        board.grid(row=3, column=0, sticky="nsew")
        board.grid_columnconfigure(0, weight=1)
        board.grid_rowconfigure(1, weight=1)
        board.grid_rowconfigure(2, weight=0)

        header = ctk.CTkFrame(board, fg_color="transparent")
        header.grid(row=0, column=0, padx=20, pady=(20, 12), sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="오늘 수업",
            font=("Noto Sans KR", 22, "bold"),
            text_color=self.colors["base03"],
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="Drive에 저장된 출결 상태를 확인한 뒤 NEIS 반영을 실행하세요.",
            font=("Noto Sans KR", 12),
            text_color=self.colors["base00"],
        ).grid(row=1, column=0, pady=(4, 0), sticky="w")

        self.summary_rows_frame = ctk.CTkScrollableFrame(
            board,
            fg_color="#fbfbfc",
            corner_radius=16,
            border_width=1,
            border_color=self.colors["line"],
        )
        self.summary_rows_frame.grid(row=1, column=0, padx=20, pady=(0, 18), sticky="nsew")
        self.summary_rows_frame.grid_columnconfigure(0, weight=1)

        footer = ctk.CTkFrame(board, fg_color="transparent")
        footer.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="ew")
        footer.grid_columnconfigure(0, weight=1)
        self.run_button = ctk.CTkButton(
            footer,
            text="NEIS 반영 실행",
            command=self.run_sync,
            font=("Noto Sans KR", 18, "bold"),
            height=54,
            corner_radius=12,
            fg_color=self.colors["blue"],
            hover_color="#0066cc",
            text_color=self.colors["base2"],
        )
        self.run_button.grid(row=0, column=0, sticky="ew")

    def _render_summary_rows(self, items) -> None:
        if self.summary_rows_frame is None:
            return

        for child in self.summary_rows_frame.winfo_children():
            child.destroy()

        if not items:
            ctk.CTkLabel(
                self.summary_rows_frame,
                text="해당 날짜에 표시할 수업이 없습니다.",
                font=("Noto Sans KR", 13),
                text_color=self.colors["base00"],
            ).pack(padx=12, pady=22)
            return

        header = ctk.CTkFrame(self.summary_rows_frame, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(14, 8))
        columns = [
            ("교시", 10),
            ("과목", 24),
            ("학년", 10),
            ("반", 10),
            ("체크", 12),
            ("결석", 12),
            ("상태", 18),
        ]
        for idx, (name, weight) in enumerate(columns):
            header.grid_columnconfigure(idx, weight=weight)
            ctk.CTkLabel(
                header,
                text=name,
                font=("Noto Sans KR", 12, "bold"),
                text_color=self.colors["base00"],
            ).grid(row=0, column=idx, sticky="w")

        for item in items:
            row = ctk.CTkFrame(
                self.summary_rows_frame,
                fg_color="#ffffff",
                corner_radius=14,
                border_width=1,
                border_color=self.colors["line"],
            )
            row.pack(fill="x", padx=12, pady=6)

            values = [
                f"{item.period}교시",
                item.subject_name,
                str(item.grade),
                str(item.class_no),
                "완료" if item.checked else "대기",
                f"{item.absence_count}명",
            ]
            for idx, (_, weight) in enumerate(columns):
                row.grid_columnconfigure(idx, weight=weight)

            for idx, text in enumerate(values):
                ctk.CTkLabel(
                    row,
                    text=text,
                    font=("Noto Sans KR", 13),
                    text_color=self.colors["base01"],
                ).grid(row=0, column=idx, padx=14, pady=14, sticky="w")

            status_text = "마감 완료" if item.closed_on_neis else "반영 완료" if item.synced_to_neis else "미반영"
            self._status_chip(row, status_text).grid(row=0, column=len(values), padx=14, pady=10, sticky="w")

    def _update_metrics(self, items) -> None:
        total = len(items)
        synced = sum(1 for item in items if item.synced_to_neis)
        pending = total - synced

        self.metric_value_labels["연결 상태"].configure(text="연결됨", text_color=self.colors["success"])
        self.metric_note_labels["연결 상태"].configure(text="Google Drive", text_color=self.colors["base00"])
        self.metric_value_labels["오늘 수업"].configure(text=f"{total}건", text_color=self.colors["blue"])
        self.metric_note_labels["오늘 수업"].configure(text="표시된 수업", text_color=self.colors["base00"])
        self.metric_value_labels["NEIS 반영"].configure(text=f"{synced}건", text_color=self.colors["blue"])
        self.metric_note_labels["NEIS 반영"].configure(text=f"미반영 {pending}건", text_color=self.colors["base00"])
        self._mark_last_sync(success=True)

        if self.rail_status_label is not None:
            self.rail_status_label.configure(text="연결됨", text_color=self.colors["success"])

    def refresh_summary(self) -> None:
        try:
            store = build_store()
            items = summarize_day(store, self.date_var.get().strip())
            self._update_metrics(items)
            self._render_summary_rows(items)
        except Exception as exc:
            self.metric_value_labels["연결 상태"].configure(text="오류", text_color="#ff3b30")
            self.metric_note_labels["연결 상태"].configure(text="요약 불러오기 실패", text_color="#ff3b30")
            self._mark_last_sync(success=False)
            if self.rail_status_label is not None:
                self.rail_status_label.configure(text="오류", text_color="#ff3b30")

            self._render_summary_rows([])
            if self.summary_rows_frame is not None:
                ctk.CTkLabel(
                    self.summary_rows_frame,
                    text=f"요약 불러오기 실패: {exc}",
                    font=("Noto Sans KR", 12),
                    text_color="#ff3b30",
                ).pack(padx=12, pady=(0, 14))

    def run_authorize(self) -> None:
        try:
            authorize_interactive()
            self.app.write_log("OAuth 재인증 완료")
            self.refresh_summary()
        except Exception as exc:
            CTkMessagebox(title="OAuth 실패", message=str(exc), icon="cancel")

    def seed_sample(self) -> None:
        try:
            seed_sample_main()
            self.app.write_log("샘플 데이터 시드 완료")
            self.refresh_summary()
        except SystemExit:
            self.refresh_summary()
        except Exception as exc:
            CTkMessagebox(title="샘플 데이터 실패", message=str(exc), icon="cancel")

    def run_sync(self) -> None:
        password = self.password_var.get()
        if not password:
            CTkMessagebox(title="입력 필요", message="인증서 비밀번호를 입력하세요.", icon="warning")
            return

        save_local_password(password)
        if self.run_button:
            self.run_button.configure(state="disabled", text="실행 중...")

        def worker():
            try:
                context = prepare_run_context(self.date_var.get().strip())
                self.app.write_log(f"실행 대상: {[slot.id for slot, _ in context.day_input.slots]}")
                results = run_day(
                    date_str=self.date_var.get().strip(),
                    password=password,
                    close_after=self.close_var.get(),
                )
                ok = sum(1 for item in results if item.status == "ok")
                failed = [item for item in results if item.status == "failed"]
                self.app.write_log(f"실행 결과: OK={ok} FAILED={len(failed)}")
                for item in failed:
                    self.app.write_log(f"  - {item.slot_id}: {item.error}")
                self.after(0, self.refresh_summary)
            except Exception as exc:
                self.app.write_log(f"실행 실패: {exc}")
                self.after(0, lambda: CTkMessagebox(title="실행 실패", message=str(exc), icon="cancel"))
            finally:
                if self.run_button:
                    self.after(0, lambda: self.run_button.configure(state="normal", text="NEIS 반영 실행"))

        threading.Thread(target=worker, daemon=True).start()

    def _window_shell(self, parent) -> ctk.CTkFrame:
        return ctk.CTkFrame(
            parent,
            fg_color=self.colors["base2"],
            corner_radius=18,
            border_width=1,
            border_color=self.colors["line"],
        )

    def _card(self, parent) -> ctk.CTkFrame:
        return ctk.CTkFrame(
            parent,
            fg_color=self.colors["base2"],
            corner_radius=18,
            border_width=1,
            border_color=self.colors["line"],
        )

    def _field_label(self, parent, text: str, row: int, column: int) -> None:
        ctk.CTkLabel(
            parent,
            text=text,
            font=("Noto Sans KR", 12, "bold"),
            text_color=self.colors["base01"],
        ).grid(row=row, column=column, padx=(18 if column == 0 else 10, 18), pady=(16, 8), sticky="w")

    def _entry(self, parent, variable, show: str | None = None) -> ctk.CTkEntry:
        return ctk.CTkEntry(
            parent,
            textvariable=variable,
            show=show,
            font=self.main_font,
            height=42,
            fg_color="#ffffff",
            border_color=self.colors["line"],
            text_color=self.colors["base03"],
        )

    def _rail_button(self, parent, text: str, command) -> ctk.CTkButton:
        return ctk.CTkButton(
            parent,
            text=f"  {text}",
            command=command,
            fg_color="transparent",
            hover_color="#eef4ff",
            text_color=self.colors["base01"],
            anchor="w",
            height=40,
            corner_radius=12,
            font=("Noto Sans KR", 14, "bold"),
        )

    def _secondary_button(self, parent, text: str, command) -> ctk.CTkButton:
        return ctk.CTkButton(
            parent,
            text=text,
            command=command,
            font=("Noto Sans KR", 12),
            height=36,
            corner_radius=12,
            fg_color="transparent",
            hover_color=self.colors["surface_alt"],
            border_width=0,
            text_color=self.colors["base01"],
            anchor="w",
        )

    def _status_chip(self, parent, text: str) -> ctk.CTkLabel:
        return ctk.CTkLabel(
            parent,
            text=text,
            font=("Noto Sans KR", 11, "bold"),
            text_color=self._neis_color(text),
            fg_color="#f3f5f7",
            corner_radius=999,
            padx=12,
            pady=5,
        )

    def _navigate_to_tab(self, name: str) -> None:
        self._set_active_nav(name)
        if hasattr(self.app, "select_tab"):
            self.app.select_tab(name)

    def _set_active_nav(self, name: str) -> None:
        for label, button in self.nav_buttons.items():
            active = label == name
            button.configure(
                fg_color="#eef4ff" if active else "transparent",
                hover_color="#eef4ff",
                text_color=self.colors["blue"] if active else self.colors["base01"],
            )

    def _mark_last_sync(self, success: bool) -> None:
        timestamp = datetime.now().strftime("%Y.%m.%d %H:%M")
        self.metric_value_labels["마지막 동기화"].configure(text=timestamp, text_color=self.colors["base03"])
        self.metric_note_labels["마지막 동기화"].configure(
            text="성공" if success else "실패",
            text_color=self.colors["success"] if success else "#ff3b30",
        )

    def _neis_color(self, text: str) -> str:
        if text == "마감 완료":
            return self.colors["success"]
        if text == "반영 완료":
            return self.colors["blue"]
        return self.colors["base01"]
