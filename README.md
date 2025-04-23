# Omni PDF

A versatile command-line tool for various PDF manipulation tasks.

## Features

- **PDF to Text/Markdown Converter:** Convert single or multiple PDF files in a folder to plain text (.txt) or Markdown (.md) format using OCR when necessary, with a progress bar.
- **PDF Splitter:** Split a PDF file into multiple files based on specified page ranges, with an option to handle leftover pages.
- **PDF Merger:** Merge multiple PDF files into a single PDF, either by selecting individual files or merging all files in a folder.
- **PDF OCR:** Perform Optical Character Recognition on PDF files to create searchable PDFs or extract text.
- **PDF Reorder and Rotate:** Reorder and rotate pages of a PDF file using a web-based editor.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone [repository_url]
    ```
    Replace `[repository_url]` with the actual URL of the GitHub repository after it's created.

2.  **Navigate to the project directory:**
    ```bash
    cd omni_pdf
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

Run the tool from the command line and follow the on-screen menu to select and use the desired feature.

```bash
python main.py
```

### PDF to Text/Markdown Converter

This feature converts PDF files to either plain text (`.txt`) or Markdown (`.md`) format. It automatically uses OCR if direct text extraction is not possible.

1.  Select option `1` from the main menu.
2.  Choose whether to convert a single file (`S`) or all PDF files in a folder (`F`).
3.  Provide the full path to the PDF file or the folder containing the PDF files.
4.  Choose the output format by entering `txt` or `md`.
5.  The converted file(s) will be saved in the same directory as the original PDF(s) with a `.txt` or `.md` extension.

### PDF Splitter

This feature allows you to split a single PDF file into multiple new PDF files based on specified page ranges.

1.  Select option `2` from the main menu.
2.  Provide the full path to the PDF file you want to split.
3.  Enter the page ranges you want to split. Use commas to separate ranges and hyphens for consecutive pages (e.g., `1-5, 7, 10-12`). Pages not included in any specified range will be saved as a separate "leftover" file.
4.  Optionally, provide a full path to an output directory where the split files will be saved. If left blank, the files will be saved in the same directory as the original PDF.
5.  The split PDF files will be created in the specified output directory.

### PDF Merger

This feature allows you to combine multiple PDF files into a single PDF file.

1.  Select option `3` from the main menu.
2.  Choose whether to merge files by manually selecting individual files (`M`) or by merging all PDF files in a specified folder (`F`).
3.  If merging manually (`M`):
    -   Enter the full paths of the PDF files you want to merge, separated by commas.
    -   Enter the full path for the output merged PDF file. If left blank, a default filename (`merged_manual.pdf`) will be used in the directory of the first input file.
4.  If merging by folder (`F`):
    -   Enter the full path to the folder containing the PDF files you want to merge.
    -   Enter the full path for the output merged PDF file. If left blank, a default filename (`merged_folder.pdf`) will be used in the input folder.
5.  The merged PDF file will be saved to the specified output path.

### PDF OCR

This feature performs Optical Character Recognition on PDF files to make them searchable or extract text from images within the PDF.

1.  Select option `4` from the main menu.
2.  Choose whether to process a single file (`S`) or all PDF files in a folder (`F`).
3.  Provide the full path to the PDF file or the folder containing the PDF files.
4.  Choose the output type: `text` to extract text using OCR, or `pdf` to create a new searchable PDF with an invisible text layer.
5.  If output type is `text`, choose the output format (`txt` or `md`).
6.  Optionally, choose to force OCR even if the page contains extractable text (enter `yes` or `no`).
7.  The output file(s) will be saved with `.ocr.txt`, `.ocr.md`, or `.searchable.pdf` appended to the original filename, in the same directory as the original file(s).

### PDF Reorder and Rotate

This feature provides a web-based interface to visually reorder and rotate the pages of a PDF file.

1.  Select option `5` from the main menu.
2.  Enter the full path to the PDF file you want to reorder and rotate.
3.  A web browser window will automatically open, displaying thumbnails of the PDF pages.
4.  In the web interface, drag and drop the page thumbnails to change their order. Use the rotate buttons on each thumbnail to rotate individual pages.
5.  Click the "Complete Reordering" button in the web interface.
6.  The reordered and rotated PDF will be saved as a new file in the same directory as the original PDF, with `_reordered` appended to the original filename.

## Contributing

Contributions are welcome! Please feel free to open issues or submit pull requests.

## License

[Add License Information Here - e.g., MIT, Apache 2.0]
