"""PDF Merger tool to merge PDF files.

This module provides functions to merge PDF files. It uses the `fitz` library (PyMuPDF) for PDF operations.
The progress bar is displayed on the console in real time.
"""

import os
import fitz
from rich.progress import Progress, TaskID

def merge_pdfs(file_paths, output_file, progress: Progress, task_id: TaskID):
    """Merge a list of PDF files into a single PDF and save as output_file.

    Args:
        file_paths: List of file paths to merge
        output_file: Path for output merged PDF file
        progress: The rich Progress object for updating the progress bar.
        task_id: The rich TaskID for the specific task.
    """
    total_files = len(file_paths)
    if total_files == 0:
        progress.console.print("No files to merge.")
        return False

    try:
        # Create a new PDF document
        new_pdf = fitz.open()

        # Iterate through files and update progress
        for i, file_path in enumerate(file_paths):
            try:
                # Open the input PDF document
                input_pdf = fitz.open(file_path)
                # Append pages from the input document to the new document
                new_pdf.insert_pdf(input_pdf)
                # Close the input document
                input_pdf.close()
                progress.update(task_id, advance=1)
            except Exception as e:
                progress.console.print(f"\nError processing file {file_path}: {e}")
                # Continue with the next file even if one fails

        # Save the new document to the output file
        new_pdf.save(output_file, incremental=False)
        # Close the new document
        new_pdf.close()
        progress.console.print(f"\nSuccessfully merged {total_files} files into {output_file}")
        return True

    except Exception as e:
        progress.console.print(f"\nError during merging: {e}")
        return False


def merge_pdfs_in_folder(folder_path, output_file, progress: Progress, task_id: TaskID):
    """Merge all PDF files in the specified folder into a single PDF.

    Args:
        folder_path: Path to folder containing PDFs
        output_file: Path for output merged PDF file
        progress: The rich Progress object for updating the progress bar.
        task_id: The rich TaskID for the specific task.
    """
    try:
        files = os.listdir(folder_path)
    except Exception as e:
        if progress:
            progress.console.print(f"Error reading folder: {e}")
        else:
            print(f"Error reading folder: {e}")
        return False
    
    pdf_files = [os.path.join(folder_path, f) for f in files if f.lower().endswith('.pdf')]
    pdf_files.sort() # Sort files alphabetically for consistent order
    return merge_pdfs(pdf_files, output_file, progress, task_id)

if __name__ == "__main__":
    # Retain old interactive mode for direct script execution
    import sys
    print("This script should be run through the main CLI interface.")
    sys.exit(1)
