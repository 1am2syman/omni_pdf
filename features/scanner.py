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
import base64
import io

# Initialize Flask app
app = Flask(__name__, template_folder='../templates')

# Temporary storage for processed images
# Key: original_image_path, Value: processed_image_object
processed_images_data = {}
original_image_order = [] # To maintain the order of images

# Placeholder for image processing functions
def detect_document_edges(img_cv):
    """Detects document edges in an image using OpenCV."""
    try:
        # Convert to grayscale if it's not already
        if len(img_cv.shape) == 3:
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        else:
            gray = img_cv.copy()
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Apply Canny edge detection
        edges = cv2.Canny(blurred, 75, 200)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # If no contours found, return None
        if not contours:
            return None
        
        # Find the largest contour by area
        largest_contour = max(contours, key=cv2.contourArea)
        
        # Approximate the contour to get a polygon
        epsilon = 0.02 * cv2.arcLength(largest_contour, True)
        approx = cv2.approxPolyDP(largest_contour, epsilon, True)
        
        # If the polygon has 4 points, it's likely a document
        if len(approx) == 4:
            return approx
        
        # If not a quadrilateral, return the bounding rectangle
        x, y, w, h = cv2.boundingRect(largest_contour)
        return np.array([[x, y], [x+w, y], [x+w, y+h], [x, y+h]], dtype=np.int32).reshape(-1, 1, 2)
    
    except Exception as e:
        print(f"Error detecting document edges: {e}")
        return None

def apply_perspective_correction(img_cv, corners):
    """Applies perspective correction to an image using detected corners."""
    try:
        # Order points in top-left, top-right, bottom-right, bottom-left order
        corners = corners.reshape(4, 2)
        rect = np.zeros((4, 2), dtype=np.float32)
        
        # Sum of coordinates: smallest is top-left, largest is bottom-right
        s = corners.sum(axis=1)
        rect[0] = corners[np.argmin(s)]  # Top-left
        rect[2] = corners[np.argmax(s)]  # Bottom-right
        
        # Difference of coordinates: smallest is top-right, largest is bottom-left
        diff = np.diff(corners, axis=1)
        rect[1] = corners[np.argmin(diff)]  # Top-right
        rect[3] = corners[np.argmax(diff)]  # Bottom-left
        
        # Compute width and height of the new image
        width_a = np.sqrt(((rect[2][0] - rect[3][0]) ** 2) + ((rect[2][1] - rect[3][1]) ** 2))
        width_b = np.sqrt(((rect[1][0] - rect[0][0]) ** 2) + ((rect[1][1] - rect[0][1]) ** 2))
        max_width = max(int(width_a), int(width_b))
        
        height_a = np.sqrt(((rect[1][0] - rect[2][0]) ** 2) + ((rect[1][1] - rect[2][1]) ** 2))
        height_b = np.sqrt(((rect[0][0] - rect[3][0]) ** 2) + ((rect[0][1] - rect[3][1]) ** 2))
        max_height = max(int(height_a), int(height_b))
        
        # Define destination points for perspective transform
        dst = np.array([
            [0, 0],
            [max_width - 1, 0],
            [max_width - 1, max_height - 1],
            [0, max_height - 1]
        ], dtype=np.float32)
        
        # Compute perspective transform matrix and apply it
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(img_cv, M, (max_width, max_height))
        
        return warped
    
    except Exception as e:
        print(f"Error applying perspective correction: {e}")
        return img_cv

def enhance_document_image(img_cv, brightness=1.0, contrast=1.5, sharpness=1.0):
    """Enhances a document image with adjustable parameters."""
    try:
        # Convert to PIL Image for enhancement operations
        if len(img_cv.shape) == 2:  # Grayscale
            img_pil = Image.fromarray(img_cv, 'L')
        else:  # Color
            img_pil = Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB))
        
        # Apply brightness adjustment
        if brightness != 1.0:
            enhancer = ImageEnhance.Brightness(img_pil)
            img_pil = enhancer.enhance(brightness)
        
        # Apply contrast adjustment
        if contrast != 1.0:
            enhancer = ImageEnhance.Contrast(img_pil)
            img_pil = enhancer.enhance(contrast)
        
        # Apply sharpness adjustment
        if sharpness != 1.0:
            enhancer = ImageEnhance.Sharpness(img_pil)
            img_pil = enhancer.enhance(sharpness)
        
        # Convert back to OpenCV format
        if len(img_cv.shape) == 2:  # Grayscale
            enhanced_cv = np.array(img_pil)
        else:  # Color
            enhanced_cv = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
        
        return enhanced_cv
    
    except Exception as e:
        print(f"Error enhancing document image: {e}")
        return img_cv

