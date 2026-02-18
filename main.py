import sys
import argparse
import os
import shutil
from tqdm import tqdm
from modules.browser import BrowserManager
from modules.navigator import Navigator
from modules.capturer import Capturer
from modules.ocr import OCRManager
from modules.pdf_maker import PDFMaker

def main():
    parser = argparse.ArgumentParser(description="VitalSource to PDF Converter")
    parser.add_argument("--url", required=True, help="URL of the book to download")
    parser.add_argument("--output", help="Output PDF filename (optional, defaults to ISBN.pdf)")
    parser.add_argument("--pages", type=str, default="all", help="Pages to capture (e.g., '1-10', '1,3,5', 'all')")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--pdf-width", type=float, default=9.15, help="Target PDF page width in inches (default: 9.15 matches typical textbook)")
    args = parser.parse_args()

    # extract ISBN from URL
    # format: .../books/[ISBN]/...
    isbn = "book"
    try:
        if "/books/" in args.url:
            isbn = args.url.split("/books/")[1].split("/")[0]
    except:
        pass

    output_filename = args.output if args.output else f"{isbn}.pdf"
    if not output_filename.endswith(".pdf"):
        output_filename += ".pdf"

    # Initialize Modules
    browser = BrowserManager(headless=args.headless)
    output_dir = "output/temp_pages"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        browser.start()
        # Navigate to book
        browser.navigate_to_book(args.url)

        # Login Check
        print("Please log in if necessary. Press Enter in the terminal to continue once the book is fully loaded.")
        input()

        # Browser & Navigation
        browser = BrowserManager(headless=not args.visible)
        navigator = Navigator(browser.page)
        capturer = Capturer(browser.page, output_dir)
        
        # Auto-detect page width
        target_width = args.pdf_width
        
        metadata = navigator.extract_metadata()
        print(f"Book Metadata: {metadata}")

        detected_width = navigator.get_page_width_inches()
        if detected_width:
            print(f"Auto-detected page width: {detected_width} inches")
            if 4.0 < detected_width < 20.0: 
                target_width = detected_width
        else:
             print(f"Using manual/default page width: {target_width} inches")

        ocr = OCRManager(target_width_inches=target_width)
        
        # Extract ToC
        navigator.extract_toc()

        
        # Filter ToC based on pages argument
        pages_to_capture = navigator.toc
        
        if args.pages and args.pages.lower() != "all":
            try:
                # Parse page ranges (e.g., "1-5", "1,3,5")
                indices = set()
                parts = args.pages.split(',')
                for part in parts:
                    if '-' in part:
                        start, end = map(int, part.split('-'))
                        indices.update(range(start-1, end))
                    else:
                        indices.add(int(part)-1)
                
                # Filter TOC
                filtered_toc = []
                for i, item in enumerate(navigator.toc):
                    if i in indices:
                        filtered_toc.append(item)
                
                if filtered_toc:
                    pages_to_capture = filtered_toc
            except Exception as e:
                print(f"Error parsing pages argument. Capturing all.")

        # Determine page count
        total_pages = len(pages_to_capture)
        print(f"Planning to capture {total_pages} pages.")

        page_files = []

    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
    finally:
        print("Cleaning up...")
        browser.close()
        # Optional: Clean up temp files in output/temp_pages

if __name__ == "__main__":
    main()
