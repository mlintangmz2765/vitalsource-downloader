"""Fake Playwright objects for exercising navigation/capture logic without a browser."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FakeElement:
    def __init__(self, visible=True):
        self.visible = visible

    def is_visible(self):
        return self.visible


class FakeLocator:
    """Stands in for a Playwright Locator (the `.first` of a selector)."""

    def __init__(self, page, exists=True, disabled=False, visible=True, on_click=None):
        self.page = page
        self.exists = exists
        self.disabled = disabled
        self.visible = visible
        self.on_click = on_click
        self.clicks = 0
        self.screenshots = []

    @property
    def first(self):
        return self

    def count(self):
        return 1 if self.exists else 0

    def is_disabled(self):
        return self.disabled

    def is_visible(self):
        return self.visible

    def click(self, timeout=None):
        if not self.exists or self.disabled or not self.visible:
            raise RuntimeError("Locator.click: element not clickable")
        self.clicks += 1
        if self.on_click:
            self.on_click()

    def screenshot(self, path, scale=None):
        self.screenshots.append(path)
        with open(path, "wb") as f:
            f.write(b"png")

    def bounding_box(self):
        return None

    def locator(self, selector):
        return FakeLocator(self.page, exists=False)

    def all(self):
        return []


class FakeFrame:
    def __init__(self, url, visible=True, page_id=None):
        self.url = url
        self.element = FakeElement(visible)
        self.page_id = page_id or url
        self.body = FakeLocator(None)

    def frame_element(self):
        return self.element

    def wait_for_load_state(self, state="load", timeout=None):
        pass

    def locator(self, selector):
        return self.body

    def evaluate(self, js, arg=None):
        return None


class FakeKeyboard:
    def __init__(self):
        self.pressed = []

    def press(self, key):
        self.pressed.append(key)


class FakePage:
    """Minimal model of the VitalSource reader: a URL with /pageid/N, a Next button,
    and one visible content iframe plus a hidden preloaded one for the following page."""

    BASE = "https://bookshelf.vitalsource.com/reader/books/0000000000000"

    def __init__(self, page_id=0, last_page_id=10, next_disabled=False):
        self.page_id = page_id
        self.last_page_id = last_page_id
        self.keyboard = FakeKeyboard()
        self.styles = []          # injected <style data-vsd-hide> tags
        self.evaluated = []
        self.gotos = []
        self.next_button = FakeLocator(self, disabled=next_disabled, on_click=self._advance)
        self.on_next = None
        self._frames = {}

    # --- reader model ---
    def _advance(self):
        if self.on_next:
            self.on_next()
        elif self.page_id < self.last_page_id:
            self.page_id += 1

    @property
    def url(self):
        return f"{self.BASE}/pageid/{self.page_id}"

    def content_frame(self, page_id):
        """One FakeFrame per reader page, cached so tests can inspect it afterwards."""
        if page_id not in self._frames:
            self._frames[page_id] = FakeFrame(
                f"https://jigsaw.vitalsource.com/books/0000000000000/pages/{1000 + page_id}/content?x=1",
                page_id=page_id)
        return self._frames[page_id]

    @property
    def frames(self):
        visible = self.content_frame(self.page_id)
        preloaded = self.content_frame(self.page_id + 1)
        for frame in self._frames.values():
            frame.element.visible = frame is visible
        wrapper = FakeFrame("https://jigsaw.vitalsource.com/mosaic/wrapper.html", visible=True)
        # preloaded (hidden) frame deliberately listed before the visible one
        return [FakeFrame(self.url), wrapper, preloaded, visible]

    # --- Playwright API subset ---
    def evaluate(self, js, arg=None):
        self.evaluated.append(js)
        if "location.href" in js:
            return self.url
        if "data-vsd-hide" in js and "createElement" in js:
            self.styles.append(arg)
            return None
        if "data-vsd-hide" in js and "remove" in js:
            self.styles.clear()
            return None
        return None

    def locator(self, selector):
        if "Next" in selector or "pb-next" in selector:
            self.next_button.visible = not self.styles  # hidden while hide-styles are injected
            return self.next_button
        return FakeLocator(self, exists=False)

    def wait_for_url(self, predicate, timeout=None):
        if not predicate(self.url):
            raise TimeoutError("wait_for_url: URL did not change")

    def wait_for_timeout(self, ms):
        pass

    def goto(self, url):
        self.gotos.append(url)
        self.page_id = int(url.rsplit("/pageid/", 1)[1])
