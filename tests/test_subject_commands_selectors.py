from subject_teacher.neis.subject_commands import (
    MENU_PATH,
    SIDE_MENU_LABEL,
    SEL,
    build_side_menu_xpath,
    build_student_row_xpath,
    combo_already_selected,
    normalize_neis_date,
)


def test_menu_path_matches_manual():
    assert MENU_PATH == [
        "교과담임",
        "학적",
        "출결관리",
    ]


def test_selectors_are_strings():
    for key, value in SEL.items():
        assert isinstance(value, str) and value, f"selector {key} must be non-empty string"


def test_row_xpath_includes_student_number():
    xpath = build_student_row_xpath(student_number=15)
    assert "15" in xpath


def test_side_menu_xpath_includes_label():
    assert SIDE_MENU_LABEL == "과목별출결관리"
    assert "과목별출결관리" in build_side_menu_xpath()


def test_normalize_neis_date_converts_dash_format():
    assert normalize_neis_date("2026-04-17") == "2026.04.17"
    assert normalize_neis_date("2026.04.17") == "2026.04.17"


def test_combo_already_selected_detects_exact_label():
    aria_labels = [
        "학년도, :::학년도:::",
        "학년도, 2026",
        "학기, 1학기",
    ]

    assert combo_already_selected(aria_labels, "학년도", "2026") is True
    assert combo_already_selected(aria_labels, "학기", "1학기") is True
    assert combo_already_selected(aria_labels, "학기", "2학기") is False
