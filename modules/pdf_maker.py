from pikepdf import Pdf, Dictionary, Name, Array, OutlineItem
import os

class PDFMaker:
    """
    Assembles final PDF from processed pages, adding metadata, bookmarks, and links.
    """
    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    def make_pdf(self, page_files: list, toc: list, links_map: dict, output_filename: str, metadata: dict = None):
        """
        Merges page files (PDFs) into a single PDF, adds ToC and links.
        """
        pdf = Pdf.new()

        # Add Metadata
        if metadata:
             # XMP Metadata
             with pdf.open_metadata(set_pikepdf_as_editor=False) as meta:
                 if "title" in metadata:
                     meta["dc:title"] = metadata["title"]
                 if "author" in metadata:
                     meta["dc:creator"] = [metadata["author"]] # Must be list
                 if "creator" in metadata:
                     meta["xmp:CreatorTool"] = metadata["creator"]
                 if "producer" in metadata:
                     meta["pdf:Producer"] = metadata["producer"]
                     
             # DocInfo (Standard PDF info)
             # accessible via pdf.docinfo dictionary in newer pikepdf
             # DocInfo (Standard PDF info)
             # accessible via pdf.docinfo dictionary in newer pikepdf
             if True: # preserving indentation level easiest
                docinfo = pdf.docinfo
                if "title" in metadata:
                    docinfo["/Title"] = metadata["title"]
                if "author" in metadata:
                    docinfo["/Author"] = metadata["author"]
                if "creator" in metadata:
                    docinfo["/Creator"] = metadata["creator"]
                if "producer" in metadata:
                    docinfo["/Producer"] = metadata["producer"]

        print("Merging pages...")
        for i, page_file in enumerate(page_files):
            try:
                # Open the single page PDF
                src_pdf = Pdf.open(page_file)
                # Copy the first page (should be only one)
                # But we want to ensure we don't carry over weird metadata
                pdf.pages.append(src_pdf.pages[0])
                
                # Now the page is at index i in the new PDF
                current_page = pdf.pages[i]

                # Add links
                if i in links_map:
                    self._add_links_to_page(current_page, links_map[i])

            except Exception as e:
                print(f"Error merging page {i}: {e}")

        # Add Bookmarks (Outlines)
        if toc:
            print("Adding bookmarks...")
            with pdf.open_outline() as outline:
                # This is a simple implementation for flat or 1-level deep ToC
                # Needs recursion for nested ToC
                for item in toc:
                    title = item.get("title", "Untitled")
                    idx = item.get("index", 0)
                    if idx < len(pdf.pages):
                        # Create outline item
                        if item.get("level", 1) == 1:
                            # Note: pikepdf OutlineItem requires title and destination
                            oi = OutlineItem(title, idx) # destination can be page index or page object
                            outline.root.append(oi)
                        # Handling nested levels requires keeping track of parents
                        pass 
 
        output_path = os.path.join(self.output_dir, output_filename)
        pdf.save(output_path)
        print(f"PDF saved to {output_path}")

    def _add_links_to_page(self, page, links):
        """Adds URI annotations to the page."""
        # Get page height for coordinate transformation
        # Mediabox is usually [0, 0, width, height]
        mediabox = page.MediaBox
        height = float(mediabox[3])
        
        for link in links:
            try:
                # Link coordinates from browser (top-left origin)
                x, y, w, h = link['x'], link['y'], link['w'], link['h']
                
                # Transform to PDF coordinates (bottom-left origin)
                # We assume the PDF page size matches the screenshot size 1:1 in pixels/points
                # If they differ, we need scaling factors.
                # Usually Tesseract PDF output matches input image size.
                
                rect = [x, height - y - h, x + w, height - y]
                
                # Create annotation
                ann = Dictionary(
                    Type=Name.Annot,
                    Subtype=Name.Link,
                    Rect=Array(rect),
                    Border=Array([0, 0, 0]),
                    A=Dictionary(
                        S=Name.URI,
                        URI=link['href']
                    )
                )
                
                if "/Annots" not in page:
                    page.Annots = Array()
                page.Annots.append(ann)
                
            except Exception as e:
                print(f"Error adding link: {e}")