def process_image(image_path, crop_coords_from_frontend, brightness=1.0, contrast=1.5, sharpness=1.0, rotation=0, auto_enhance_enabled=False):
    """Processes a single image with cropping and enhancements using OpenCV."""
    try:
        print(f"Processing image: {image_path}")
        print(f"Parameters: brightness={brightness}, contrast={contrast}, sharpness={sharpness}, rotation={rotation}, auto_enhance={auto_enhance_enabled}")
        print(f"Frontend crop coordinates: {crop_coords_from_frontend}")
        
        img_cv = cv2.imread(image_path)
        if img_cv is None:
            print(f"Error: Could not read image {image_path}")
            return None

        original_height, original_width = img_cv.shape[:2]
        print(f"Original image dimensions: {original_width}x{original_height}")

        # 1. Apply rotation first
        if rotation != 0:
            print(f"Applying rotation: {rotation} degrees")
            if rotation == 90: rotate_code = cv2.ROTATE_90_CLOCKWISE
            elif rotation == 180: rotate_code = cv2.ROTATE_180
            elif rotation == 270: rotate_code = cv2.ROTATE_90_COUNTERCLOCKWISE
            else: rotate_code = cv2.ROTATE_180 # Should not happen with current frontend
            img_cv = cv2.rotate(img_cv, rotate_code)
            print(f"Image dimensions after rotation: {img_cv.shape[1]}x{img_cv.shape[0]}")

        # 2. Define initial Region of Interest (ROI) based on frontend crop
        # The crop_coords_from_frontend are relative to the *rotated* image state as seen by Cropper.js
        h_rotated, w_rotated = img_cv.shape[:2]
        
        # Initialize roi_cv to the full rotated image. It will be updated if valid crop_coords are provided.
        roi_cv = img_cv.copy()

        if crop_coords_from_frontend and \
           crop_coords_from_frontend.get('width', 0) > 0 and \
           crop_coords_from_frontend.get('height', 0) > 0:
            
            x_f = int(crop_coords_from_frontend['x'])
            y_f = int(crop_coords_from_frontend['y'])
            w_f = int(crop_coords_from_frontend['width'])
            h_f = int(crop_coords_from_frontend['height'])

            # Validate and clamp frontend crop coordinates
            # Ensure x_f, y_f are within bounds before calculating w_f, h_f relative to them
            x_f = max(0, min(x_f, w_rotated - 1 if w_rotated > 0 else 0))
            y_f = max(0, min(y_f, h_rotated - 1 if h_rotated > 0 else 0))
            
            # Ensure w_f and h_f do not extend beyond image boundaries from x_f, y_f
            w_f = max(1, min(w_f, w_rotated - x_f))
            h_f = max(1, min(h_f, h_rotated - y_f))
            
            print(f"Applying frontend crop: x={x_f}, y={y_f}, w={w_f}, h={h_f} to rotated image of size {w_rotated}x{h_rotated}")
            # Only update roi_cv if the crop dimensions are valid
            if w_f > 0 and h_f > 0:
                 roi_cv = img_cv[y_f:y_f+h_f, x_f:x_f+w_f]
            else:
                print("Warning: Frontend crop coordinates resulted in zero width/height. Using full rotated image as ROI.")
        else:
            print("No valid frontend crop coordinates provided, using full rotated image as ROI.")

        if roi_cv.size == 0: # Check if ROI became empty
            print("Error: ROI is empty after frontend crop. Using full rotated image.")
            roi_cv = img_cv.copy() # Fallback to full image
        
        print(f"ROI dimensions before auto-enhance: {roi_cv.shape[1]}x{roi_cv.shape[0]}")

        # 3. If auto_enhance_enabled, perform edge detection and perspective correction on the ROI
        if auto_enhance_enabled:
            print("Auto-enhance enabled. Detecting edges on ROI...")
            edges = detect_document_edges(roi_cv) 
            if edges is not None:
                print("Document edges detected in ROI. Applying perspective correction...")
                roi_cv = apply_perspective_correction(roi_cv, edges) 
                print(f"ROI dimensions after perspective correction: {roi_cv.shape[1]}x{roi_cv.shape[0]}")
            else:
                print("No document edges detected in ROI for auto-enhancement.")
        
        # 4. Apply image enhancements (brightness, contrast, sharpness) to the (potentially perspective-corrected) ROI
        print("Applying image enhancements to ROI...")
        enhanced_roi_cv = enhance_document_image(roi_cv, brightness, contrast, sharpness)
        print(f"ROI dimensions after enhancements: {enhanced_roi_cv.shape[1]}x{enhanced_roi_cv.shape[0]}")

        # 5. Convert to grayscale, denoise, and apply adaptive thresholding to the enhanced ROI
        print("Converting to grayscale, denoising, and applying adaptive thresholding...")
        if len(enhanced_roi_cv.shape) == 3: 
             gray_roi_cv = cv2.cvtColor(enhanced_roi_cv, cv2.COLOR_BGR2GRAY)
        else: 
             gray_roi_cv = enhanced_roi_cv
        
        denoised_roi_cv = cv2.bilateralFilter(gray_roi_cv, 9, 75, 75)
        processed_roi_cv = cv2.adaptiveThreshold(denoised_roi_cv, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        
        if len(processed_roi_cv.shape) == 2: 
            final_pil_image = Image.fromarray(processed_roi_cv, 'L').convert('RGB')
        else: 
            final_pil_image = Image.fromarray(cv2.cvtColor(processed_roi_cv, cv2.COLOR_BGR2RGB))

        print(f"Final processed image dimensions: {final_pil_image.width}x{final_pil_image.height}")
        return final_pil_image
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
    contrast = data.get('contrast', 1.0)
    sharpness = data.get('sharpness', 1.0)
    rotation = data.get('rotation', 0)
    output_folder = data.get('output_folder')
    auto_enhance_enabled = data.get('auto_enhance_enabled', False) # Get the new flag

    if not image_path or not os.path.exists(image_path):
        return jsonify({"status": "error", "message": "Image path not provided or does not exist."}), 400

    # Pass auto_enhance_enabled to process_image
    processed_image = process_image(image_path, crop_coords, brightness, contrast, sharpness, rotation, auto_enhance_enabled)

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


@app.route('/detect_edges', methods=['POST'])
def detect_edges():
    """Detects document edges in an image and returns crop coordinates."""
    data = request.json
    image_data = data.get('image_data')
    image_path = data.get('image_path')
    
    if not image_data and not image_path:
        return jsonify({"status": "error", "message": "No image data or path provided."}), 400
    
    try:
        # Process image from base64 data or file path
        if image_data:
            # Remove the data URL prefix if present
            if image_data.startswith('data:image'):
                image_data = image_data.split(',')[1]
            
            # Decode base64 image
            image_bytes = base64.b64decode(image_data)
            nparr = np.frombuffer(image_bytes, np.uint8)
            img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        elif image_path:
            # Read image from file path
            img_cv = cv2.imread(image_path)
        
        if img_cv is None:
            return jsonify({"status": "error", "message": "Failed to decode image."}), 400
        
        # Detect document edges
        edges = detect_document_edges(img_cv)
        
        if edges is None:
            return jsonify({"status": "error", "message": "No document edges detected."}), 404
        
        # Get bounding rectangle of the detected edges
        x, y, w, h = cv2.boundingRect(edges)
        
        # Return crop coordinates
        return jsonify({
            "status": "success",
            "crop_coords": {
                "x": int(x),
                "y": int(y),
                "width": int(w),
                "height": int(h)
            }
        })
    
    except Exception as e:
        print(f"Error detecting edges: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    # This will be run when executing scanner.py directly for testing
    # In the final application, the Flask app will be run from main.py
    app.run(debug=True)
