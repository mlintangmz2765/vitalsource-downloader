from playwright.sync_api import Page, ElementHandle
from bs4 import BeautifulSoup
import time
import json

class Navigator:
    """
    Handles navigation, Table of Contents extraction, and metadata scraping.
    """
    def __init__(self, page: Page):
        self.page = page
        self.toc = []  # List of dictionaries: {title, page_index, level, id}

    # Common trim sizes (width, height in inches). Order matters: the first entry
    # within tolerance of the measured aspect ratio wins.
    TRIM_SIZES = [
        ("6 x 9 in", 6.0, 9.0),
        ("7 x 10 in", 7.0, 10.0),
        ("8.5 x 11 in (US Letter)", 8.5, 11.0),
        ("A4", 8.27, 11.69),
        ("5.5 x 8.5 in", 5.5, 8.5),
        ("8 x 10 in", 8.0, 10.0),
        ("A5", 5.83, 8.27),
        ("5 x 8 in", 5.0, 8.0),
        ("8.5 x 8.5 in (square)", 8.5, 8.5),
        ("11 x 8.5 in (landscape)", 11.0, 8.5),
    ]

    def measure_page_ratio(self):
        """Returns width/height of the rendered page, measured inside the content frame."""
        frame = self.wait_for_content(timeout_ms=30000)
        if frame is None:
            return None
        try:
            size = frame.evaluate("""() => {
                const img = [...document.images].find(i => i.naturalWidth > 300 && i.naturalHeight > 300);
                if (img) return [img.naturalWidth, img.naturalHeight];
                const page = document.querySelector('#pbk-page') || document.body;
                const r = page.getBoundingClientRect();
                return r.width > 0 && r.height > 0 ? [r.width, r.height] : null;
            }""")
            if size and size[1]:
                return size[0] / size[1]
        except Exception as e:
            print(f"Warning: could not measure page ({e})")
        return None

    def guess_page_size(self):
        """Picks the closest common trim size to the page's aspect ratio.

        The reader never exposes the physical size, only the proportions, so this is a
        best guess; --pdf-width overrides it.
        """
        ratio = self.measure_page_ratio()
        if not ratio:
            return None
        best = min(self.TRIM_SIZES, key=lambda t: abs(t[1] / t[2] - ratio))
        if abs(best[1] / best[2] - ratio) > 0.05:
            return None
        return {"name": best[0], "width": best[1], "height": best[2], "ratio": ratio}

    def open_toc_sidebar(self):
        """Opens the Table of Contents sidebar."""
        try:
            toc_btn = self.page.wait_for_selector('button[aria-label="Table of Contents"]', timeout=10000)
            if toc_btn:
                toc_btn.click()
                time.sleep(3)
            else:
                print("ToC button not found (timeout).")
        except Exception as e:
            print(f"Could not open ToC or it's already open: {e}")

    def extract_toc(self):
        """Extracts the Table of Contents structure."""
        print("Extracting Table of Contents...")
        self.open_toc_sidebar()
        
        try:
            html = ""
            for i in range(3):
                html = self.page.content()
                soup = BeautifulSoup(html, 'html.parser')
                nav = soup.find('nav', {'aria-label': 'Table of Contents'})
                if nav:
                    break
                print(f"ToC nav not found, retrying... ({i+1}/3)")
                time.sleep(2)
            
            if not nav:
                print("ToC nav element not found in DOM via BeautifulSoup after retries.")
                nav = soup.find('nav', class_='hLmjGr')
            
            if not nav:
                print("ToC nav element definitively not found.")
                return

            buttons = nav.find_all('button', attrs={'data-uuid': True})
            
            count = 0
            for index, btn in enumerate(buttons):
                uuid = btn.get('data-uuid', '')
                if not uuid.startswith('tocIndex'):
                    continue
                
                try:
                    spans = btn.find_all('span')
                    if len(spans) >= 1:
                        title = spans[0].get_text(strip=True)
                        page_num_str = spans[1].get_text(strip=True) if len(spans) > 1 else ""
                        
                        cfi = btn.get('data-cfi', '') or btn.get('data-href', '')
                            
                        self.toc.append({
                            "title": title,
                            "index": index, 
                            "page_label": page_num_str, 
                            "level": 1,
                            "link": cfi
                        })
                        count += 1
                except Exception as inner_e:
                    print(f"Error parsing ToC item {index}: {inner_e}")

            print(f"Extracted {len(self.toc)} ToC items using BeautifulSoup.")
        except Exception as e:
            print(f"Error extracting ToC: {e}")
            self.toc = []

    def get_total_pages(self, isbn=None):
        """Total page count: the reader's page list when available, else scraped from the UI."""
        if isbn:
            try:
                resp = self.page.request.get(f"https://jigsaw.vitalsource.com/books/{isbn}/pages.json")
                if resp.ok:
                    pages = resp.json()
                    if isinstance(pages, list) and pages:
                        return len(pages)
            except Exception as e:
                print(f"Warning: could not fetch page list ({e})")
        try:
            selectors = [
                'div[class*="ebHWgB"]',
                '.page-count',
                'div:contains("/")',
                'span[aria-label*="total pages"]'
            ]
            
            for sel in selectors:
                try:
                    el = self.page.query_selector(sel)
                    if el:
                        text = el.inner_text()
                        if "/" in text:
                            return int(text.split("/")[-1].strip().replace(",", ""))
                except:
                    continue

            footer_text = self.page.evaluate("document.body.innerText")
            import re
            match = re.search(r'/\s*(\d{1,4})\b', footer_text)
            if match:
                return int(match.group(1))
        except:
            pass
        return None

    def restore_ui(self):
        """Removes any UI-hiding style tags injected by the Capturer so controls are clickable."""
        try:
            self.page.evaluate("""() => {
                document.querySelectorAll('style[data-vsd-hide]').forEach(s => s.remove());
            }""")
        except Exception:
            pass

    def current_url(self):
        """Returns the live URL (page.url can be stale in the sync API between calls)."""
        try:
            return self.page.evaluate("location.href")
        except Exception:
            return self.page.url

    def wait_for_content(self, timeout_ms: int = 30000):
        """Waits for the visible jigsaw content iframe to finish loading. Returns the frame or None."""
        deadline = time.time() + timeout_ms / 1000.0
        while time.time() < deadline:
            for frame in self.page.frames:
                if "/content" in frame.url and "jigsaw" in frame.url:
                    try:
                        el = frame.frame_element()
                        if el.is_visible():
                            frame.wait_for_load_state("load", timeout=max(1000, int((deadline - time.time()) * 1000)))
                            return frame
                    except Exception:
                        continue
            self.page.wait_for_timeout(200)
        return None

    def jump_to_page(self, book_url: str, page_number: int):
        """Moves the reader directly to a 1-based page. Reader pageids are zero-based."""
        self.page.goto(f"{book_url.rstrip('/')}/pageid/{page_number - 1}")
        return self.wait_for_content() is not None

    def next_page(self):
        """Navigates to the next page. Returns False when the page did not change (end of book)."""
        try:
            self.restore_ui()
            before = self.current_url()

            next_btn = self.page.locator('button[aria-label="Next"], button[aria-label="Next page"], #pb-next-button').first
            try:
                if next_btn.count() and next_btn.is_disabled():
                    return False
                next_btn.click(timeout=8000)
            except Exception:
                # Button not clickable (re-rendering or hidden): keyboard fallback
                self.page.keyboard.press("ArrowRight")

            try:
                self.page.wait_for_url(lambda u: u != before, timeout=10000)
            except Exception:
                return False

            self.wait_for_content()
            return True
        except Exception as e:
            print(f"Navigation error: {e}")
            return False

    def extract_metadata(self):
        """Extracts book metadata (Title, Author)."""
        metadata = {
            "title": "Unknown Title", 
            "author": "Unknown Author",
            "creator": "Adobe InDesign 16.4 (Macintosh)", # Spoofing as per user request
            "producer": "Adobe PDF Library 16.0"        # Spoofing as per user request
        }
        try:
            # The sidebar heading (book title) appears once the reader has fully loaded.
            try:
                self.page.wait_for_selector("h2", timeout=15000)
            except Exception:
                pass

            # 1. Try to get from page title ("VitalSource Bookshelf: <Book Title>")
            page_title = self.page.title() or ""
            if "VitalSource Bookshelf:" in page_title:
                metadata["title"] = page_title.split("VitalSource Bookshelf:")[1].strip()
            elif ":" in page_title:
                metadata["title"] = page_title.split(":", 1)[1].strip()
            elif page_title.strip() and page_title.strip() != "VitalSource Bookshelf":
                metadata["title"] = page_title.strip()

            # 2. Try to find precise metadata from internal JSON state (Common in React apps)
            try:
                data = self.page.evaluate("""() => {
                    let title = null;
                    let author = null;
                    const clean = (t) => (t || '').trim();
                    // The reader's <h1> is the app name ("VitalSource Bookshelf"); the book
                    // title is the <h2> in the ToC sidebar, followed by the author line.
                    for (const el of document.querySelectorAll('h2, h1, [role="heading"]')) {
                        const t = clean(el.innerText);
                        if (!t || /^VitalSource Bookshelf/i.test(t)) continue;
                        title = t;
                        const sib = el.nextElementSibling;
                        if (sib && !sib.querySelector('button, a') && clean(sib.innerText).length < 120) {
                            author = clean(sib.innerText) || null;
                        }
                        break;
                    }
                    const metaTitle = document.querySelector('meta[property="og:title"]');
                    if (metaTitle && metaTitle.content) title = metaTitle.content;
                    return {title, author};
                }""")
                
                if data:
                    if data.get("title"):
                        metadata["title"] = data["title"]
                    if data.get("author"):
                        metadata["author"] = data["author"]
                    # If we can't find author, we might leave it or use a generic one
            except:
                pass
            
            # Fallback: Extract from specific "Details" button if available in sidebar
            if "Unknown" in metadata["title"] or "Unknown" in metadata["author"]:
                try:
                    full_title = self.page.evaluate("document.title")
                    if "|" in full_title:
                        metadata["title"] = full_title.split("|")[0].strip()
                    elif ":" in full_title:
                        metadata["title"] = full_title.split(":")[1].strip()
                except:
                    pass

        except Exception as e:
            print(f"Error extracting metadata: {e}")
        
        return metadata
