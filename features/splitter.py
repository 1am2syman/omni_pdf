"""PDF Splitter tool to split PDF files by page ranges.

This module provides a function to split a PDF file into multiple files based on specified page ranges.
It uses the `PyPDF2` library for PDF operations.
The progress bar is displayed on the console in real time using rich.
"""

import os
from PyPDF2 import PdfReader, PdfWriter
from rich.progress import Progress, TaskID

def split_pdf(pdf_path, page_ranges, output_dir=None, progress: Progress = None, task_id: TaskID = None):
    """Splits a PDF file into multiple files based on page ranges.

    Args:
        pdf_path (str): The path to the input PDF file.
        page_ranges (str): A string specifying the page ranges (e.g., "1-5,7,10-12").
        output_dir (str, optional): The directory to save the output files.
                                     Defaults to the same directory as the input file.
        progress: The rich Progress object for updating the progress bar.
        task_id: The rich TaskID for the specific task.
    """
    if not os.path.exists(pdf_path):
        if progress:
            progress.console.print(f"Error: Input PDF file not found at '{pdf_path}'")
        else:
            print(f"Error: Input PDF file not found at '{pdf_path}'")
        return

    try:
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
    except Exception as e:
        if progress:
            progress.console.print(f"Error reading PDF file '{pdf_path}': {e}")
        else:
            print(f"Error reading PDF file '{pdf_path}': {e}")
        return

    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    base_filename = os.path.splitext(os.path.basename(pdf_path))[0]

    ranges = []
    for part in page_ranges.split(','):
        part = part.strip()
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                ranges.append((start, end))
            except ValueError:
                if progress:
                    progress.console.print(f"Warning: Invalid range format '{part}'. Skipping.")
                else:
                    print(f"Warning: Invalid range format '{part}'. Skipping.")
        else:
            try:
                page_num = int(part)
                ranges.append((page_num, page_num))
            except ValueError:
                if progress:
                    progress.console.print(f"Warning: Invalid page number format '{part}'. Skipping.")
                else:
                    print(f"Warning: Invalid page number format '{part}'. Skipping.")

    if not ranges:
        if progress:
            progress.console.print("No valid page ranges specified.")
        else:
            print("No valid page ranges specified.")
        return

    total_tasks = len(ranges)
    if progress and task_id:
         progress.update(task_id, total=total_tasks)

    for i, (start_page, end_page) in enumerate(ranges):
        writer = PdfWriter()
        valid_pages_added = 0
        for page_num in range(start_page - 1, end_page):
            if 0 <= page_num < total_pages:
                writer.add_page(reader.pages[page_num])
                valid_pages_added += 1
            else:
                if progress:
                    progress.console.print(f"Warning: Page number {page_num + 1} is out of range.")
                else:
                    print(f"Warning: Page number {page_num + 1} is out of range.")

        if valid_pages_added > 0:
            output_filename = f"{base_filename}_part_{i+1}.pdf"
            if output_dir:
                output_path = os.path.join(output_dir, output_filename)
            else:
                output_path = os.path.join(os.path.dirname(pdf_path), output_filename)

            try:
                with open(output_path, 'wb') as outfile:
                    writer.write(outfile)
                if progress:
                    progress.console.print(f"Successfully created '{output_path}' with pages {start_page}-{end_page}")
                else:
                    print(f"Successfully created '{output_path}' with pages {start_page}-{end_page}")
            except Exception as e:
                if progress:
                    progress.console.print(f"Error writing output file '{output_path}': {e}")
                else:
                    print(f"Error writing output file '{output_path}': {e}")
        else:
            if progress:
                progress.console.print(f"No valid pages found for range {start_page}-{end_page}. Skipping output file creation.")
            else:
                print(f"No valid pages found for range {start_page}-{end_page}. Skipping output file creation.")

        if progress and task_id:
            progress.update(task_id, advance=1)


if __name__ == "__main__":
    # Retain old interactive mode for direct script execution
    import sys
    print("This script should be run through the main CLI interface.")
    sys.exit(1)
