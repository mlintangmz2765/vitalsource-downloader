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

1.  **Simplest**: run with no arguments. A browser opens on your Bookshelf library; log in,
    open the book you want, then press Enter in the terminal.
    ```bash
    python3 main.py
    ```

2.  **With an ISBN or reader URL** (skips the library step):
    ```bash
    python3 main.py [ISBN]
    python3 main.py "https://bookshelf.vitalsource.com/reader/books/[ISBN]"
    ```
    Log in if prompted, wait for the book to load, then press Enter in the terminal.
    The PDF is written to `output/<ISBN>.pdf`.

3.  **Options** (all optional):
    ```bash
    # Download specific pages (numbers are reader positions, counting from the cover,
    # so they include front matter and differ from the printed page numbers)
    python3 main.py [ISBN] --pages "1-50"

    # Page size is guessed from the page proportions (6x9, 7x10, A4, Letter, ...).
    # Force a width in inches if the guess is wrong:
    python3 main.py [ISBN] --pdf-width 8.27

    # Custom output name
    python3 main.py [ISBN] --output my-book.pdf

    # Run in background (headless) - needs a cookies.json from a previous login
    python3 main.py [ISBN] --headless
    ```

## VPS / Headless Setup (Step-by-Step)

To run this on a Linux VPS where you cannot open a browser window:

### 1. Initial VPS Setup
Install the necessary system packages first:
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr python3-venv git
```

### 2. Project Preparation
Clone the repo and create a virtual environment (`venv`) to keep things clean:
```bash
git clone https://github.com/mlintangmz2765/vitalsource-downloader.git
cd vitalsource-downloader
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install-deps
playwright install chromium
```

### 3. The "Cookie Trick" (Authentication)
Since the VPS has no screen, you cannot log in there manually.
1.  **On your laptop/PC**: Run the script locally once and log in to VitalSource.
2.  Once logged in, find the `cookies.json` file created in your local project folder.
3.  **Transfer to VPS**: Upload/SFTP that `cookies.json` to the same folder on your VPS.

### 4. Running the Downloader
Now you can run the script headlessly on your VPS:
```bash
# Always activate venv first if starting a new session
source venv/bin/activate

# Execute headlessly
python3 main.py [ISBN] --headless
```

## Disclaimer

This tool is for educational and archival purposes only. Please respect copyright laws and the terms of service of the content provider. Do not distribute copyrighted material without permission.
