"""Omni PDF - A comprehensive PDF manipulation tool with a modern CLI."""
import sys
import os
import questionary
from features.converter import convert_pdf_to_text, convert_folder_pdfs_to_text
from features.splitter import split_pdf
from features.reorder import start_editor
from rich.progress import Progress
from features.compressor import PDFCompressor
from features.conversions import (
    PDFToImageConverter,
    ImageToPDFConverter,
    TextToPDFConverter,
    MarkdownToPDFConverter,
    HTMLToPDFConverter,
    handle_conversion
)
from features.scanner import app as scanner_app
import threading
import webbrowser

def scan_to_pdf_cli():
    """Scan image(s) to PDF with a local web interface."""
    input_path = questionary.text(
        "Scan Image to PDF: Enter image file or folder path",
        validate=lambda path: os.path.exists(path) or "Path does not exist"
    ).ask()
    if not input_path:
        return

    output_folder = questionary.text(
        "Enter output folder (leave blank for same as input):",
        default=''
    ).ask()

    # Determine if input is file or folder
    image_paths = []
    if os.path.isfile(input_path):
        image_paths.append(input_path)
    elif os.path.isdir(input_path):
        # For now, just get image files. We'll handle multiple images in the Flask app later.
        for filename in os.listdir(input_path):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
                image_paths.append(os.path.join(input_path, filename))
        if not image_paths:
            print("No supported image files found in the specified folder.")
            return
    else:
        print("Invalid input path. Please provide a valid image file or folder.")
        return

    if not image_paths:
        print("No supported image files found.")
        return

    print(f"Launching scan interface for {len(image_paths)} image(s).")

    # Run Flask app in a separate thread
    def run_flask():
        scanner_app.run(debug=False, port=5000) # Run on a specific port

    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True # Allow the main program to exit even if the thread is running
    flask_thread.start()

    # Open the browser to the scan interface
    # Pass all image paths as a comma-separated string for now
    import urllib.parse
    encoded_image_paths = urllib.parse.quote_plus(",".join(image_paths))
    encoded_output_folder = urllib.parse.quote_plus(output_folder)
    scan_url = f"http://localhost:5000/scan?image_paths={encoded_image_paths}&output_folder={encoded_output_folder}"
    print(f"Opening browser to {scan_url}")
    webbrowser.open(scan_url)

    # Keep the main thread alive while the Flask thread is running
    input("Press Enter to close the scan interface and continue...")


def convert_to_text_cli():
    """Convert PDF to text or markdown format."""
    pdf_path = questionary.text(
        "PDF to Text: Enter file/folder path", 
        validate=lambda path: os.path.exists(path) or "Path does not exist"
    ).ask()
    if not pdf_path:
        return
    output_format = questionary.select(
        "Select output format:",
        choices=['txt', 'md'],
        default='txt'
    ).ask()
    if not output_format:
        return

    with Progress() as progress:
        if os.path.isfile(pdf_path):
            # For single file, we need to get the number of pages to set the total for the progress bar
            try:
                doc = fitz.open(pdf_path)
                num_pages = doc.page_count
                doc.close()
            except Exception:
                num_pages = 1 # Fallback if we can't get page count
            task = progress.add_task(f"Converting [bold green]'{os.path.basename(pdf_path)}'[/bold green] to [bold blue]{output_format}[/bold blue]...", total=num_pages)
            convert_pdf_to_text(pdf_path, output_format, progress, task)
        else:
            # For folder, we can count the number of PDF files
            try:
                pdf_files = [f for f in os.listdir(pdf_path) if f.lower().endswith('.pdf')]
                num_files = len(pdf_files)
            except Exception:
                num_files = 1 # Fallback if we can't count files
            task = progress.add_task(f"Converting [bold green]{num_files}[/bold green] files in [bold blue]'{os.path.basename(pdf_path)}'[/bold blue] to [bold blue]{output_format}[/bold blue]...", total=num_files)
            convert_folder_pdfs_to_text(pdf_path, output_format, progress, task)

