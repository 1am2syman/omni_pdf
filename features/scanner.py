"""Module for scanning images to PDF with a local web interface."""

import datetime as dt
import pathlib
import sys
import time
from contextlib import suppress
from timeit import default_timer as timer

import lxml
import openpyxl
import requests as rq
from bs4 import BeautifulSoup
from openpyxl.utils import get_column_letter

import cv2
import numpy as np
from flask import Flask, render_template, request, jsonify, send_from_directory
from PIL import Image, ImageEnhance, ImageFilter # Keep Pillow for compatibility
import img2pdf
import os
import urllib.parse
import tempfile

# Initialize Flask app
app = Flask(__name__, template_folder='../templates')

# Temporary storage for processed images
# Key: original_image_path, Value: processed_image_object
processed_images_data = {}
original_image_order = [] # To maintain the order of images

# Placeholder for image processing functions
def process_image(image_path, crop_coords, brightness=1.0, contrast=1.5, sharpness=1.0, rotation=0):
    """Processes a single image with cropping and enhancements using OpenCV."""
    try:
        # Read image using OpenCV
        img_cv = cv2.imread(image_path)

        if img_cv is None:
            print(f"Error: Could not read image {image_path}")
            return None

        # Apply rotation using OpenCV
        if rotation != 0:
            # OpenCV rotation codes for 90, 180, 270 degrees
            if rotation == 90:
                rotate_code = cv2.ROTATE_90_CLOCKWISE
            elif rotation == 180:
                rotate_code = cv2.ROTATE_180
            elif rotation == 270:
                rotate_code = cv2.ROTATE_90_COUNTERCLOCKWISE
            else:
                rotate_code = cv2.ROTATE_180 # Default for other angles, though frontend sends 0, 90, 180, 270

            img_cv = cv2.rotate(img_cv, rotate_code)


        # Convert to grayscale for processing
        gray_cv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

        # Apply de-smudging (e.g., using a bilateral filter which is good at noise reduction while preserving edges)
        # Parameters: source, diameter of pixel neighborhood, sigmaColor, sigmaSpace
        denoised_cv = cv2.bilateralFilter(gray_cv, 9, 75, 75)

        # Apply adaptive thresholding for better contrast and scanned look
        # This is often more effective than simple contrast adjustment for documents
        processed_cv = cv2.adaptiveThreshold(denoised_cv, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)

        # Note: Brightness, Contrast, and Sharpness adjustments are less common
        # after adaptive thresholding as the image is already binary (black and white).
        # If color or grayscale output is desired, these could be applied before thresholding.
        # For a typical "scanned document" look (black and white), adaptive thresholding is key.
        # We will keep the parameters in the function signature but they might not have
        # a significant effect after thresholding. If a grayscale output with these
        # adjustments is needed, the thresholding step would need to be conditional or removed.
        # Let's assume a black and white scanned look is the primary goal after de-smudging.

        # If a grayscale output with enhancements is preferred, uncomment and adjust these lines:
        # img_pil = Image.fromarray(denoised_cv)
        # enhancer = ImageEnhance.Brightness(img_pil)
        # img_pil = enhancer.enhance(brightness)
        # enhancer = ImageEnhance.Contrast(img_pil)
        # img_pil = enhancer.enhance(contrast)
        # enhancer = ImageEnhance.Sharpness(img_pil)
        # img_pil = enhancer.enhance(sharpness)
        # processed_cv = np.array(img_pil)


        # Apply crop using OpenCV (coordinates need to be integers)
        if crop_coords:
             x, y, w, h = int(crop_coords['x']), int(crop_coords['y']), int(crop_coords['width']), int(crop_coords['height'])
             # Ensure crop coordinates are within image bounds
             h_cv, w_cv = processed_cv.shape[:2]
             x = max(0, x)
             y = max(0, y)
             w = min(w, w_cv - x)
             h = min(h, h_cv - y)
             processed_cv = processed_cv[y:y+h, x:x+w]


        # Convert the processed OpenCV image (which is grayscale/binary) back to Pillow Image
        # If the OpenCV image is binary (from adaptive thresholding), it's 1 channel.
        # Convert to RGB for compatibility with img2pdf if needed, although img2pdf
        # can often handle grayscale. Let's convert to RGB for consistency.
        if len(processed_cv.shape) == 2: # Check if it's grayscale/binary
             processed_pil = Image.fromarray(processed_cv, 'L') # 'L' for grayscale
             processed_pil = processed_pil.convert('RGB') # Convert to RGB
        else: # If somehow it's still color (unlikely after steps above, but for safety)
             processed_pil = Image.fromarray(cv2.cvtColor(processed_cv, cv2.COLOR_BGR2RGB))


        return processed_pil
    except Exception as e:
        print(f"Error processing image with OpenCV {image_path}: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_pdf(images, output_path):
    """Creates a PDF from a list of processed images."""
    try:
        if not images:
            print("Error creating PDF: No images provided.")
            return False

        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)
        print(f"Attempting to save PDF to: {output_path}")

        with open(output_path, "wb") as f:
            f.write(img2pdf.convert(images))

        print(f"PDF successfully created at: {output_path}")
        return True
    except Exception as e:
        print(f"Error creating PDF: {e}")
        # Log the traceback for more detailed debugging
        import traceback
        traceback.print_exc()
        return False

