import argparse
import re
import os
import shutil
from tqdm import tqdm
from modules.browser import BrowserManager
from modules.navigator import Navigator
from modules.capturer import Capturer
from modules.ocr import OCRManager
from modules.pdf_maker import PDFMaker
from modules.pages import parse_page_spec, describe_pages, navigation_steps, all_pages

BOOKSHELF_HOME = "https://bookshelf.vitalsource.com/"
READER_URL_RE = re.compile(r"https://bookshelf\.vitalsource\.com/reader/books/(\d{9,13}X?)")


def resolve_book_url(book):
    """Accepts an ISBN or a reader URL; returns a reader URL, or None to open the library."""
    if not book:
        return None
    book = book.strip()
    if re.fullmatch(r"\d{9,13}X?", book):
        return f"https://bookshelf.vitalsource.com/reader/books/{book}"
    return book


def isbn_from_url(url):
    match = READER_URL_RE.match(url or "")
    return match.group(1) if match else None


def main():
    parser = argparse.ArgumentParser(
        description="VitalSource to PDF Converter",
        epilog="With no arguments, the Bookshelf library opens so you can log in and open a book.")
    parser.add_argument("book", nargs="?", help="ISBN or reader URL of the book (optional)")
    parser.add_argument("--url", help="Reader URL of the book (same as the positional argument)")
    parser.add_argument("--output", help="Output PDF filename (defaults to <ISBN>.pdf)")
    parser.add_argument("--pages", type=str, default="all", help="Pages to capture (e.g., '1-10', '1,3,5', 'all')")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode (needs a saved cookies.json)")
    parser.add_argument("--pdf-width", type=float, default=None,
                        help="PDF page width in inches (default: guessed from the page proportions)")
    args = parser.parse_args()

    book_url = resolve_book_url(args.url or args.book)
    output_filename = args.output

    # Initialize Modules
    browser = BrowserManager(headless=args.headless)
    output_dir = "output/temp_pages"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        browser.start()
        if book_url:
            browser.navigate_to_book(book_url)
            print("Please log in if necessary. Press Enter in the terminal to continue once the book is fully loaded.")
        else:
            browser.page.goto(BOOKSHELF_HOME)
            print("Log in if necessary, open the book you want to download, then press Enter in the terminal.")
        input()

        # Use whatever book is open in the browser (the user may have navigated)
        current = browser.page.evaluate("location.href")
        isbn = isbn_from_url(current)
        if not isbn:
            print(f"No book is open in the reader (current page: {current}). "
                  "Open a book at bookshelf.vitalsource.com/reader/books/<ISBN> and try again.")
            return
        book_url = f"https://bookshelf.vitalsource.com/reader/books/{isbn}"
        output_filename = output_filename or f"{isbn}.pdf"
        if not output_filename.endswith(".pdf"):
            output_filename += ".pdf"

        # Save session and switch to high-res mode
        browser.save_cookies("cookies.json")
        browser.set_high_res_viewport()

        # Core components
        navigator = Navigator(browser.page)
        capturer = Capturer(browser.page, output_dir)
        
        metadata = navigator.extract_metadata()
        print(f"Book Metadata: {metadata}")

        # Page width: explicit flag, else guessed from the page proportions
        if args.pdf_width:
            target_width = args.pdf_width
            print(f"Using page width from --pdf-width: {target_width} inches")
        else:
            guess = navigator.guess_page_size()
            if guess:
                target_width = guess["width"]
                print(f"Page proportions {guess['ratio']:.3f} look like {guess['name']} "
                      f"({guess['width']} x {guess['height']} in). Override with --pdf-width if wrong.")
            else:
                target_width = 9.15
                print(f"Could not measure the page; using default width {target_width} inches.")

        ocr = OCRManager(target_width_inches=target_width)
        navigator.extract_toc()

        # Exact page selection (e.g. "3,7-9" captures pages 3, 7, 8 and 9 only)
        try:
            selected_pages = parse_page_spec(args.pages)
        except ValueError as e:
            print(f"{e}. Use forms like '5', '1-10' or '3,7-9', or 'all'.")
            return

        if selected_pages is None:
            # Page count comes from the reader's page list when available; otherwise the
            # capture is open-ended and stops when the Next button no longer advances.
            detected_total = navigator.get_total_pages(isbn)
            targets = all_pages(detected_total)
            pbar_total = detected_total
            print("Capturing the whole book" + (f" ({detected_total} pages)" if detected_total else ""))
        else:
            targets = selected_pages
            pbar_total = len(selected_pages)
            print(f"Capturing {len(selected_pages)} page(s): {describe_pages(selected_pages)}")

        page_files = []
        max_pages_limit = 2500
        captured = 0
        pbar = tqdm(total=pbar_total, desc="Capturing Pages", unit="page")

        # Page capture loop: consecutive pages use the Next button; gaps and the first
        # page jump directly to the reader position.
        for page_number, action in navigation_steps(targets, limit=max_pages_limit):
            try:
                if action == "jump":
                    if not navigator.jump_to_page(book_url, page_number):
                        print(f"Warning: page {page_number} did not load; capturing anyway.")
                elif not navigator.next_page():
                    print("Reached the end of the book.")
                    break

                capturer.capture_page(page_number)

                filename = f"page_{page_number:04d}.png"
                filepath = os.path.join(output_dir, filename)

                optimized_pdf_page = ocr.image_to_pdf(filepath)
                if optimized_pdf_page:
                    page_files.append(optimized_pdf_page)
                    if os.path.exists(filepath):
                        os.remove(filepath)

                pbar.update(1)
                captured += 1

                if captured % 25 == 0:
                    # Periodic reload keeps memory in check; the reader stays on the same page.
                    try:
                        pbar.set_description("Optimizing RAM...")
                        import gc
                        gc.collect()
                        browser.page.reload(timeout=60000)
                        browser.page.wait_for_load_state("domcontentloaded", timeout=60000)
                        browser.set_high_res_viewport()
                        capturer = Capturer(browser.page, output_dir)
                        navigator = Navigator(browser.page)
                        navigator.wait_for_content()
                    except Exception as e:
                        print(f"RAM Optimization warning: {e}")
                    finally:
                        pbar.set_description("Capturing Pages")

            except Exception as e:
                print(f"Error capturing page {page_number}: {e}")

        pbar.close()

        # Generate Final PDF
        if page_files:
            print(f"Generating PDF: {output_filename}...")
            # Save final PDF in the 'output' folder
            pdf_maker = PDFMaker("output")
            
            pdf_maker.make_pdf(page_files, navigator.toc, {}, output_filename, metadata)
            print(f"Successfully created output/{output_filename}")
            
            # Only delete the temporary image subdirectory
            shutil.rmtree(output_dir)
            print("Temporary image files cleaned up.")
        else:
            print("No pages captured.")

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
