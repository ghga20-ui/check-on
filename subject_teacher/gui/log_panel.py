from __future__ import annotations

import logging
import queue
import sys

import customtkinter as ctk


class TextRedirector:
    def __init__(self, output_queue: queue.Queue[str]):
        self.output_queue = output_queue

    def write(self, text: str) -> None:
        if text:
            self.output_queue.put(text)

    def flush(self) -> None:
        return


class QueueLogHandler(logging.Handler):
    def __init__(self, output_queue: queue.Queue[str]):
        super().__init__()
        self.output_queue = output_queue

    def emit(self, record: logging.LogRecord) -> None:
        self.output_queue.put(self.format(record) + "\n")


class LogPanel(ctk.CTkFrame):
    def __init__(self, master, font: tuple[str, int], colors: dict[str, str]):
        super().__init__(master, fg_color=colors["base01"], corner_radius=18)
        self.colors = colors
        self.output_queue: queue.Queue[str] = queue.Queue()
        self.textbox = ctk.CTkTextbox(
            self,
            height=150,
            fg_color=colors["base01"],
            text_color=colors["base2"],
            font=(font[0], 12),
            border_width=0,
            corner_radius=14,
        )
        self.textbox.pack(fill="both", expand=True, padx=12, pady=12)
        self.textbox.configure(state="disabled")
        self._redirector = TextRedirector(self.output_queue)
        self._previous_stdout = None
        self._handler: QueueLogHandler | None = None
        self.after(100, self._drain_queue)

    def attach(self, logger: logging.Logger) -> None:
        if self._handler is not None:
            return
        self._handler = QueueLogHandler(self.output_queue)
        self._handler.setFormatter(
            logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
        )
        logger.addHandler(self._handler)
        root_logger = logging.getLogger()
        root_logger.addHandler(self._handler)
        self._previous_stdout = sys.stdout
        sys.stdout = self._redirector

    def detach(self, logger: logging.Logger) -> None:
        if self._handler is None:
            return
        logger.removeHandler(self._handler)
        logging.getLogger().removeHandler(self._handler)
        if self._previous_stdout is not None:
            sys.stdout = self._previous_stdout
            self._previous_stdout = None
        self._handler = None

    def write_line(self, text: str) -> None:
        self.output_queue.put(text.rstrip("\n") + "\n")

    def _drain_queue(self) -> None:
        try:
            while True:
                message = self.output_queue.get_nowait()
                self.textbox.configure(state="normal")
                self.textbox.insert("end", message)
                self.textbox.see("end")
                self.textbox.configure(state="disabled")
        except queue.Empty:
            pass
        finally:
            self.after(100, self._drain_queue)
