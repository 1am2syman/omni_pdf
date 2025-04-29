"""PDF compression feature for the Omni PDF tool using Ghostscript via subprocess.
This implementation replaces the pikepdf and siuba dependencies with a Ghostscript call,
and utilizes method chaining.

Usage:
    compressor = PDFCompressor("input.pdf").compress(quality=0.5).save()
    # If quality is:
    #   < 0.33: uses '/screen' preset (maximum compression, lower quality)
    #   0.33 - 0.66: uses '/ebook' preset (moderate compression)
    #   >= 0.66: uses '/printer' preset (minimal compression, higher quality)
"""

import pathlib
import sys
import subprocess
from contextlib import suppress

# Determine the folder based on whether running from EXE or script.
if hasattr(sys, "_MEIPASS"):
    # Running from the EXE.
    FOLDER = pathlib.Path(sys.executable).parent
else:
    # Running as the script.
    FOLDER = pathlib.Path(__file__).parent

class PDFCompressor:
    """
    A class to handle PDF compression with a fluent interface,
    replacing the pikepdf and siuba-based implementations with a Ghostscript-based method.
    """
    def __init__(self, input_pdf: str):
        """
        Initializes the PDFCompressor with the input PDF path.

        Args:
            input_pdf: The path to the input PDF file.
        """
        self.input_pdf = pathlib.Path(input_pdf)
        self.quality = 0.5  # default quality

    def compress(self, quality: float = 0.5):
        """
        Verifies the input file and stores the quality parameter.
        This method is provided for method chaining.

        Args:
            quality: The compression quality (0.0 to 1.0). Lower means more compression.
                     The quality is mapped to Ghostscript presets:
                         < 0.33: '/screen'
                         0.33-0.66: '/ebook'
                         >= 0.66: '/printer'
        """
        if not self.input_pdf.exists():
            print(f"Error: Input file not found at {self.input_pdf}")
        else:
            print(f"Input file {self.input_pdf} found for compression.")
        self.quality = quality
        return self

    def save(self, output_pdf: str = None):
        """
        Compresses and saves the PDF using Ghostscript.
        If no output path is provided, saves to the input folder with a "_compressed" suffix.

        Args:
            output_pdf: The path to save the compressed PDF.
        """
        if not self.input_pdf.exists():
            print("Error: No valid PDF loaded for compression.")
            return self

        if output_pdf is None:
            output_path = self.input_pdf.parent / f"{self.input_pdf.stem}_compressed{self.input_pdf.suffix}"
        else:
            output_path = pathlib.Path(output_pdf)

        # Map quality value to Ghostscript PDFSETTINGS
        if self.quality < 0.33:
            pdf_settings = "/screen"
        elif self.quality < 0.66:
            pdf_settings = "/ebook"
        else:
            pdf_settings = "/printer"

        command = [
            "gswin64c",
            "-sDEVICE=pdfwrite",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            "-dSAFER",
            "-dCompatibilityLevel=1.4",
            f"-dPDFSETTINGS={pdf_settings}",
            f"-sOutputFile={str(output_path)}",
            str(self.input_pdf)
        ]

        try:
            subprocess.run(command, check=True)
            print(f"Successfully saved compressed PDF to {output_path}")
        except subprocess.CalledProcessError as e:
            print(f"Error during PDF compression: {e}")

        return self
