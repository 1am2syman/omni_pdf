import os
import fitz  # Import PyMuPDF
from tqdm import tqdm
from paddleocr import PaddleOCR
from pdf2image import convert_from_path
from PIL import Image
import numpy as np

# Initialize PaddleOCR engine (will be done once for folder processing)
# lang='en' is used by default, can be parameterized later if needed.
# use_angle_cls=True helps with rotated text.
ocr_engine = None

def get_ocr_engine():
    """Initializes and returns the PaddleOCR engine."""
    global ocr_engine
    if ocr_engine is None:
        print("Initializing PaddleOCR engine...")
        ocr_engine = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
        print("PaddleOCR engine initialized.")
    return ocr_engine

def ocr_pdf_page(image: Image.Image, engine: PaddleOCR) -> list:
    """Performs OCR on a single image page and returns results including bounding boxes."""
    # Convert PIL Image to NumPy array for PaddleOCR
    image_np = np.array(image)
    # PaddleOCR expects a list of images or a file path.
    # We'll pass the NumPy array.
    result = engine.ocr(image_np, det=True, rec=True, cls=True)

    # PaddleOCR result format: list of pages, each page is list of lines, each line is [bbox, (text, score)]
    # We'll return the list of lines for the first page (assuming single page image input)
    return result[0] if result and result[0] else []


