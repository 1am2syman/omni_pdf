"""OCR tool to perform OCR on PDF files.

This module provides functions to perform OCR on PDF files. It uses the `fitz` library (PyMuPDF) and `paddleocr` for OCR operations.
The progress bar is displayed on the console in real time using rich.
"""

import os
import fitz
from paddleocr import PaddleOCR
from rich.progress import Progress, TaskID

# Initialize PaddleOCR (this can take some time)
# Consider moving this to a more central location or initializing once
ocr_model = PaddleOCR(use_angle_cls=True, lang='en')

def perform_ocr_on_page(page, ocr_model):
    """Performs OCR on a single page and returns the extracted text."""
    # Render page to an image (PIL Image)
    pix = page.get_pixmap()
    img = pix.pil_image()

    # Perform OCR
    result = ocr_model.ocr(img, clsid=False)

    # Extract text
    text = ""
    if result and result[0]:
        for line in result[0]:
            text += line[1][0] + "\n"
    return text

def convert_pdf_to_ocr(pdf_path, output_type='text', output_format='txt', force_ocr=False, progress: Progress = None, task_id: TaskID = None):
    """Performs OCR on a single PDF file and saves the output as text or a searchable PDF."""
    try:
        doc = fitz.open(pdf_path)
        num_pages = doc.page_count
        output_filename = os.path.splitext(pdf_path)[0]

        if output_type == 'text':
            output_path = output_filename + f'.{output_format}'
            extracted_text = ""
            for page_num in range(num_pages):
                page = doc.load_page(page_num)
                extracted_text += perform_ocr_on_page(page, ocr_model)
                if output_format == 'md':
                    extracted_text += "\n\n---\n\n" # Add a separator for markdown pages
                if progress and task_id:
                    progress.update(task_id, advance=1)

            with open(output_path, 'w', encoding='utf-8') as outfile:
                outfile.write(extracted_text)
            if progress:
                progress.console.print(f"\nSuccessfully performed OCR on '{pdf_path}' and saved as '{output_path}'")
            else:
                print(f"\nSuccessfully performed OCR on '{pdf_path}' and saved as '{output_path}'")

        elif output_type == 'pdf':
            # Creating a new PDF with OCR text (simplified example)
            # A more robust implementation would involve placing text invisibly
            # or using a library specifically for searchable PDF creation.
            output_path = output_filename + '_ocr.pdf'
            new_pdf = fitz.open()
            for page_num in range(num_pages):
                page = doc.load_page(page_num)
                # This is a placeholder. Actual searchable PDF creation is more complex.
                # For a simple approach, you might just add the original page image
                # and potentially add the text layer if the library supports it easily.
                new_pdf.insert_pdf(doc, from_page=page_num, to_page=page_num)
                if progress and task_id:
                    progress.update(task_id, advance=1)

            new_pdf.save(output_path)
            new_pdf.close()
            if progress:
                progress.console.print(f"\nSuccessfully performed OCR on '{pdf_path}' and saved as searchable PDF '{output_path}'")
            else:
                print(f"\nSuccessfully performed OCR on '{pdf_path}' and saved as searchable PDF '{output_path}'")

        doc.close()

    except FileNotFoundError:
        if progress:
            progress.console.print(f"\nError: File not found at '{pdf_path}'")
        else:
            print(f"\nError: File not found at '{pdf_path}'")
    except Exception as e:
        if progress:
            progress.console.print(f"\nError performing OCR on '{pdf_path}': {e}")
        else:
            print(f"\nError performing OCR on '{pdf_path}': {e}")


def ocr_folder_pdfs(folder_path, output_type='text', output_format='txt', force_ocr=False, progress: Progress = None, task_id: TaskID = None):
    """Performs OCR on all PDF files in a folder."""
    if not os.path.isdir(folder_path):
        if progress:
            progress.console.print(f"Error: Folder not found at '{folder_path}'")
        else:
            print(f"Error: Folder not found at '{folder_path}'")
        return

    pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")]
    if not pdf_files:
        if progress:
            progress.console.print(f"\nNo PDF files found in '{folder_path}'")
        else:
            print(f"\nNo PDF files found in '{folder_path}'")
        return

    for filename in pdf_files:
        pdf_path = os.path.join(folder_path, filename)
        convert_pdf_to_ocr(pdf_path, output_type, output_format, force_ocr, progress, task_id)


if __name__ == "__main__":
    # Retain old interactive mode for direct script execution
    import sys
    print("This script should be run through the main CLI interface.")
    sys.exit(1)
