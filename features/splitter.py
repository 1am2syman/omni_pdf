import os
import fitz  # Import PyMuPDF
from tqdm import tqdm

def split_pdf(pdf_path, page_ranges, output_dir=None):
    """Splits a PDF file into multiple files based on page ranges with a progress bar using PyMuPDF."""
    try:
        # Use fitz.open() to open the PDF
        doc = fitz.open(pdf_path)
        total_pages = doc.page_count

        if output_dir is None:
            output_dir = os.path.dirname(pdf_path)
        os.makedirs(output_dir, exist_ok=True)

        base_filename = os.path.splitext(os.path.basename(pdf_path))[0]

        split_jobs = []
        for range_str in page_ranges.split(','):
            range_str = range_str.strip()
            if '-' in range_str:
                start_end = range_str.split('-')
                if len(start_end) == 2:
                    try:
                        start_page = int(start_end[0])
                        end_page = int(start_end[1])
                        if 1 <= start_page <= end_page <= total_pages:
                            split_jobs.append((start_page, end_page))
                        else:
                            print(f"Warning: Invalid page range '{range_str}' for '{os.path.basename(pdf_path)}'. Skipping.")
                    except ValueError:
                        print(f"Warning: Invalid page range format '{range_str}'. Skipping.")
                else:
                     print(f"Warning: Invalid page range format '{range_str}'. Skipping.")
            else:
                try:
                    page = int(range_str)
                    if 1 <= page <= total_pages:
                        split_jobs.append((page, page))
                    else:
                         print(f"Warning: Invalid page number '{range_str}' for '{os.path.basename(pdf_path)}'. Skipping.")
                except ValueError:
                    print(f"Warning: Invalid page number format '{range_str}'. Skipping.")

        if not split_jobs:
            print(f"No valid page ranges provided for '{os.path.basename(pdf_path)}'. No files will be split.")
            doc.close() # Close the document
            return

        # Determine pages included in split jobs
        included_pages = set()
        for start_page, end_page in split_jobs:
            for page_num in range(start_page, end_page + 1):
                included_pages.add(page_num)

        # Find leftover pages
        all_pages = set(range(1, total_pages + 1))
        leftover_pages = sorted(list(all_pages - included_pages))

        # Add leftover pages as a split job if they exist
        if leftover_pages:
            # Consolidate consecutive leftover pages into ranges
            leftover_ranges = []
            if leftover_pages:
                start_range = leftover_pages[0]
                end_range = leftover_pages[0]
                for i in range(1, len(leftover_pages)):
                    if leftover_pages[i] == end_range + 1:
                        end_range = leftover_pages[i]
                    else:
                        leftover_ranges.append((start_range, end_range))
                        start_range = leftover_pages[i]
                        end_range = leftover_pages[i]
                leftover_ranges.append((start_range, end_range)) # Add the last range

            for start_page, end_page in leftover_ranges:
                 split_jobs.append((start_page, end_page))


        # Sort split jobs by start page
        split_jobs.sort()

        for i, (start_page, end_page) in enumerate(tqdm(split_jobs, desc=f"Splitting '{os.path.basename(pdf_path)}'")):
            # Create a new PDF document for each split job
            new_pdf = fitz.open()
            for page_num in range(start_page - 1, end_page):
                # Copy pages from the original document to the new one
                new_pdf.insert_pdf(doc, from_page=page_num, to_page=page_num)

            if (start_page, end_page) in leftover_ranges:
                 output_filename = f"{base_filename}_leftover_pages_{start_page}-{end_page}.pdf"
            else:
                output_filename = f"{base_filename}_pages_{start_page}-{end_page}.pdf"

            output_path = os.path.join(output_dir, output_filename)

            # Save the new PDF
            new_pdf.save(output_path)
            new_pdf.close() # Close the new document

        doc.close() # Close the original document

        print(f"\nSuccessfully split '{os.path.basename(pdf_path)}' into {len(split_jobs)} files in '{output_dir}'")

    except FileNotFoundError:
        print(f"\nError: File not found at '{pdf_path}')")
    except Exception as e:
        print(f"\nError splitting '{pdf_path}': {e}")
