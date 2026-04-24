"""Low-level Selenium helpers for NEIS subject attendance screens."""
from __future__ import annotations

import json
import time
from typing import Iterable

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import utils

MENU_PATH = [
    "\uad50\uacfc\ub2f4\uc784",
    "\ud559\uc801",
    "\ucd9c\uacb0\uad00\ub9ac",
]

SIDE_MENU_LABEL = "\uacfc\ubaa9\ubcc4\ucd9c\uacb0\uad00\ub9ac"

SEL: dict[str, str] = {
    "radio_day_mode": "//div[@data-role='radio' and @data-value='1']",
    "radio_subject_mode": "//div[@data-role='radio' and @data-value='2']",
    "input_date": "//input[@aria-label='\uc77c\uc790']",
    "left_panel_period_row": "//*[contains(@aria-label, '\uad50\uc2dc {period}')]",
    "excused_checkbox": "//div[@data-role='checkbox' and @role='checkbox']",
    "student_row_by_number": "//table[contains(@class,'attend-grid')]//tr[td[normalize-space()='{number}']]",
    "cell_status_in_row": ".//td[contains(@class,'status')]//input",
    "cell_note_in_row": ".//td[contains(@class,'note')]//input",
}


def build_student_row_xpath(student_number: int) -> str:
    return (
        f"//div[@role='row'][.//div[@data-cellindex='4' and .//div[normalize-space()='{student_number}']]]"
    )


def build_status_cell_xpath(student_number: int) -> str:
    row_xpath = build_student_row_xpath(student_number)
    return (
        f"{row_xpath}//div[@role='gridcell' and (@data-cellindex='7' or @data-cellindex='8' or @data-cellindex='9')][1]"
    )


def build_note_input_xpath(student_number: int) -> str:
    row_xpath = build_student_row_xpath(student_number)
    return f"{row_xpath}//div[@role='gridcell' and @data-cellindex='12']//input"


def build_side_menu_xpath() -> str:
    label = SIDE_MENU_LABEL
    return (
        f"//a[contains(@class,'cl-sidenavigation-item') and contains(normalize-space(.), '{label}')]"
        f"|//div[contains(@class,'cl-sidenavigation-item') and contains(normalize-space(.), '{label}')]"
    )


def build_button_xpath(label: str) -> str:
    return (
        f"//div[@role='button' and @aria-label='{label}']"
        f"|//a[contains(@class,'cl-text-wrapper')][.//div[contains(@class,'cl-text') and normalize-space()='{label}']]"
        f"|//div[contains(@class,'cl-button') and .//div[contains(@class,'cl-text') and normalize-space()='{label}']]"
    )


def normalize_neis_date(date_str: str) -> str:
    return date_str.replace("-", ".")


def combo_already_selected(aria_labels: Iterable[str], label_text: str, option_text: str) -> bool:
    expected = f"{label_text}, {option_text}"
    return any((label or "").strip() == expected for label in aria_labels)


def _wait(driver: WebDriver, timeout: float = 10.0) -> WebDriverWait:
    return WebDriverWait(driver, timeout)


def open_subject_attendance_page(driver: WebDriver, year: int, term: int) -> None:
    utils.neis_go_menu(driver, *MENU_PATH)
    side_menu = _wait(driver, 15).until(
        EC.element_to_be_clickable((By.XPATH, build_side_menu_xpath()))
    )
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", side_menu)
    driver.execute_script("arguments[0].click();", side_menu)

    # The page defaults to the active school year/term and the legacy combobox helper
    # is brittle against duplicate hidden controls. For the current workflow we rely on
    # the already-selected values and only automate date/mode/period interactions.


def select_day_mode(driver: WebDriver) -> None:
    _wait(driver).until(EC.element_to_be_clickable((By.XPATH, SEL["radio_day_mode"]))).click()


def select_date(driver: WebDriver, date_str: str) -> None:
    date_input = _wait(driver).until(EC.presence_of_element_located((By.XPATH, SEL["input_date"])))
    date_input.clear()
    date_input.send_keys(normalize_neis_date(date_str))


def click_search(driver: WebDriver) -> None:
    button = _wait(driver).until(EC.presence_of_element_located((By.XPATH, build_button_xpath("\uc870\ud68c"))))
    driver.execute_script("arguments[0].click();", button)


def page_has_period_rows(driver: WebDriver) -> bool:
    return bool(driver.find_elements(By.XPATH, "//*[contains(@aria-label, '행 교시') or contains(normalize-space(.), '교시')]"))


def select_period(driver: WebDriver, period: int) -> None:
    xpath = SEL["left_panel_period_row"].format(period=period)
    _wait(driver).until(EC.element_to_be_clickable((By.XPATH, xpath))).click()


