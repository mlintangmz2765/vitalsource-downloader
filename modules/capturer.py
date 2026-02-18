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
            self.page.add_style_tag(content=display_none_style)
        except Exception as e:
            print(f"Warning: could not hide UI: {e}")

    def show_ui_elements(self):
        """Restores UI visibility."""
        try:
            self.page.evaluate("""
                const styles = document.querySelectorAll('style');
                if (styles.length > 0) {
                    styles[styles.length - 1].remove();
                }
            """)
        except Exception as e:
             print(f"Warning: could not show UI: {e}")

    def capture_page(self, page_index: int, zoom_level: int = 1.0) -> dict:
        """Captures page content and returns metadata."""
        try:
            self.page.wait_for_load_state("networkidle", timeout=15000)
            time.sleep(4)
        except:
            print("Warning: Network idle timeout, proceeding...")
            time.sleep(2)

        self.hide_ui_elements()
        # Element to capture.
        element = None
        
        # Try to find the best container
        try:
            # Iterate through frames to find the actual content frame
            for frame in self.page.frames:
                if "/content" in frame.url and "jigsaw" in frame.url:
                    try:
                        body = frame.locator("body").first
                        if body.count() > 0:
                            element = body
                            break
                    except:
                        continue
            
            if not element:
                 frame_handle = self.page.frame_locator('iframe[title="Document reading pane"]').first
                 if frame_handle:
                     element = frame_handle.locator("body").first

            if not element:
                 frame_handle = self.page.frame_locator('iframe[src*="wrapper.html"]').first
                 if frame_handle:
                      element = frame_handle.locator("body").first

            if not element:
                 frame_handle = self.page.frame_locator('iframe[src*="jigsaw.vitalsource.com"]').first
                 if frame_handle:
                      element = frame_handle.locator("body").first
        except Exception as e:
             print(f"Error finding frame: {e}")
             pass

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