def split_cli():
    """Split PDF into multiple files by page ranges."""
    pdf_path = questionary.text(
        "Split PDF: Enter file path", 
        validate=lambda path: os.path.exists(path) and os.path.isfile(path) or "Invalid file path"
    ).ask()
    if not pdf_path:
        return
    page_ranges = questionary.text("Enter page ranges to split (e.g., 1-5,7,10-12):").ask()
    if not page_ranges:
        return
    output_dir = questionary.text("Enter output directory (leave blank for same as input):", default='').ask()

    # We need to determine the number of splits to set the total for the progress bar
    # This requires parsing the page_ranges string
    ranges = []
    for part in page_ranges.split(','):
        part = part.strip()
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                ranges.append((start, end))
            except ValueError:
                pass # Handle invalid ranges in the split_pdf function
        else:
            try:
                page_num = int(part)
                ranges.append((page_num, page_num))
            except ValueError:
                pass # Handle invalid page numbers in the split_pdf function

    total_splits = len(ranges) if ranges else 1 # Default to 1 task if ranges are invalid or empty

    with Progress() as progress:
        task = progress.add_task(f"Splitting [bold green]'{os.path.basename(pdf_path)}'[/bold green]...", total=total_splits)
        split_pdf(pdf_path, page_ranges, output_dir if output_dir else None, progress, task)

def ocr_cli():
    """Convert scanned PDF to searchable text/PDF."""
    from features.ocr import convert_pdf_to_ocr, ocr_folder_pdfs
    pdf_path = questionary.text(
        "OCR: Enter file/folder path",
        validate=lambda path: os.path.exists(path) or "Path does not exist"
    ).ask()
    if not pdf_path:
        return
    output_type = questionary.select(
        "Select output type:",
        choices=['text', 'pdf'],
        default='text'
    ).ask()
    if not output_type:
        return
    output_format = 'txt'
    if output_type == 'text':
         output_format = questionary.select(
            "Select text output format:",
            choices=['txt', 'md'],
            default='txt'
        ).ask()
         if not output_format:
             return

    force_ocr = questionary.confirm("Force OCR on all pages (otherwise intelligent detection)?", default=False).ask()
    if force_ocr is None: # Handle Ctrl+C
        return

    with Progress() as progress:
        if os.path.isfile(pdf_path):
            # For single file, we need to get the number of pages to set the total for the progress bar
            try:
                doc = fitz.open(pdf_path)
                num_pages = doc.page_count
                doc.close()
            except Exception:
                num_pages = 1 # Fallback if we can't get page count
            task = progress.add_task(f"Performing OCR on [bold green]'{os.path.basename(pdf_path)}'[/bold green]...", total=num_pages)
            convert_pdf_to_ocr(pdf_path, output_type, output_format, force_ocr, progress, task)
        else:
            # For folder, we can count the number of PDF files
            try:
                pdf_files = [f for f in os.listdir(pdf_path) if f.lower().endswith('.pdf')]
                num_files = len(pdf_files)
            except Exception:
                num_files = 1 # Fallback if we can't count files
            task = progress.add_task(f"Performing OCR on [bold green]{num_files}[/bold green] files in [bold blue]'{os.path.basename(pdf_path)}'[/bold blue]...", total=num_files)
            ocr_folder_pdfs(pdf_path, output_type, output_format, force_ocr, progress, task)

def merge_cli():
    """Combine multiple PDFs into one file."""
    from features.merger import merge_pdfs
    pdf_paths = []
    while True:
        pdf_path = questionary.text(
            "Merge: Add PDF file (blank when done)",
            validate=lambda path: os.path.exists(path) and os.path.isfile(path) or "Invalid file path"
        ).ask()
        if not pdf_path:
            break
        pdf_paths.append(pdf_path)

    if not pdf_paths:
        print("Error: No PDF files specified")
        return

    output = questionary.text("Enter output filename:", default='merged.pdf').ask()
    if not output:
        return

    from rich.progress import Progress

    with Progress() as progress:
        task = progress.add_task(f"Merging [bold green]{len(pdf_paths)}[/bold green] files into [bold blue]'{output}'[/bold blue]...", total=len(pdf_paths))
        merge_pdfs(pdf_paths, output, progress, task)

def reorder_cli():
    """Reorder pages in a PDF interactively."""
    pdf_path = questionary.text("Enter the path to the PDF file:", validate=lambda path: os.path.exists(path) and os.path.isfile(path) or "Invalid file path").ask()
    if not pdf_path:
        return
    print(f"Starting interactive reorder for '{pdf_path}'...")
    start_editor(pdf_path)
    print("Reorder session ended.")