def convert_pdf_to_ocr(pdf_path: str, output_type: str, output_format='txt', force_ocr=False, engine: PaddleOCR = None):
    """
    Converts a single PDF file using OCR, with options for text output or searchable PDF.
    """
    if not os.path.exists(pdf_path):
        print(f"\nError: File not found at '{pdf_path}'")
        return

    if engine is None:
        engine = get_ocr_engine()

    base_name = os.path.basename(pdf_path)
    
    if output_type == 'text':
        output_path = os.path.splitext(pdf_path)[0] + f".ocr.{output_format}"
        all_text = ""
    elif output_type == 'pdf':
        output_path = os.path.splitext(pdf_path)[0] + f".searchable.pdf"
        # For PDF output, we'll create a new PDF document to add layers
        output_pdf_doc = fitz.open()
    else:
        print(f"\nError: Invalid output type '{output_type}'. Must be 'text' or 'pdf'.")
        return

    try:
        # Use fitz.open() to open the PDF
        doc = fitz.open(pdf_path)
        num_pages = doc.page_count

        # Use tqdm for page-level progress
        for page_num in tqdm(range(num_pages), desc=f"Processing '{base_name}'"):
            page = doc.load_page(page_num)
            page_text = ""
            ocr_results = [] # To store OCR results with bounding boxes for PDF output
            use_ocr = force_ocr

            if not force_ocr and output_type == 'text':
                # Attempt basic text extraction first only for text output
                basic_text = page.get_text() # Use fitz.get_text()
                if basic_text and basic_text.strip():
                    page_text = basic_text
                else:
                    # Basic extraction failed or returned empty, use OCR
                    use_ocr = True
            elif output_type == 'pdf':
                 # Always use OCR for searchable PDF output to get bounding boxes
                 use_ocr = True


            if use_ocr:
                try:
                    # Convert the specific page to a high-resolution image for OCR
                    # dpi can be adjusted for better accuracy vs performance
                    pix = page.get_pixmap(dpi=300)

                    # Determine the correct pixel format (mode) for Pillow based on PyMuPDF Pixmap
                    # Use pix.n for number of components and pix.alpha for alpha channel
                    if pix.alpha:
                        pil_mode = 'RGBA'
                    elif pix.n == 1: # Grayscale
                        pil_mode = 'L'
                    elif pix.n == 3:
                        pil_mode = 'RGB'
                    elif pix.n == 4:
                            pil_mode = 'CMYK'
                    else:
                        # Default to RGB if number of components is unexpected
                        pil_mode = 'RGB'
                        print(f"\nWarning: Unexpected number of color components: {pix.n}. Assuming RGB.")

                    page_image = Image.frombytes(pil_mode, [pix.width, pix.height], pix.samples)

                    ocr_results = ocr_pdf_page(page_image, engine)
                    
                    if output_type == 'text':
                         # Extract text from OCR results for text output
                         page_text = ""
                         for line in ocr_results:
                              page_text += line[1][0] + "\n"

                    # No need to close PIL image explicitly if created from pixmap this way

                except Exception as e:
                     print(f"\nError processing page {page_num + 1} with OCR: {e}")
                     import traceback
                     traceback.print_exc() # Print the full traceback
                     if output_type == 'text':
                         page_text = f"[OCR Error on page {page_num + 1}]" # Indicate error in output
                     # For PDF output, we might add a placeholder or skip layering for this page


            if output_type == 'text':
                all_text += page_text
                if output_format == 'md':
                    all_text += "\n\n---\n\n" # Add a separator for markdown pages
            elif output_type == 'pdf':
                # --- OCR Layering Logic using PyMuPDF ---
                # This is the complex part. We need to add the original page image
                # to a new PDF page and then add the OCRed text as invisible annotations
                # or using a different method for adding invisible text layers.

                # Method 1: Create a new page with the image and add text as annotations
                # This requires creating a new PDF document and adding pages to it.
                # We'll add the original page as a background image and then add text.

                # Create a blank new page with the same dimensions as the original
                new_page = output_pdf_doc.new_page(width=page.rect.width, height=page.rect.height)

                # Add the original page content (visuals) to the new page.
                # A simple way is to draw the original page's pixmap onto the new page.
                # Ensure the pixmap was generated with a suitable DPI (e.g., 300) for good OCR.
                # We already generated the pixmap for OCR, so we can reuse it if available,
                # or generate it again here if needed. Let's regenerate to keep logic clean.
                try:
                    pix = page.get_pixmap(dpi=300) # Regenerate pixmap for drawing
                    # Draw the pixmap onto the new page. The pixmap covers the whole page.
                    new_page.insert_image(new_page.rect, pixmap=pix)
                    # No need to close pixmap explicitly if created this way
                except Exception as e:
                    print(f"\nWarning: Could not get pixmap for page {page_num + 1} for layering: {e}")
                    # If pixmap fails, the new page will be blank visually, but we can still add text layer if OCR succeeded.


                # Add the OCRed text as invisible annotations to the new page
                # Iterate through OCR results (lines or words with bboxes)
                # Assuming ocr_results is a list of [bbox, (text, score)] for lines
                # We need to map bbox coordinates from image pixels to PDF points on the new page.
                # Image size: pix.width x pix.height (pixels)
                # PDF page size: new_page.rect.width x new_page.rect.height (points)
                # Scale factors: scale_x = new_page.rect.width / pix.width, scale_y = new_page.rect.height / pix.height

                if ocr_results: # Check if OCR returned any results for this page
                    # We need to iterate through individual words for better searchability,
                    # but PaddleOCR's default result is lines. Let's process line results first.
                    # For each line result: [bbox, (text, score)]
                    for bbox, (text, score) in ocr_results:
                        # Map bbox from image coords to PDF coords
                        # bbox is [x0, y0, x1, y1] in image pixels
                        # PDF coords are relative to the top-left of the page
                        # x_pdf = x_img * scale_x
                        # y_pdf = y_img * scale_y

                        # Calculate scale factors based on the pixmap used for OCR
                        # Assuming the pixmap was generated with dpi=300
                        # Need the pixmap dimensions used for OCR. Let's assume we regenerate it here.
                        # If pixmap generation failed above, we can't scale correctly.
                        # Let's add a check.
                        if 'pix' in locals(): # Check if pixmap was successfully created
                            scale_x = new_page.rect.width / pix.width
                            scale_y = new_page.rect.height / pix.height

                            # Calculate the rectangle on the PDF page
                            text_rect = fitz.Rect(
                                bbox[0] * scale_x,
                                bbox[1] * scale_y,
                                bbox[2] * scale_x,
                                bbox[3] * scale_y
                            )

                            # Add the text as an invisible annotation within the rectangle
                            # Using add_text_annot is one way, but insert_text with render=3 is more standard for searchable text layers.
                            # insert_text requires a point and calculates font size automatically or takes a fontsize.
                            # We have a rectangle, not a single point.

                            # A common technique is to use the 'text' method with render=3
                            # page.insert_text(point, text, fontsize=..., render=3)
                            # We need to insert the text at the correct position and size.

                            # Let's try inserting the text at the bottom-left of the mapped rectangle
                            # and approximate font size from the rectangle height.
                            font_size = text_rect.height * 0.8 # Approximate font size

                            # Ensure font size is reasonable
                            if font_size < 4: font_size = 4 # Minimum font size
                            if font_size > 30: font_size = 30 # Maximum font size

                            # Insert the text invisibly
                            # The point is the bottom-left corner of the text baseline.
                            # For a rectangle, the bottom-left point is (text_rect.x0, text_rect.y1)
                            # We need to be careful with text baseline vs bbox bottom.
                            # Let's use the top-left of the bbox for insertion point and rely on insert_text to handle baseline.
                            # point = fitz.Point(text_rect.x0, text_rect.y0) # Top-left

                            # Let's try inserting text at the top-left of the rectangle
                            # new_page.insert_text(point, text, fontsize=font_size, render=3)

                            # A more robust way for searchable text is often to use the 'text' method
                            # with render=3, drawing text within the bounding box.
                            # This requires iterating through words.

                            # Let's refine ocr_pdf_page to return word-level results if possible.
                            # PaddleOCR's result structure can be nested to include words.
                            # result = engine.ocr(image, det=True, rec=True, cls=True)
                            # result[0] is list of lines. Each line is [bbox, (text, score)].
                            # The text in (text, score) is the recognized text for the whole line.
                            # To get word bboxes, we might need to process the result further or use a different output format from PaddleOCR.

                            # Let's stick to line-level for now, as it's simpler and still provides searchability.
                            # We'll insert the entire line text at the line's bounding box location.

                            # For each [bbox, (text, score)] in ocr_results:
                            #   line_bbox = bbox
                            #   line_text = text

                            #   # Map line_bbox from image coords to PDF coords
                            #   # bbox is [x0, y0, x1, y1] in image pixels
                            #   # PDF coords are relative to the top-left of the page
                            #   # x_pdf = x_img * scale_x
                            #   # y_pdf = y_img * scale_y

                            #   pdf_rect = fitz.Rect(
                            #       line_bbox[0] * scale_x,
                            #       line_bbox[1] * scale_y,
                            #       line_bbox[2] * scale_x,
                            #       line_bbox[3] * scale_y
                            #   )

                            #   # Approximate font size from line height
                            #   font_size = pdf_rect.height * 0.8
                            #   if font_size < 4: font_size = 4
                            #   if font_size > 30: font_size = 30

                            #   # Insert the line text invisibly at the top-left of the line rectangle
                            #   # Using insert_text with render=3
                            #   point = fitz.Point(pdf_rect.x0, pdf_rect.y0)
                            #   new_page.insert_text(point, line_text, fontsize=font_size, render=3)

                            # This seems like a reasonable approach for line-based searchable text.

                            # Let's implement this logic.

                            for bbox, (text, score) in ocr_results:
                                line_bbox = bbox
                                line_text = text

                                # Map line_bbox from image coords to PDF coords
                                # bbox is [x0, y0, x1, y1] in image pixels
                                # PDF coords are relative to the top-left of the page
                                # x_pdf = x_img * scale_x
                                # y_pdf = y_img * scale_y

                                pdf_rect = fitz.Rect(
                                    line_bbox[0] * scale_x,
                                    line_bbox[1] * scale_y,
                                    line_bbox[2] * scale_x,
                                    line_bbox[3] * scale_y
                                )

                                # Approximate font size from line height
                                font_size = pdf_rect.height * 0.8
                                if font_size < 4: font_size = 4
                                if font_size > 30: font_size = 30

                                # Insert the line text invisibly at the top-left of the line rectangle
                                # Using insert_text with render=3
                                point = fitz.Point(pdf_rect.x0, pdf_rect.y0)
                                try:
                                    new_page.insert_text(point, line_text, fontsize=font_size, render=3)
                                except Exception as text_insert_e:
                                    print(f"\nWarning: Could not insert text '{line_text}' on page {page_num + 1}: {text_insert_e}")


                        else:
                            print(f"\nWarning: Skipping text layering for page {page_num + 1} due to missing pixmap.")

                else:
                    # If OCR returned no results for this page, just add the original page visual
                    # The new_page with the image is already created above.
                    pass # No text to add

                # --- End OCR Layering Logic ---


        if output_type == 'text':
            # Write the combined text to the output file
            with open(output_path, 'w', encoding='utf-8') as outfile:
                outfile.write(all_text)

            print(f"\nSuccessfully processed '{pdf_path}' and saved text to '{output_path}'")

        elif output_type == 'pdf':
            # Save the OCR-layered PDF document
            output_pdf_doc.save(output_path)
            output_pdf_doc.close() # Close the output document
            print(f"\nSuccessfully processed '{pdf_path}' and saved searchable PDF to '{output_path}'")

        doc.close() # Close the original document

    except FileNotFoundError:
        print(f"\nError: File not found at '{pdf_path}'")
    except Exception as e:
        print(f"\nAn unexpected error occurred while processing '{pdf_path}': {e}")


def ocr_folder_pdfs(folder_path: str, output_type: str, output_format='txt', force_ocr=False):
    """
    Performs OCR on all PDF files in a folder with progress bars.
    """
    if not os.path.isdir(folder_path):
        print(f"\nError: Folder not found at '{folder_path}'")
        return

    pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")]
    if not pdf_files:
        print(f"\nNo PDF files found in '{folder_path}'")
        return

    # Initialize OCR engine once for the folder
    engine = get_ocr_engine()

    # Use tqdm for file-level progress
    for filename in tqdm(pdf_files, desc=f"Processing folder '{os.path.basename(folder_path)}'"):
        pdf_path = os.path.join(folder_path, filename)
        # Call the single file function, passing the initialized engine and output type
        convert_pdf_to_ocr(pdf_path, output_type, output_format, force_ocr, engine)