def ensure_excused_mode(driver: WebDriver, on: bool) -> None:
    checkboxes = driver.find_elements(By.XPATH, SEL["excused_checkbox"])
    if not checkboxes:
        if on:
            raise RuntimeError("excused checkbox not found")
        return

    checkbox = checkboxes[0]
    if checkbox.is_selected() != on:
        driver.execute_script("arguments[0].click();", checkbox)
        time.sleep(0.2)


def click_reset(driver: WebDriver) -> None:
    button = _wait(driver).until(EC.presence_of_element_located((By.XPATH, build_button_xpath("\ucd08\uae30\ud654"))))
    driver.execute_script("arguments[0].click();", button)


def click_attendance_cell(driver: WebDriver, student_number: int) -> None:
    try:
        cell = _wait(driver).until(EC.presence_of_element_located((By.XPATH, build_status_cell_xpath(student_number))))
        driver.execute_script("arguments[0].click();", cell)
        return
    except Exception:
        pass

    script = """
    const studentNumber = String(arguments[0]);
    const candidates = Array.from(document.querySelectorAll('*')).filter((el) => {
      const text = (el.innerText || '').trim();
      const aria = el.getAttribute('aria-label') || '';
      const compact = text.replace(/\\s+/g, ' ').trim();
      const isShort = compact.length > 0 && compact.length <= 20;
      return (
        text === studentNumber ||
        (isShort && compact.split(' ').includes(studentNumber)) ||
        aria.includes(`번호 ${studentNumber}`) ||
        aria.endsWith(` ${studentNumber}`)
      );
    });
    candidates.sort((a, b) => {
      const ra = a.getBoundingClientRect();
      const rb = b.getBoundingClientRect();
      return (ra.width * ra.height) - (rb.width * rb.height);
    });
    for (const el of candidates) {
      const rect = el.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) continue;
      const x = rect.left + 380;
      const y = rect.top + rect.height / 2;
      const target = document.elementFromPoint(x, y);
      if (target) {
        target.click();
        return true;
      }
    }
    return false;
    """
    if not driver.execute_script(script, student_number):
        debug_script = """
        const studentNumber = String(arguments[0]);
        const out = [];
        for (const el of Array.from(document.querySelectorAll('*'))) {
          const text = (el.innerText || '').trim();
          const aria = el.getAttribute('aria-label') || '';
          if (text.includes(studentNumber) || aria.includes(studentNumber)) {
            const rect = el.getBoundingClientRect();
            out.push({
              tag: el.tagName,
              cls: el.className,
              role: el.getAttribute('role'),
              aria,
              text,
              x: rect.left,
              y: rect.top,
              w: rect.width,
              h: rect.height,
              html: (el.outerHTML || '').slice(0, 500),
            });
          }
        }
        return out;
        """
        with open("tmp_student_candidates.json", "w", encoding="utf-8") as f:
            json.dump(driver.execute_script(debug_script, student_number), f, ensure_ascii=False, indent=2)
        raise RuntimeError(f"attendance cell not found for student {student_number}")


def fill_note(driver: WebDriver, student_number: int, note: str) -> None:
    try:
        field = _wait(driver).until(EC.presence_of_element_located((By.XPATH, build_note_input_xpath(student_number))))
        field.clear()
        field.send_keys(note)
        return
    except Exception:
        pass

    script = """
    const studentNumber = String(arguments[0]);
    const note = arguments[1];
    const row = Array.from(document.querySelectorAll("div[role='row']")).find((el) =>
      el.innerText && el.innerText.split(/\\s+/).includes(studentNumber)
    );
    if (!row) return false;
    const noteCell = row.querySelector("div[data-cellindex='12']");
    if (!noteCell) return false;
    const field = noteCell.querySelector("input, textarea");
    if (!field) return false;
    field.focus();
    field.value = note;
    field.dispatchEvent(new Event("input", { bubbles: true }));
    field.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
    """
    if not driver.execute_script(script, student_number, note):
        return


def click_save(driver: WebDriver) -> None:
    button = _wait(driver).until(EC.presence_of_element_located((By.XPATH, build_button_xpath("\uc800\uc7a5"))))
    driver.execute_script("arguments[0].click();", button)


def click_close(driver: WebDriver) -> None:
    button = _wait(driver).until(EC.presence_of_element_located((By.XPATH, build_button_xpath("\ucd9c\uacb0\ub9c8\uac10"))))
    driver.execute_script("arguments[0].click();", button)


def absent_numbers(absences: Iterable) -> list[int]:
    return [absence.student_number for absence in absences if absence.mark_type.value == "absent"]


def excused_numbers(absences: Iterable) -> list[int]:
    return [absence.student_number for absence in absences if absence.mark_type.value == "excused"]