def compress_cli():
    """Compress a PDF file."""
    input_path = questionary.text(
        "Compress PDF: Enter input file path",
        validate=lambda path: os.path.exists(path) and os.path.isfile(path) or "Invalid file path"
    ).ask()
    if not input_path:
        return

    output_path = questionary.text(
        "Compress PDF: Enter output file path (leave blank for compressed_[filename])",
        default=''
    ).ask()
    if not output_path:
        input_dir = os.path.dirname(input_path)
        input_filename = os.path.basename(input_path)
        name, ext = os.path.splitext(input_filename)
        output_path = os.path.join(input_dir, f"compressed_{name}{ext}")

    # Add questionary for quality
    quality_str = questionary.text("Enter compression quality (0.0 to 1.0, lower is more compression):", default='0.7').ask()
    try:
        quality = float(quality_str)
        if not 0.0 <= quality <= 1.0:
            print("Invalid quality value. Must be between 0.0 and 1.0. Using default 0.7")
            quality = 0.7
    except ValueError:
        print("Invalid quality value. Using default 0.7")
        quality = 0.7


    print(f"Compressing '{input_path}' to '{output_path}' with quality {quality}...")
    compressor = PDFCompressor(input_path)
    compressor.compress(quality=quality).save(output_path)
    print("Compression complete.")


def convert_file_type_cli():
    """File conversion tools."""
    convert_commands = {
        "PDF to Image": pdf_to_image_cli,
        "Image to PDF": image_to_pdf_cli,
        "Text to PDF": text_to_pdf_cli,
        "Markdown to PDF": markdown_to_pdf_cli,
        "HTML to PDF": html_to_pdf_cli,
        "Back to Main Menu": None
    }
    choice = questionary.select(
        "Convert File Type - Choose an operation:",
        choices=list(convert_commands.keys())
    ).ask()

    if choice and convert_commands[choice]:
        convert_commands[choice]()

def pdf_to_image_cli():
    """Convert PDF to images."""
    input_path = questionary.text("Enter the path to the PDF file:", validate=lambda path: os.path.exists(path) and os.path.isfile(path) or "Invalid file path").ask()
    if not input_path:
        return
    output_format = questionary.select(
        "Select output image format:",
        choices=['PNG', 'JPG'],
        default='PNG'
    ).ask()
    if not output_format:
        return
    pages = questionary.text("Enter page range (e.g., 1-5 or 3, leave blank for all pages):", default='').ask()

    page_range = None
    if pages:
        try:
            if '-' in pages:
                start, end = map(int, pages.split('-'))
                page_range = (start, end)
            else:
                page_range = (int(pages), int(pages))
        except ValueError:
            print("Invalid page range format. Converting all pages.")
            page_range = None

    print(f"Converting '{input_path}' to image(s)...")
    handle_conversion(input_path, PDFToImageConverter(), fmt=output_format, pages=page_range)
    print("Conversion complete.")

def image_to_pdf_cli():
    """Convert images to PDF."""
    input_path = questionary.text("Enter the path to the image file or folder:", validate=lambda path: os.path.exists(path) or "Path does not exist").ask()
    if not input_path:
        return
    print(f"Converting '{input_path}' to PDF...")
    handle_conversion(input_path, ImageToPDFConverter())
    print("Conversion complete.")

def text_to_pdf_cli():
    """Convert text files to PDF."""
    input_path = questionary.text("Enter the path to the text file or folder:", validate=lambda path: os.path.exists(path) or "Path does not exist").ask()
    if not input_path:
        return
    print(f"Converting '{input_path}' to PDF...")
    handle_conversion(input_path, TextToPDFConverter())
    print("Conversion complete.")

def markdown_to_pdf_cli():
    """Convert markdown files to PDF."""
    input_path = questionary.text("Enter the path to the markdown file or folder:", validate=lambda path: os.path.exists(path) or "Path does not exist").ask()
    if not input_path:
        return
    print(f"Converting '{input_path}' to PDF...")
    handle_conversion(input_path, MarkdownToPDFConverter())
    print("Conversion complete.")

def html_to_pdf_cli():
    """Convert HTML files/URLs to PDF."""
    input_path = questionary.text("Enter the path to the HTML file, folder, or URL:").ask()
    if not input_path:
        return
    print(f"Converting '{input_path}' to PDF...")
    handle_conversion(input_path, HTMLToPDFConverter())
    print("Conversion complete.")

def main():
    """Main procedure of the program."""
    while True:
        main_commands = {
            "Convert to Text": convert_to_text_cli,
            "Split PDF": split_cli,
            "Perform OCR": ocr_cli,
            "Merge PDFs": merge_cli,
            "Reorder Pages": reorder_cli,
            "Compress PDF": compress_cli,
            "Convert File Type": convert_file_type_cli,
            "Scan Image to PDF": scan_to_pdf_cli,
            "Exit": None
        }
        choice = questionary.select(
            "Omni PDF - Choose an operation:",
            choices=list(main_commands.keys())
        ).ask()

        if choice == "Exit":
            break
        elif choice and main_commands[choice]:
            main_commands[choice]()

if __name__ == '__main__':
    main()
