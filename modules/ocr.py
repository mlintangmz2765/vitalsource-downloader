import pytesseract
import os

class OCRManager:
    """
    Manages OCR processing and image-to-PDF conversion with compression.
    """
    def __init__(self, target_width_inches=9.15):
        self.target_width_inches = target_width_inches

    def image_to_pdf(self, image_path: str):
        """Converts an image to a searchable PDF page with correct sizing."""
        temp_jpg = image_path.replace(".png", ".jpg")
        output_pdf_path = image_path.replace(".png", ".pdf")
        try:
            # 1. Compress Image (PNG -> High Quality JPEG)
            # This drastically reduces PDF size for HD screenshots
            from PIL import Image
            with Image.open(image_path) as img:
                # Convert to RGB (remove alpha)
                rgb_img = img.convert('RGB')
                
                # Calculate DPI to fit standard page width
                # Custom width passed from arguments (default 9.15 for this project)
                target_dpi = int(img.width / self.target_width_inches)
                
                # Save as optimized JPEG with specific DPI
                rgb_img.save(temp_jpg, "JPEG", quality=85, optimize=True, dpi=(target_dpi, target_dpi))

            # 2. Generate PDF from the compressed JPEG
            # Tesseract respects the DPI in the image metadata for PDF page sizing
            pdf_bytes = pytesseract.image_to_pdf_or_hocr(temp_jpg, extension='pdf')
            
            with open(output_pdf_path, "wb") as f:
                f.write(pdf_bytes)
            
            # Clean up temp jpeg
            if os.path.exists(temp_jpg):
                os.remove(temp_jpg)
                
            return output_pdf_path
        except Exception as e:
            print(f"OCR Error: {e}")
            if os.path.exists(temp_jpg):
                os.remove(temp_jpg)
            return None
