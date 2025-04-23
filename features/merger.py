"""PDF Merger tool to merge PDF files as per user selection.

This module provides functions to merge PDF files either by manually selecting individual files
or by merging all PDF files in a folder. It uses the `fitz` library (PyMuPDF) for PDF operations.
The progress bar is displayed on the console in real time.
"""

import os
import sys
import fitz
from tqdm import tqdm

def merge_files(file_paths, output_file):
    """Merge a list of PDF files into a single PDF and save as output_file.

    Displays a real-time progress bar during processing using tqdm.
    """
    total_files = len(file_paths)
    if total_files == 0:
        print("No files to merge.")
        return

    try:
        # Create a new PDF document
        new_pdf = fitz.open()

        # Use tqdm for file iteration
        for file_path in tqdm(file_paths, desc="Merging PDFs"):
            try:
                # Open the input PDF document
                input_pdf = fitz.open(file_path)
                # Append pages from the input document to the new document
                new_pdf.insert_pdf(input_pdf)
                # Close the input document
                input_pdf.close()
            except Exception as e:
                print(f"\nError processing file {file_path}: {e}")
                # Continue with the next file even if one fails

        # Save the new document to the output file
        new_pdf.save(output_file, incremental=False)
        # Close the new document
        new_pdf.close()
        print(f"\nMerged {total_files} files into {output_file}") # Add newline after progress bar

    except Exception as e:
        print(f"\nError during merging: {e}") # Add newline

def merge_folder_pdfs(folder_path, output_file):
    """Merge all PDF files in the specified folder into a single PDF.
    
    The files are processed in the natural sequence as returned by os.listdir.
    """
    try:
        files = os.listdir(folder_path)
    except Exception as e:
        print(f"Error reading folder: {e}")
        return
    
    pdf_files = [os.path.join(folder_path, f) for f in files if f.lower().endswith('.pdf')]
    pdf_files.sort() # Sort files alphabetically for consistent order
    merge_files(pdf_files, output_file)

def merge_prompt():
    """Interactively prompt the user for merging PDFs either manually or by folder."""
    mode = input("Merge manually (M) or by folder (F)? (M/F): ").upper()

    if mode == 'M':
        files_input = input("Enter comma-separated paths of PDF files: ")
        raw_paths = [path.strip().strip('"') for path in files_input.split(',')]
        
        # Validate file paths
        file_paths = []
        valid = True
        for path in raw_paths:
            if not os.path.isfile(path):
                print(f"Error: File not found - {path}")
                valid = False
            elif not path.lower().endswith('.pdf'):
                print(f"Error: Not a PDF file - {path}")
                valid = False
            else:
                file_paths.append(path)
        
        if not valid:
            print("Aborting merge due to invalid file paths.")
            return
        if not file_paths:
            print("No valid PDF files provided.")
            return

        output_file = input("Enter the output file path (e.g., merged.pdf), leave blank for default in the first input file's folder: ").strip().strip('"')
        if not output_file:
            # Default to 'merged_manual.pdf' in the directory of the first input file
            first_file_dir = os.path.dirname(file_paths[0])
            output_file = os.path.join(first_file_dir, "merged_manual.pdf")
            print(f"Using default output file: {output_file}")
        elif not output_file.lower().endswith('.pdf'):
             output_file += ".pdf" # Ensure it has a .pdf extension

        merge_files(file_paths, output_file)

    elif mode == 'F':
        folder_path = input("Enter the folder path containing PDF files: ").strip().strip('"')
        
        # Validate folder path
        if not os.path.isdir(folder_path):
            print(f"Error: Folder not found or is not a directory - {folder_path}")
            return

        output_file = input("Enter the output file path (e.g., merged.pdf), leave blank for default in input folder: ").strip().strip('"')
        if not output_file:
            output_file = os.path.join(folder_path, "merged_folder.pdf")
            print(f"Using default output file: {output_file}")
        elif not output_file.lower().endswith('.pdf'):
             output_file += ".pdf" # Ensure it has a .pdf extension

        merge_folder_pdfs(folder_path, output_file)
        
    else:
        print("Invalid mode selected. Please enter 'M' or 'F'.")

if __name__ == "__main__":
    merge_prompt() # Run the interactive prompt when script is executed directly
