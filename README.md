# VitalSource to High-Quality PDF Downloader

A robust, full-featured script to convert VitalSource e-textbooks into professional-quality, searchable PDFs.

## Features

-   **Ultra HD Capture**: Captures pages at 4x resolution (High DPI) for crisp text and images.
-   **Intelligent Compression**: Automatically compresses captured pages to High-Quality JPEGs, reducing final PDF size by ~80% without visible quality loss.
-   **Smart Metadata**: Scrapes book Title and Author from the viewer and embeds them into the PDF metadata (XMP & DocInfo).
-   **Exact Layout**: Preserves the original textbook layout, including complex formatting, tables, and images.
-   **Table of Contents**: Extracts the book's ToC and creates clickable PDF bookmarks.
-   **Clean Output**: Automatically hides UI elements (sidebars, buttons, navigation) for a clean reading experience.

## Prerequisites

-   Python 3.10+
-   [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (for searchable text layer)

## Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/mlintangmz2765/vitalsource-downloader.git
    cd vitalsource-downloader
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3.  Install Playwright browsers:
    ```bash
    playwright install chromium
    ```

## Usage

1.  **Login**: The script uses a persistent browser context. On the first run, you may need to log in to VitalSource manually in the browser window that pops up.

2.  **Basic Conversion**:
    ```bash
    python3 main.py --url "https://bookshelf.vitalsource.com/reader/books/[ISBN]"
    ```

3.  **Advanced Options**:
    ```bash
    # Download specific pages
    python3 main.py --url "..." --pages "1-50"

    # Set custom PDF width (default is auto-detected or 9.15 inches)
    python3 main.py --url "..." --pdf-width 8.27  # Force specific size (e.g. A4)

    # Run in background (headless) - Recommended for VPS
    python3 main.py --url "..." --headless
    ```

## VPS / Headless Setup

To run this on a generic Linux VPS (Ubuntu/Debian):

1.  **Install System Dependencies**:
    ```bash
    sudo apt-get update && sudo apt-get install -y tesseract-ocr
    playwright install-deps
    ```

2.  **Run with Headless Mode**:
    Always use the `--headless` flag.

## Disclaimer

This tool is for educational and archival purposes only. Please respect copyright laws and the terms of service of the content provider. Do not distribute copyrighted material without permission.
