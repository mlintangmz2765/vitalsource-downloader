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
        """
        Attempts to detect the page width from the DOM styles.
        Returns width in inches (96 DPI) or None.
        """
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
            # Wait for the button to be attached to DOM
            toc_btn = self.page.wait_for_selector('button[aria-label="Table of Contents"]', timeout=10000)
            if toc_btn:
                toc_btn.click()
                time.sleep(3) # Wait for animation/data fetch
            else:
                print("ToC button not found (timeout).")
        except Exception as e:
            print(f"Could not open ToC or it's already open: {e}")

    def extract_toc(self):
        """Extracts the Table of Contents structure."""
        print("Extracting Table of Contents...")
        self.open_toc_sidebar()
        
        # Use BeautifulSoup to parse
        try:
            # Retry loop for Nav element
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
                # Fallback check
                nav = soup.find('nav', class_='hLmjGr')
            
            if not nav:
                print("ToC nav element definitively not found.")
                return

            # Find all buttons with data-uuid starting with "tocIndex"
            # In BS4, we can use a lambda or loop
            buttons = nav.find_all('button', attrs={'data-uuid': True})
            
            count = 0
            for index, btn in enumerate(buttons):
                uuid = btn.get('data-uuid', '')
                if not uuid.startswith('tocIndex'):
                    continue
                
                try:
                    # Title is usually the first span
                    spans = btn.find_all('span')
                    if len(spans) >= 1:
                        title = spans[0].get_text(strip=True)
                        page_num_str = spans[1].get_text(strip=True) if len(spans) > 1 else ""
                        
                        # Store extracted data
                        self.toc.append({
                            "title": title,
                            "index": index, # This is the capture index, might not match page_num
                            "page_label": page_num_str, 
                            "level": 1 # Flat for now
                        })
                        count += 1
                except Exception as inner_e:
                    print(f"Error parsing ToC item {index}: {inner_e}")

            print(f"Extracted {len(self.toc)} ToC items using BeautifulSoup.")
        except Exception as e:
            print(f"Error extracting ToC: {e}")
            self.toc = []

    def get_total_pages(self):
        """Tries to determine total pages from the UI."""
        # Footer usually has " / 922"
        try:
            # Look for div containing "/" and a number
            # Based on HTML: <div class="sc-wkwDy ebHWgB">/ 922</div>
            footer_text_els = self.page.get_by_text(r"/ \d+").all()
            for el in footer_text_els:
                text = el.inner_text()
                if "/" in text:
                    parts = text.split("/")
                    if len(parts) > 1:
                         return int(parts[1].strip())
        except Exception as e:
            print(f"Could not determine total pages: {e}")
        return 1000 # Default safe limit

    def next_page(self):
        """Navigates to the next page."""
        try:
            # Selector from analysis: button[aria-label="Next"]
            next_btn = self.page.query_selector('button[aria-label="Next"]')
            
            if next_btn and not next_btn.is_disabled():
                next_btn.click()
                # Wait for content to stabilize
                # We can wait for the iframe body to exist/stabilize if needed
                time.sleep(1.5) 
                return True
            else:
                print("Next button not found or disabled.")
                return False
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
                # Execute script to find the book title/author from window state or specific elements
                # VitalSource often puts title in a button or header with specific class
                data = self.page.evaluate("""() => {
                    let title = null;
                    let author = null;
                    
                    // Try to finding the info button or header
                    const titleEl = document.querySelector('h1') || document.querySelector('[role="heading"]');
                    if (titleEl) title = titleEl.innerText;
                    
                    // Try getting data from meta tags which are often more accurate
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
                    # In newer VS reader, there is often a "Details" or "About" button in the menu
                    # But reliable extraction is key.
                    # Let's try to parse the window title aggressively
                    # Format usually: "Book Title | VitalSource Bookshelf"
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
