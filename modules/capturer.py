import os
import time
from playwright.sync_api import Page, Locator
from PIL import Image

class Capturer:
    """
    Handles screenshot capture of book pages, including UI element hiding.
    """
    def __init__(self, page, output_dir="output"):
        self.page = page
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def _wait_for_visible_content_frame(self, timeout_ms=30000):
        """Returns the visible jigsaw content frame once loaded, or None on timeout."""
        deadline = time.time() + timeout_ms / 1000.0
        while time.time() < deadline:
            for frame in self.page.frames:
                if "/content" in frame.url and "jigsaw" in frame.url:
                    try:
                        if frame.frame_element().is_visible():
                            frame.wait_for_load_state("load", timeout=max(1000, int((deadline - time.time()) * 1000)))
                            return frame
                    except Exception:
                        continue
            self.page.wait_for_timeout(200)
        return None

    def hide_ui_elements(self):
        """Hides known UI elements that might obstruct the view."""
        try:
            display_none_style = """
                nav[aria-label='Table of Contents'], 
                .sc-hFLmAl.hLmjGr,
                header, 
                div[role="banner"],
                footer, 
                div[data-testid="scrubber"],
                .sc-wkwDy.ebHWgB,
                button,
                [role="button"],
                [aria-label*="sidebar"],
                [class*="Button"],
                #vst-app-container > div > div:nth-child(2)
                { display: none !important; }
            """
            self.page.evaluate("""(css) => {
                const s = document.createElement('style');
                s.setAttribute('data-vsd-hide', '1');
                s.textContent = css;
                document.head.appendChild(s);
            }""", display_none_style)
        except Exception as e:
            print(f"Warning: could not hide UI: {e}")

    def show_ui_elements(self):
        """Restores UI visibility."""
        try:
            self.page.evaluate("""() => {
                document.querySelectorAll('style[data-vsd-hide]').forEach(s => s.remove());
            }""")
        except Exception as e:
             print(f"Warning: could not show UI: {e}")

    def capture_page(self, page_index: int, zoom_level: int = 1.0) -> dict:
        """Captures page content and returns metadata."""
        # Wait for the visible content iframe (the reader also keeps a hidden, preloaded
        # iframe for the next page, so we must pick the visible one, not the first one).
        element = None
        content_frame = self._wait_for_visible_content_frame(timeout_ms=30000)
        if content_frame is not None:
            self.page.wait_for_timeout(1000)  # let fonts/images settle
            try:
                body = content_frame.locator("body").first
                if body.count() > 0:
                    element = body
            except Exception:
                element = None
        else:
            print("Warning: content frame not found, falling back to page body.")

        self.hide_ui_elements()

        if not element or element.count() == 0:
            element = self.page.locator("body")
            print("Warning: capturing full body.")

        image_path = os.path.join(self.output_dir, f"page_{page_index:04d}.png")
        
        # Capture screenshot
        try:
            # scale="device" ensures we use the device_scale_factor (3.0) for HD capture
            element.screenshot(path=image_path, scale="device")
        except Exception as e:
            print(f"Screenshot failed on frame, trying page fallback: {e}")
            self.page.screenshot(path=image_path)

        # Extract Links
        links = self.extract_links(element, page_index)

        # Put the reader controls back so navigation can click them
        self.show_ui_elements()
        
        return {
            "page_index": page_index,
            "image_path": image_path,
            "links": links
        }

    def extract_links(self, element: Locator, page_index: int):
        """Extracts links and their bounding boxes relative to the captured element."""
        links_data = []
        try:
            # We need to evaluate JS to get coordinates relative to the element
            # This is a bit complex in Playwright without direct API for relative box
            # We will use evaluate to get the bounding box of the element and the links
            
            # 1. Get element global box
            element_box = element.bounding_box()
            if not element_box:
                return []

            # 2. Find all 'a' tags inside
            link_elements = element.locator("a").all()
            
            for link in link_elements:
                box = link.bounding_box()
                if not box:
                    continue
                
                href = link.get_attribute("href")
                if not href:
                    continue

                # Calculate relative coordinates
                rel_x = box["x"] - element_box["x"]
                rel_y = box["y"] - element_box["y"]
                width = box["width"]
                height = box["height"]

                links_data.append({
                    "href": href,
                    "x": rel_x,
                    "y": rel_y,
                    "w": width,
                    "h": height,
                    "page": page_index
                })
        except Exception as e:
            print(f"Error extracting links: {e}")
        
        return links_data
