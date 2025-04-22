# Omni PDF

A versatile command-line tool for various PDF manipulation tasks.

## Features

- **PDF to Text/Markdown Converter:** Convert single or multiple PDF files in a folder to plain text (.txt) or Markdown (.md) format using OCR when necessary, with a progress bar.
- **PDF Splitter:** (Coming Soon)

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

The PDF to Text/Markdown Converter feature automatically utilizes OCR (Optical Character Recognition) when it cannot extract text directly from the PDF or when creating searchable PDF output (if implemented).

1.  **Run the tool:**
    ```bash
    python main.py
    ```

2.  **Follow the on-screen menu:**
    -   Choose '1' for the PDF to Text/Markdown Converter.
    -   Select whether to convert a single file ('S') or a folder ('F').
    -   Provide the path to the PDF file or folder.
    -   Choose the output format (.txt or .md).

## Contributing

Contributions are welcome! Please feel free to open issues or submit pull requests.

## License

[Add License Information Here - e.g., MIT, Apache 2.0]
