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
        """Starts the Playwright browser with persistent context."""
        self.playwright = sync_playwright().start()
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=self.headless,
            viewport={"width": 1600, "height": 3000}, # Taller viewport to prevent cutoff
            device_scale_factor=4, # Ultra High DPI for HD capture
            args=["--start-maximized"]
        )
        
        # Load cookies if they exist in the project directory
        self.load_cookies("cookies.json")

        # Create a new page or get the first one
        if len(self.context.pages) > 0:
            self.page = self.context.pages[0]
        else:
            self.page = self.context.new_page()
        
        # Set default timeout
        self.page.set_default_timeout(30000)

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
            self.context.close()
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
