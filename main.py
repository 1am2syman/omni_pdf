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
from features.password_remover import remove_pdf_password_core, remove_passwords_from_folder_core, password_remover_bp # Import new feature
import threading
import webbrowser

# Register blueprints with the scanner_app if it's the central Flask app for web features
# This should be done before the app is run.
# If scanner_app is only for scanning, then password_remover might need its own app instance or be CLI-only.
# For now, let's assume scanner_app can host multiple web features.
scanner_app.register_blueprint(password_remover_bp, url_prefix='/password_remover')

def remove_password_cli():
    """Remove password from a PDF file or all PDF files in a folder."""
    process_type = questionary.select(
        "Remove PDF Password: Process a single file or a folder?",
        choices=["Single File", "Folder"],
        default="Single File"
    ).ask()

    if not process_type:
        return

    password = questionary.password("Enter PDF password (leave blank if none or to try empty):").ask()
    if password is None: # Handle Ctrl+C
        return

    if process_type == "Single File":
        pdf_path = questionary.text(
            "Enter PDF file path:",
            validate=lambda path: (os.path.exists(path) and os.path.isfile(path) and path.lower().endswith('.pdf')) or "Invalid PDF file path"
        ).ask()
        if not pdf_path:
            return

        output_folder_single = questionary.text(
            "Enter output folder for the decrypted file (default: 'decrypted_output'):",
            default='decrypted_output'
        ).ask()
        if output_folder_single is None: return # User pressed Ctrl+C

        # Determine absolute output path for single file
        if os.path.isabs(output_folder_single):
            absolute_output_folder = output_folder_single
        else:
            absolute_output_folder = os.path.abspath(output_folder_single)
        
        os.makedirs(absolute_output_folder, exist_ok=True)
        print(f"Attempting to remove password from '{os.path.basename(pdf_path)}'...")
        result = remove_pdf_password_core(pdf_path, password, absolute_output_folder)

        if result["status"] == "success":
            print(f"Successfully removed password. Decrypted file saved to: {result['output_path']}")
        elif result["status"] == "info":
            print(f"Info: {result['message']} Copied file to: {result['output_path']}")
        else:
            print(f"Error: {result['message']}")

    elif process_type == "Folder":
        input_folder_path = questionary.text(
            "Enter folder path containing PDFs:",
            validate=lambda path: (os.path.exists(path) and os.path.isdir(path)) or "Invalid folder path"
        ).ask()
        if not input_folder_path:
            return

        output_folder_folder = questionary.text(
            "Enter output folder (leave blank to save in the input folder, or specify a different one e.g. 'decrypted_output'):",
            default='' # Default is empty string, meaning use input folder
        ).ask()
        if output_folder_folder is None: return # User pressed Ctrl+C

        # Determine absolute output path for folder processing
        if not output_folder_folder: # User left it blank
            absolute_output_folder = os.path.abspath(input_folder_path)
        elif os.path.isabs(output_folder_folder):
            absolute_output_folder = output_folder_folder
        else:
            absolute_output_folder = os.path.abspath(output_folder_folder)

        os.makedirs(absolute_output_folder, exist_ok=True) # Core function also does this, but good to ensure
        print(f"Attempting to remove passwords from PDFs in folder '{input_folder_path}' (Output to: '{absolute_output_folder}')...")
        
        results = remove_passwords_from_folder_core(input_folder_path, password, absolute_output_folder)

        print(f"\n--- Folder Processing Summary ---")
        print(f"Status: {results.get('status')}")
        print(f"Message: {results.get('message')}")
        summary = results.get('summary', {})
        print(f"  Total Files Scanned: {summary.get('total_files_scanned', 0)}")
        print(f"  Successful Removals: {summary.get('successful_removals', 0)}")
        print(f"  Failed Removals: {summary.get('failed_removals', 0)}")
        print(f"  Not Encrypted/Copied: {summary.get('not_encrypted_or_copied', 0)}")
        
        if results.get("details"):
            print("\n--- File Details ---")
            for detail in results["details"]:
                print(f"  File: {detail['file_name']}")
                print(f"    Status: {detail['status']}")
                print(f"    Message: {detail['message']}")
                if "output_path" in detail:
                    print(f"    Output: {detail['output_path']}")
        print("-----------------------------")


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
    """Combine multiple PDFs into one file or merge all PDFs in a folder."""
    from features.merger import merge_pdfs, merge_pdfs_in_folder

    merge_type = questionary.select(
        "Merge PDFs: Merge individual files or all files in a folder?",
        choices=["Individual Files", "Folder"],
        default="Individual Files"
    ).ask()

    if not merge_type:
        return

    # Output path will be determined based on merge_type

    with Progress() as progress:
        if merge_type == "Individual Files":
            output_filename = questionary.text(
                "Enter output filename for merged PDF:",
                default='merged.pdf'
            ).ask()
            if not output_filename:
                return

            pdf_paths = []
            while True:
                pdf_path = questionary.text(
                    "Merge: Add PDF file (blank when done)",
                    validate=lambda path: os.path.exists(path) and os.path.isfile(path) and path.lower().endswith('.pdf') or "Invalid PDF file path"
                ).ask()
                if not pdf_path:
                    break
                pdf_paths.append(pdf_path)

            if not pdf_paths:
                print("Error: No PDF files specified")
                return

            task = progress.add_task(f"Merging [bold green]{len(pdf_paths)}[/bold green] files into [bold blue]'{output_filename}'[/bold blue]...", total=len(pdf_paths))
            merge_pdfs(pdf_paths, output_filename, progress, task)

        elif merge_type == "Folder":
            folder_path = questionary.text(
                "Enter folder path containing PDFs:",
                validate=lambda path: (os.path.exists(path) and os.path.isdir(path)) or "Invalid folder path"
            ).ask()
            if not folder_path:
                return

            default_output_name = 'merged.pdf'
            # Ensure folder_path is absolute for reliable os.path.join behavior and clear display
            abs_folder_path = os.path.abspath(folder_path)
            default_output_path = os.path.join(abs_folder_path, default_output_name)

            output_path_str = questionary.text(
                f"Enter output path for merged PDF (default: '{default_output_path}'):",
                default=default_output_path
            ).ask()
            if not output_path_str:
                return

            # Count PDF files in the folder for progress bar total
            try:
                pdf_files_in_folder = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
                num_files_in_folder = len(pdf_files_in_folder)
            except Exception:
                num_files_in_folder = 1 # Fallback

            task = progress.add_task(f"Merging files in [bold green]'{os.path.basename(folder_path)}'[/bold green] into [bold blue]'{os.path.basename(output_path_str)}'[/bold blue]...", total=num_files_in_folder)
            merge_pdfs_in_folder(folder_path, output_path_str, progress, task)

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
            "Remove PDF Password": remove_password_cli,
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
