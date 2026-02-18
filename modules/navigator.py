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

    def get_page_width_inches(self):
        """Detects page width from DOM styles."""
        try:
            width_px = self.page.evaluate("""() => {
                const selectors = [
                    '#jigsaw-content', 
                    '#book-content', 
                    '.page-content',
                    'iframe[src*="jigsaw"]',
                    'div[data-page-no]'
                ];
                
                for (const sel of selectors) {
                    const el = document.querySelector(sel);
                    if (el && el.offsetWidth > 0) {
                        return el.offsetWidth;
                    }
                }
                
                const imgs = document.querySelectorAll('img');
                for (const img of imgs) {
                     if (img.width > 500) return img.width;
                }
                return null;
            }""")
            
            if width_px:
                return round(width_px / 96.0, 2)
            
        except Exception as e:
            print(f"Warning: Could not detect page width ({e})")
        
        return None


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

    def get_total_pages(self):
        """Attempts to determine total page count from UI."""
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

    def next_page(self):
        """Navigates to the next page."""
        try:
            selectors = [
                'button[aria-label="Next"]',
                'button[aria-label="Next page"]',
                '[data-testid="next-button"]',
                'button:has(svg[aria-label="Next"])',
                '#pb-next-button'
            ]
            
            next_btn = None
            for sel in selectors:
                btn = self.page.query_selector(sel)
                if btn and not btn.is_disabled() and btn.is_visible():
                    next_btn = btn
                    break
                
                if not next_btn:
                    for frame in self.page.frames:
                        try:
                            btn = frame.query_selector(sel)
                            if btn and not btn.is_disabled() and btn.is_visible():
                                next_btn = btn
                                break
                        except:
                            continue
                if next_btn:
                    break
            
            if next_btn:
                next_btn.click()
                time.sleep(1.5) 
                return True
            else:
                # Keyboard fallback
                self.page.keyboard.press("ArrowRight")
                time.sleep(1.5)
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
            # 1. Try to get from page title
            page_title = self.page.title()
            if page_title:
                if "VitalSource Bookshelf:" in page_title:
                    metadata["title"] = page_title.split("VitalSource Bookshelf:")[1].strip()
                elif ":" in page_title:
                    metadata["title"] = page_title.split(":")[1].strip()
                else:
                    metadata["title"] = page_title.strip()

            # 2. Try to find precise metadata from internal JSON state (Common in React apps)
            try:
                data = self.page.evaluate("""() => {
                    let title = null;
                    let author = null;
                    const titleEl = document.querySelector('h1') || document.querySelector('[role="heading"]');
                    if (titleEl) title = titleEl.innerText;
                    const metaTitle = document.querySelector('meta[property="og:title"]');
                    if (metaTitle) title = metaTitle.content;
                    return {title, author};
                }""")
                
                if data:
                    if data.get("title"):
                        metadata["title"] = data["title"]
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
