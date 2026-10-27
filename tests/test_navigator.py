from modules.navigator import Navigator
from tests.conftest import FakePage


def test_next_page_clicks_next_and_verifies_url_changed():
    page = FakePage(page_id=4)
    nav = Navigator(page)
    assert nav.next_page() is True
    assert page.page_id == 5
    assert page.next_button.clicks == 1
    assert page.keyboard.pressed == []


def test_next_page_restores_hidden_ui_before_clicking():
    # Regression: hide-styles left behind by the Capturer made the Next button
    # unclickable, so every "page turn" silently re-captured the same page.
    page = FakePage(page_id=1)
    page.styles.append("button { display: none }")
    nav = Navigator(page)
    assert nav.next_page() is True
    assert page.styles == []
    assert page.page_id == 2


def test_next_page_returns_false_when_button_disabled_at_end():
    page = FakePage(page_id=10, last_page_id=10, next_disabled=True)
    assert Navigator(page).next_page() is False
    assert page.page_id == 10


def test_next_page_returns_false_when_url_does_not_change():
    page = FakePage(page_id=10, last_page_id=10)  # click succeeds but reader stays put
    assert Navigator(page).next_page() is False


def test_next_page_falls_back_to_keyboard_when_click_fails_and_verifies():
    page = FakePage(page_id=2)
    page.next_button.exists = False
    page.on_next = None
    nav = Navigator(page)
    # keyboard does nothing in the fake, so the URL must be reported unchanged
    assert nav.next_page() is False
    assert page.keyboard.pressed == ["ArrowRight"]


def test_wait_for_content_picks_visible_frame_not_preloaded_one():
    page = FakePage(page_id=6)
    frame = Navigator(page).wait_for_content(timeout_ms=500)
    assert frame is not None
    assert frame.page_id == 6


def test_jump_to_page_uses_zero_based_pageid():
    page = FakePage(page_id=0)
    assert Navigator(page).jump_to_page(FakePage.BASE, 1) is True
    assert page.gotos == [f"{FakePage.BASE}/pageid/0"]
    assert Navigator(page).jump_to_page(FakePage.BASE + "/", 7) is True
    assert page.gotos[-1] == f"{FakePage.BASE}/pageid/6"
    assert page.page_id == 6