# Flask routes
@app.route('/scan')
def scan_interface():
    """Renders the scan interface and passes image paths."""
    global original_image_order, processed_images_data
    processed_images_data = {} # Clear previous data
    original_image_order = [] # Clear previous order

    image_paths_str = request.args.get('image_paths')
    if not image_paths_str:
        return "Error: Image paths not provided.", 400

    try:
        # Decode and split the comma-separated image paths
        image_paths = urllib.parse.unquote_plus(image_paths_str).split(',')
        original_image_order = image_paths # Store the original order

        # Validate paths exist
        valid_image_paths = [path for path in image_paths if os.path.exists(path)]
        if len(valid_image_paths) != len(image_paths):
            print("Warning: Some image paths provided do not exist.")
        image_paths = valid_image_paths

        # If decoding and validation are successful, proceed
        output_folder = request.args.get('output_folder', '') # Get output_folder from URL parameter

        if not image_paths:
            return "Error: No valid image paths found.", 400

        # Get the directory of the first image
        image_directory = os.path.dirname(image_paths[0]) if image_paths else ''

        # Prepare a list of dictionaries with full path and filename
        images_data = [{'full_path': p, 'filename': os.path.basename(p)} for p in image_paths]

        # Pass the list of image data and output_folder to the template
        return render_template('scan.html', images_data=images_data, output_folder=output_folder)

    except Exception as e:
        print(f"Exception type: {type(e)}")
        print(f"Exception value: {e}")
        return f"Error processing image paths: {e}", 500


@app.route('/process', methods=['POST'])
def process_scan():
    """Receives image data and processing parameters and processes a single image."""
    data = request.json
    image_path = data.get('image_path')
    crop_coords = data.get('crop_coords')
    brightness = data.get('brightness', 1.0) # Get brightness, default to 1.0
    contrast = data.get('contrast', 1.0)     # Get contrast, default to 1.0
    sharpness = data.get('sharpness', 1.0)   # Get sharpness, default to 1.0
    rotation = data.get('rotation', 0)       # Get rotation, default to 0
    output_folder = data.get('output_folder')

    if not image_path or not os.path.exists(image_path):
        return jsonify({"status": "error", "message": "Image path not provided or does not exist."}), 400

    processed_image = process_image(image_path, crop_coords, brightness, contrast, sharpness, rotation)

    if processed_image:
        # Save the processed image to a temporary file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
            processed_image_path = tmp_file.name
            processed_image.save(processed_image_path)

        # --- Debugging Step: Save a copy of the processed image for inspection ---
        debug_output_path = os.path.join(tempfile.gettempdir(), f"debug_processed_{int(time.time())}.png")
        try:
            processed_image.save(debug_output_path)
            print(f"Debug: Saved processed image to {debug_output_path}")
        except Exception as e:
            print(f"Debug: Failed to save debug image: {e}")
        # --- End Debugging Step ---


        # Store the path of the temporary file
        processed_images_data[image_path] = processed_image_path
        return jsonify({"status": "success", "message": "Image processed successfully."})
    else:
        return jsonify({"status": "error", "message": "Failed to process image."}), 500

@app.route('/create_final_pdf', methods=['POST'])
def create_final_pdf():
    """Creates the final PDF from all processed images."""
    global processed_images_data, original_image_order

    data = request.json
    output_folder = data.get('output_folder')

    if not original_image_order or not processed_images_data:
         return jsonify({"status": "error", "message": "No processed images found."}), 400

    # Get the paths of the temporary processed image files in the original order
    processed_image_paths = []
    for original_path in original_image_order:
        if original_path in processed_images_data:
            processed_image_paths.append(processed_images_data[original_path])

    if not processed_image_paths:
        return jsonify({"status": "error", "message": "No processed images found for PDF creation."}), 400

    # Determine output path for the PDF
    # Use the directory of the first image if no output_folder is provided
    if output_folder:
        output_dir = output_folder
    elif original_image_order:
        output_dir = os.path.dirname(original_image_order[0])
    else:
        output_dir = "." # Default to current directory if no images were processed

    # Generate a unique filename for the PDF
    timestamp = int(time.time())
    output_pdf_filename = f"scanned_document_{timestamp}.pdf"
    output_pdf_path = os.path.join(output_dir, output_pdf_filename)

    # Create PDF
    success = create_pdf(processed_image_paths, output_pdf_path)

    # Clear temporary data and delete temporary files after PDF creation
    processed_images_data = {}
    original_image_order = []
    for temp_path in processed_image_paths:
        try:
            os.remove(temp_path)
            print(f"Cleaned up temporary file: {temp_path}")
        except OSError as e:
            print(f"Error removing temporary file {temp_path}: {e}")

    if success:
        return jsonify({"status": "success", "message": "PDF created successfully.", "output_path": output_pdf_path})
    else:
        return jsonify({"status": "error", "message": "Failed to create PDF."}), 500


@app.route('/serve_image/<path:filename>')
def serve_image(filename):
    """Serves image files from the specified directory."""
    # The base directory for serving images needs to be stored globally or passed
    # in a way accessible to this route. For now, we'll assume the image_directory
    # from the last scan request is available. A more robust solution might involve
    # a temporary mapping or a more secure way to handle paths.
    # IMPORTANT: This is a simplified approach for demonstration. In a production
    # environment, serving arbitrary files like this can be a security risk.
    # A safer approach would be to copy images to a dedicated temporary serve directory.
    global original_image_order
    if original_image_order:
        base_dir = os.path.dirname(original_image_order[0])
        full_path = os.path.join(base_dir, filename)
        if os.path.exists(full_path):
            return send_from_directory(base_dir, filename)
    return "Image not found.", 404


if __name__ == '__main__':
    # This will be run when executing scanner.py directly for testing
    # In the final application, the Flask app will be run from main.py
    app.run(debug=True)
