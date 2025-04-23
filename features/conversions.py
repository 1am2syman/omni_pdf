"""Conversion features for Omni PDF."""

import datetime as dt
import pathlib
import sys
import time
from contextlib import suppress
from timeit import default_timer as timer
# Removed subprocess import
import base64 # Import base64

import lxml
import openpyxl
import requests as rq
from bs4 import BeautifulSoup
from openpyxl.utils import get_column_letter
from PIL import Image
import markdown
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch # Import inch for spacing
# Removed httpx import
import PyPDF2
from selenium import webdriver # Import selenium
from selenium.webdriver.chrome.options import Options # Import ChromeOptions
from selenium.webdriver.chrome.service import Service # Import Service for ChromeDriver management
from selenium.common.exceptions import WebDriverException # Import WebDriverException

# Base Converter Class
class BaseConverter:
    def __init__(self):
        self.supported_inputs = []
        self.supported_outputs = {}

    def process(self, input_path, output_dir=None, **kwargs):
        raise NotImplementedError("Subclasses must implement this method")

# PDF to Image Converter
class PDFToImageConverter(BaseConverter):
    def __init__(self):
        super().__init__()
        self.supported_inputs = [".pdf"]
        # Corrected supported_outputs to include "JPG"
        self.supported_outputs = {"PNG": ".png", "JPEG": ".jpg", "JPG": ".jpg"}
        self.page_range_pattern = r"^\d+(-\d+)?$"

    def process(self, input_path, output_dir=None, pages=None, fmt="PNG"):
        from pdf2image import convert_from_path

        if input_path.suffix.lower() not in self.supported_inputs:
            print(f"Error: Unsupported input file type for PDF to Image conversion: {input_path.suffix}")
            return

        # Strip whitespace and check if the uppercase format is in supported_outputs keys
        output_format_key = fmt.strip().upper()
        if output_format_key not in self.supported_outputs:
             print(f"Error: Unsupported output format for PDF to Image conversion: {fmt}")
             return

        output_dir = output_dir if output_dir else input_path.parent
        output_path_base = output_dir / input_path.stem

        try:
            images = convert_from_path(
                input_path,
                output_folder=output_dir,
                first_page=pages[0] if pages else None,
                last_page=pages[1] if pages else None,
                fmt=output_format_key.lower() # pdf2image expects lowercase format
            )

            # pdf2image saves with a naming convention like output_path_base-0001.png
            print(f"Successfully converted {input_path.name} to image(s) in {output_dir}")

        except Exception as e:
            print(f"Error converting {input_path.name} to image(s): {e}")

# Image to PDF Converter
class ImageToPDFConverter(BaseConverter):
    def __init__(self):
        super().__init__()
        self.supported_inputs = [".png", ".jpg", ".jpeg"]
        self.supported_outputs = {"PDF": ".pdf"}

    def process(self, input_path, output_dir=None, **kwargs):
        if input_path.suffix.lower() not in self.supported_inputs:
            print(f"Error: Unsupported input file type for Image to PDF conversion: {input_path.suffix}")
            return

        output_dir = output_dir if output_dir else input_path.parent
        output_path = output_dir / f"{input_path.stem}.pdf"

        try:
            image = Image.open(input_path)
            image = image.convert("RGB")
            image.save(output_path)
            print(f"Successfully converted {input_path.name} to {output_path.name}")
        except Exception as e:
            print(f"Error converting {input_path.name} to PDF: {e}")


# Text to PDF Converter
class TextToPDFConverter(BaseConverter):
    def __init__(self):
        super().__init__()
        self.supported_inputs = [".txt"]
        self.supported_outputs = {"PDF": ".pdf"}

    def process(self, input_path, output_dir=None, **kwargs):
        if input_path.suffix.lower() not in self.supported_inputs:
            print(f"Error: Unsupported input file type for Text to PDF conversion: {input_path.suffix}")
            return

        output_dir = output_dir if output_dir else input_path.parent
        output_path = output_dir / f"{input_path.stem}.pdf"

        try:
            with open(input_path, "r", encoding="utf-8") as f:
                text_content = f.read()

            doc = SimpleDocTemplate(str(output_path), pagesize=letter)
            styles = getSampleStyleSheet()
            story = []

            # Add text content as paragraphs
            for line in text_content.splitlines():
                story.append(Paragraph(line, styles['Normal']))
                story.append(Spacer(1, 0.1 * inch)) # Add a small space between lines

            doc.build(story)

            print(f"Successfully converted {input_path.name} to {output_path.name}")
        except Exception as e:
            print(f"Error converting {input_path.name} to PDF: {e}")

