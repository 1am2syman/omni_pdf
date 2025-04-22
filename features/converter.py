import os
import fitz  # Import PyMuPDF
from tqdm import tqdm

def convert_pdf_to_text(pdf_path, output_format='txt'):
    """Converts a single PDF file to text or markdown with a progress bar using PyMuPDF."""
    try:
        # Use fitz.open() to open the PDF
        doc = fitz.open(pdf_path)
        text = ""
        num_pages = doc.page_count

        # Use tqdm for page iteration
        for page_num in tqdm(range(num_pages), desc=f"Converting '{os.path.basename(pdf_path)}'"):
            page = doc.load_page(page_num) # Load the page
            text += page.get_text() or "" # Extract text using get_text()
            if output_format == 'md':
                text += "\n\n---\n\n" # Add a separator for markdown pages

        doc.close() # Close the document

        output_path = os.path.splitext(pdf_path)[0] + f".{output_format}"
        with open(output_path, 'w', encoding='utf-8') as outfile:
            outfile.write(text)
        print(f"\nSuccessfully converted '{pdf_path}' to '{output_path}'") # Add newline after progress bar
    except FileNotFoundError:
        print(f"\nError: File not found at '{pdf_path}'") # Add newline
    except Exception as e:
        print(f"\nError converting '{pdf_path}': {e}") # Add newline

def convert_folder_pdfs_to_text(folder_path, output_format='txt'):
    """Converts all PDF files in a folder to text or markdown with progress bars using PyMuPDF."""
    if not os.path.isdir(folder_path):
        print(f"Error: Folder not found at '{folder_path}'")
        return

    pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")]
    if not pdf_files:
        print(f"\nNo PDF files found in '{folder_path}'")
        return

    # Wrap the file iteration with tqdm for a progress bar
    for filename in tqdm(pdf_files, desc=f"Processing folder '{os.path.basename(folder_path)}'"):
        pdf_path = os.path.join(folder_path, filename)
        convert_pdf_to_text(pdf_path, output_format)
