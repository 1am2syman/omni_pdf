import sys
import os
from features.converter import convert_pdf_to_text, convert_folder_pdfs_to_text
from features.splitter import split_pdf

def display_menu():
    """Displays the main menu of features."""
    print("\nOmni PDF - Choose a feature:")
    print("1. PDF to Text/Markdown Converter")
    print("2. PDF Splitter")
    print("3. PDF OCR (PaddleOCR)")
    print("4. Exit")

def handle_choice(choice):
    """Handles the user's menu choice."""
    if choice == '1':
        print("\nPDF to Text/Markdown Converter selected.")
        conversion_type = input("Convert (S)ingle file or (F)older? (S/F): ").upper()
        output_format = input("Output format (txt/md): ").lower()
        if output_format not in ['txt', 'md']:
            print("Invalid output format. Defaulting to txt.")
            output_format = 'txt'

        if conversion_type == 'S':
            pdf_path = input("Enter the path to the PDF file: ").strip('"')
            convert_pdf_to_text(pdf_path, output_format)
        elif conversion_type == 'F':
            folder_path = input("Enter the path to the folder containing PDF files: ").strip('"')
            convert_folder_pdfs_to_text(folder_path, output_format) # Corrected output_path to output_format
        else:
            print("Invalid conversion type. Please enter 'S' or 'F'.")

    elif choice == '2':
        print("\nPDF Splitter selected.")
        pdf_path = input("Enter the path to the PDF file to split: ").strip('"')
        page_ranges_str = input("Enter page ranges to split (e.g., 1-5, 7, 10-12): ")
        output_dir = input("Enter output directory (leave blank for input folder): ").strip('"') or None
        split_pdf(pdf_path, page_ranges_str, output_dir)

    elif choice == '3':
        print("\nPDF OCR (PaddleOCR) selected.")
        from features.ocr import convert_pdf_to_ocr, ocr_folder_pdfs # Import OCR functions (updated function name)
        ocr_type = input("Perform OCR on (S)ingle file or (F)older? (S/F): ").upper()

        # Prompt for output type: Text or Searchable PDF
        output_type_input = input("Output as (T)ext (.txt/.md) or (S)earchable PDF (.pdf)? (T/S): ").upper()
        if output_type_input == 'T':
            output_type = 'text'
            output_format = input("Text output format (txt/md): ").lower()
            if output_format not in ['txt', 'md']:
                print("Invalid text output format. Defaulting to txt.")
                output_format = 'txt'
        elif output_type_input == 'S':
            output_type = 'pdf'
            output_format = 'pdf' # Output format is fixed for PDF
        else:
            print("Invalid output type. Defaulting to Text (.txt).")
            output_type = 'text'
            output_format = 'txt'

        force_ocr_input = input("Force OCR on all pages (Y/N)? (Default is intelligent detection for text, always OCR for PDF): ").upper()
        force_ocr = force_ocr_input == 'Y'

        if ocr_type == 'S':
            pdf_path = input("Enter the path to the PDF file: ").strip('"')
            convert_pdf_to_ocr(pdf_path, output_type, output_format, force_ocr) # Pass output_type
        elif ocr_type == 'F':
            folder_path = input("Enter the path to the folder containing PDF files: ").strip('"')
            ocr_folder_pdfs(folder_path, output_type, output_format, force_ocr) # Pass output_type
        else:
            print("Invalid OCR type. Please enter 'S' or 'F'.")

    elif choice == '4':
        print("Exiting Omni PDF. Goodbye!")
        sys.exit()
    else:
        print("Invalid choice. Please enter a number from the menu.")

def main():
    """Main function to run Omni PDF."""
    while True:
        display_menu()
        choice = input("Enter your choice: ")
        handle_choice(choice)

if __name__ == "__main__":
    main()
