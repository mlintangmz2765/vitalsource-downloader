import os

from modules.capturer import Capturer
from modules.navigator import Navigator
from tests.conftest import FakePage


def test_capture_screenshots_visible_frame_not_preloaded_one(tmp_path):
    page = FakePage(page_id=3)
    capturer = Capturer(page, str(tmp_path))

    result = capturer.capture_page(4)

    assert result["page_index"] == 4
    assert os.path.exists(result["image_path"])
    assert page.content_frame(3).body.screenshots == [result["image_path"]]
    assert page.content_frame(4).body.screenshots == []  # hidden preloaded frame untouched


def test_capture_hides_ui_only_during_screenshot(tmp_path):
    page = FakePage(page_id=0)
    capturer = Capturer(page, str(tmp_path))

    capturer.hide_ui_elements()
    assert page.locator('button[aria-label="Next"]').is_visible() is False

    capturer.capture_page(1)
    assert page.styles == [], "hide-styles must be removed after the screenshot"
    assert page.locator('button[aria-label="Next"]').is_visible() is True


def test_capture_then_next_visits_distinct_pages(tmp_path):
    """Regression for the 'same page N times' bug: alternating capture/next must
    screenshot a different reader page each time."""
    page = FakePage(page_id=0, last_page_id=5)
    nav = Navigator(page)
    capturer = Capturer(page, str(tmp_path))

    assert nav.jump_to_page(FakePage.BASE, 1)
    for n in range(1, 4):
        capturer.capture_page(n)
        if n < 3:
            assert nav.next_page()

    captured = [pid for pid in range(0, 5) if page.content_frame(pid).body.screenshots]
    assert captured == [0, 1, 2]
