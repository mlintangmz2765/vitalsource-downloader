import os
import time
from playwright.sync_api import sync_playwright, BrowserContext, Page

class BrowserManager:
    def __init__(self, headless: bool = False, user_data_dir: str = "user_data"):
        self.headless = headless
        self.user_data_dir = os.path.abspath(user_data_dir)
        self.playwright = None
        self.context = None
        self.page = None

    def start(self):
        """Starts the Playwright browser."""
        self.playwright = sync_playwright().start()
        
        # Browser initialization
        self.browser_instance = self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox", 
                "--disable-infobars",
                "--disable-dev-shm-usage", # Critical for low RAM/docker
                "--disable-gpu"
            ]
        )
        
        # Create context with standard settings
        self.context = self.browser_instance.new_context(
            viewport=None, 
            device_scale_factor=4,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # Load cookies
        self.load_cookies("cookies.json")

        # Create a new page or get the first one
        if len(self.context.pages) > 0:
            self.page = self.context.pages[0]
        else:
            self.page = self.context.new_page()
        
        # Set default timeout
        self.page.set_default_timeout(30000)

    def set_high_res_viewport(self):
        """Switches the current page to a high-resolution tall viewport for capturing."""
        if self.page:
            self.page.set_viewport_size({"width": 1600, "height": 3000})
            print("Viewport switched to Ultra HD (1600x3000)")

    def save_cookies(self, path: str):
        """Saves cookies to a JSON file."""
        if self.context:
            cookies = self.context.cookies()
            import json
            with open(path, 'w') as f:
                json.dump(cookies, f)
            print(f"Cookies saved to {path}")

    def load_cookies(self, path: str):
        """Loads cookies from a JSON file."""
        import json
        if os.path.exists(path):
            with open(path, 'r') as f:
                cookies = json.load(f)
            self.context.add_cookies(cookies)
            print(f"Cookies loaded from {path}")
        else:
            print("No cookies found to load.")

    def navigate_to_book(self, url: str):
        """Navigates to the specified book URL."""
        print(f"Navigating to {url}...")
        self.page.goto(url)
        # Wait for the reader to load.  Adjust selector as needed.
        # VitalSource reader usually has a specific container.
        try:
            # Updated selectors based on debug analysis
            self.page.wait_for_selector("iframe[src*='jigsaw'], #vst-app-container, div#print-content", timeout=20000)
            print("Book content loaded.")
        except:
            print("Warning: timed out waiting for content. Please verify login.")

    def close(self):
        """Closes the browser."""
        if self.context:
            try:
                self.context.close()
            except:
                pass
        
        if hasattr(self, 'browser_instance') and self.browser_instance:
             self.browser_instance.close()
             
        if self.playwright:
            self.playwright.stop()

    def is_logged_in(self) -> bool:
        """Checks if the user is likely logged in."""
        # Simple check: if we see a 'Sign In' button, we are probably not logged in.
        # This selector depends on VitalSource's login page.
        # For now, we will rely on manual confirmation or successful navigation to the reader.
        # If redirected to login page, the URL will change.
        current_url = self.page.url
        if "login" in current_url or "signin" in current_url:
            return False
        return True
