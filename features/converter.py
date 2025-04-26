"""PDF Converter tool to convert PDF files to text or markdown.

This module provides functions to convert PDF files to text or markdown. It uses the `fitz` library (PyMuPDF) for PDF operations.
The progress bar is displayed on the console in real time using rich.
"""

import os
import fitz  # Import PyMuPDF
from rich.progress import Progress, TaskID

def convert_pdf_to_text(pdf_path, output_format='txt', progress: Progress = None, task_id: TaskID = None):
    """Converts a single PDF file to text or markdown with a progress bar using PyMuPDF."""
    try:
        # Use fitz.open() to open the PDF
        doc = fitz.open(pdf_path)
        text = ""
        num_pages = doc.page_count

        # Use rich for page iteration
        for page_num in range(num_pages):
            page = doc.load_page(page_num) # Load the page
            text += page.get_text() or "" # Extract text using get_text()
            if output_format == 'md':
                text += "\n\n---\n\n" # Add a separator for markdown pages
            if progress and task_id:
                progress.update(task_id, advance=1)

        doc.close() # Close the document

        output_path = os.path.splitext(pdf_path)[0] + f".{output_format}"
        with open(output_path, 'w', encoding='utf-8') as outfile:
            outfile.write(text)
        if progress:
             progress.console.print(f"\nSuccessfully converted '{pdf_path}' to '{output_path}'") # Add newline after progress bar
        else:
             print(f"\nSuccessfully converted '{pdf_path}' to '{output_path}'")
    except FileNotFoundError:
        if progress:
            progress.console.print(f"\nError: File not found at '{pdf_path}'") # Add newline
        else:
            print(f"\nError: File not found at '{pdf_path}'")
    except Exception as e:
        if progress:
            progress.console.print(f"\nError converting '{pdf_path}': {e}") # Add newline
        else:
            print(f"\nError converting '{pdf_path}': {e}")


def convert_folder_pdfs_to_text(folder_path, output_format='txt', progress: Progress = None, task_id: TaskID = None):
    """Converts all PDF files in a folder to text or markdown with progress bars using PyMuPDF."""
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

    # Wrap the file iteration with rich for a progress bar
    for filename in pdf_files:
        pdf_path = os.path.join(folder_path, filename)
        convert_pdf_to_text(pdf_path, output_format, progress, task_id)


if __name__ == "__main__":
    # Retain old interactive mode for direct script execution
    import sys
    print("This script should be run through the main CLI interface.")
    sys.exit(1)