# Markdown to PDF Converter
class MarkdownToPDFConverter(BaseConverter):
    def __init__(self):
        super().__init__()
        self.supported_inputs = [".md"]
        self.supported_outputs = {"PDF": ".pdf"}

    def process(self, input_path, output_dir=None, **kwargs):
        if input_path.suffix.lower() not in self.supported_inputs:
            print(f"Error: Unsupported input file type for Markdown to PDF conversion: {input_path.suffix}")
            return

        output_dir = output_dir if output_dir else input_path.parent
        output_path = output_dir / f"{input_path.stem}.pdf"

        try:
            with open(input_path, "r", encoding="utf-8") as f:
                md_content = f.read()

            html_content = markdown.markdown(md_content)

            doc = SimpleDocTemplate(str(output_path), pagesize=letter)
            styles = getSampleStyleSheet()
            story = []

            # Basic conversion of HTML from Markdown to ReportLab elements
            # This is a simplified approach and may not handle complex HTML/Markdown
            from html.parser import HTMLParser

            class ReportLabHTMLParser(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.story = []
                    self.current_style = styles['Normal']
                    self.ignore_data = False # Flag to ignore data within certain tags

                def handle_starttag(self, tag, attrs):
                    if tag == 'strong' or tag == 'b':
                        self.current_style = styles['h3'] # Use a different style for bold
                    elif tag == 'em' or tag == 'i':
                         self.current_style = styles['Italic']
                    elif tag == 'h1':
                        self.current_style = styles['h1']
                    elif tag == 'h2':
                        self.current_style = styles['h2']
                    elif tag == 'h3':
                        self.current_style = styles['h3']
                    elif tag == 'p':
                        self.current_style = styles['Normal']
                    elif tag == 'img':
                        # Ignore img tags for now to avoid paraparser errors
                        self.ignore_data = True


                def handle_endtag(self, tag):
                     if tag in ['strong', 'b', 'em', 'i', 'h1', 'h2', 'h3', 'p']:
                         self.current_style = styles['Normal']
                     elif tag == 'img':
                         self.ignore_data = False


                def handle_data(self, data):
                    if not self.ignore_data and data.strip():
                        self.story.append(Paragraph(data, self.current_style))
                        self.story.append(Spacer(1, 0.1 * inch))

            parser = ReportLabHTMLParser()
            parser.feed(html_content)
            story = parser.story

            doc.build(story)

            print(f"Successfully converted {input_path.name} to {output_path.name}")
        except Exception as e:
            print(f"Error converting {input_path.name} to PDF: {e}")

# HTML to PDF Converter
class HTMLToPDFConverter(BaseConverter):
    def __init__(self):
        super().__init__()
        self.supported_inputs = [".html", ".htm"]
        self.supported_outputs = {"PDF": ".pdf"}

    def process(self, input_path, output_dir=None, **kwargs):
        driver = None # Initialize driver to None
        try:
            # Configure Chrome options for headless mode
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")

            # Initialize ChromeDriver
            # Assumes ChromeDriver is in the system's PATH or in the same directory
            driver = webdriver.Chrome(options=chrome_options)

            # Navigate to the input path (URL or local file)
            if isinstance(input_path, pathlib.Path):
                 # Convert local file path to a URL
                 input_url = f"file:///{input_path.resolve()}"
            elif isinstance(input_path, str) and "://" in input_path:
                 input_url = input_path
            else:
                 print(f"Error: Invalid input type for HTML to PDF conversion: {input_path}")
                 return

            driver.get(input_url)

            # Wait for the page to load (adjust time as needed)
            time.sleep(2) # Simple wait, consider more robust waiting strategies

            # Get PDF data using DevTools protocol command
            # This requires Chrome 78 or later
            pdf_options = {
                'printBackground': True
            }
            pdf_data = driver.execute_cdp_cmd("Page.printToPDF", pdf_options)

            # Determine output path
            output_dir = output_dir if output_dir else pathlib.Path(".")
            if isinstance(input_path, pathlib.Path):
                 output_path = output_dir / f"{input_path.stem}.pdf"
            else:
                 # For URLs, create a filename from the URL or use a default
                 url_parts = input_path.replace("http://", "").replace("https://", "").split("/")
                 filename = url_parts[0].replace(".", "_") + ".pdf" if url_parts else "webpage.pdf"
                 output_path = output_dir / filename


            # Write PDF data to file
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(pdf_data['data']))

            print(f"Successfully converted {input_path} to {output_path.name}")

        except WebDriverException as e:
            print(f"WebDriver error during conversion: {e}")
            print("Please ensure you have Chrome installed and a compatible ChromeDriver in your system's PATH.")
            print("ChromeDriver download: https://chromedriver.chromium.org/downloads")
        except Exception as e:
            print(f"An unexpected error occurred during conversion: {e}")
        finally:
            if driver:
                driver.quit() # Ensure the browser is closed


# Helper function to handle single file or folder processing
def handle_conversion(input_path, converter, **kwargs):
    # Check if input_path is a URL string
    if isinstance(input_path, str) and "://" in input_path:
        print(f"Processing URL: {input_path}")
        converter.process(input_path, **kwargs)
    else:
        # Treat as a file or directory path
        input_path = pathlib.Path(input_path)
        if input_path.is_dir():
            print(f"Processing folder: {input_path}")
            for file in input_path.iterdir():
                if file.suffix.lower() in converter.supported_inputs:
                    converter.process(file, output_dir=input_path, **kwargs)
                else:
                    print(f"Skipping unsupported file in folder: {file.name}")
        elif input_path.is_file():
            print(f"Processing file: {input_path}")
            converter.process(input_path, **kwargs)
        else:
            print(f"Error: Invalid input path: {input_path}")
