import sys
import os
import PyPDF2
from tqdm import tqdm

def convert_pdf_to_text(pdf_path, output_format='txt'):
    """Converts a single PDF file to text or markdown with a progress bar."""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            # Wrap the page iteration with tqdm for a progress bar
            for page_num in tqdm(range(len(reader.pages)), desc=f"Converting '{os.path.basename(pdf_path)}'"):
                text += reader.pages[page_num].extract_text() or ""
                if output_format == 'md':
                    text += "\n\n---\n\n" # Add a separator for markdown pages
        
        output_path = os.path.splitext(pdf_path)[0] + f".{output_format}"
        with open(output_path, 'w', encoding='utf-8') as outfile:
            outfile.write(text)
        print(f"\nSuccessfully converted '{pdf_path}' to '{output_path}'") # Add newline after progress bar
    except FileNotFoundError:
        print(f"\nError: File not found at '{pdf_path}'") # Add newline
    except Exception as e:
        print(f"\nError converting '{pdf_path}': {e}") # Add newline

def convert_folder_pdfs_to_text(folder_path, output_format='txt'):
    """Converts all PDF files in a folder to text or markdown with progress bars."""
    if not os.path.isdir(folder_path):
        print(f"Error: Folder not found at '{folder_path}'")
        return

    pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")]
    # Wrap the file iteration with tqdm for a progress bar
    for filename in tqdm(pdf_files, desc=f"Processing folder '{os.path.basename(folder_path)}'"):
        pdf_path = os.path.join(folder_path, filename)
        convert_pdf_to_text(pdf_path, output_format)

def display_menu():
    """Displays the main menu of features."""
    print("\nPDF Swiss Army Knife - Choose a feature:")
    print("1. PDF to Text/Markdown Converter")
    print("2. PDF Splitter (Coming Soon)")
    print("3. Exit")

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
            pdf_path = input("Enter the path to the PDF file: ")
            convert_pdf_to_text(pdf_path, output_format)
        elif conversion_type == 'F':
            folder_path = input("Enter the path to the folder containing PDF files: ")
            convert_folder_pdfs_to_text(folder_path, output_format)
        else:
            print("Invalid conversion type. Please enter 'S' or 'F'.")

    elif choice == '2':
        print("\nPDF Splitter selected. This feature is coming soon.")
        pass
    elif choice == '3':
        print("Exiting PDF Swiss Army Knife. Goodbye!")
        sys.exit()
    else:
        print("Invalid choice. Please enter a number from the menu.")

def main():
    """Main function to run the PDF Swiss Army Knife."""
    while True:
        display_menu()
        choice = input("Enter your choice: ")
        handle_choice(choice)

if __name__ == "__main__":
    main()
