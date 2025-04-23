import datetime as dt
import pathlib
import sys
import time
import os
import json
from contextlib import suppress
from timeit import default_timer as timer

import fitz  # PyMuPDF
from flask import Flask, render_template, request, send_file, jsonify

DOMAIN = "http://127.0.0.1:5000"
if hasattr(sys, "_MEIPASS"):
    # Running from the EXE.
    FOLDER = pathlib.Path(sys.executable).parent
else:
    # Running as the script.
    FOLDER = pathlib.Path(__file__).parent.parent # Go up one directory to the omni_pdf folder

app = Flask(__name__, template_folder=FOLDER / 'templates') # Specify the templates folder
temp_dir = FOLDER / "temp_reorder"
temp_dir.mkdir(exist_ok=True)

pdf_path = None
original_pdf_path = None

@app.route('/')
def index():
    global pdf_path
    if pdf_path is None:
        return "Error: PDF path not provided."
    
    doc = fitz.open(pdf_path)
    page_count = doc.page_count
    thumbnails = []
    for i in range(page_count):
        pix = doc.load_page(i).get_pixmap()
        thumbnail_path = temp_dir / f"page_{i+1}.png"
        pix.save(thumbnail_path)
        thumbnails.append(f"/thumbnail/{i+1}")
    doc.close()
    
    return render_template('index.html', thumbnails=thumbnails)

@app.route('/thumbnail/<int:page_num>')
def thumbnail(page_num):
    thumbnail_path = temp_dir / f"page_{page_num}.png"
    if thumbnail_path.exists():
        return send_file(thumbnail_path, mimetype='image/png')
    return "Thumbnail not found", 404

@app.route('/reorder', methods=['POST'])
def reorder_pdf():
    global pdf_path, original_pdf_path
    if pdf_path is None or original_pdf_path is None:
        return jsonify({"status": "error", "message": "PDF path not provided."}), 400

    try:
        data = request.get_json()
        page_order = data.get('order')
        if not page_order:
            return jsonify({"status": "error", "message": "Page order not provided."}), 400

        doc = fitz.open(pdf_path)
        new_doc = fitz.open()

        for item in page_order:
            page_num = int(item['pageNum']) - 1 # Adjust for 0-based index
            rotation = int(item['rotation'])
            if 0 <= page_num < doc.page_count:
                page = doc.load_page(page_num)
                page.set_rotation(rotation) # Apply rotation
                new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
            else:
                print(f"Warning: Invalid page number {page_num + 1} in order.")

        # Generate new filename
        original_path = pathlib.Path(original_pdf_path)
        new_filename = f"{original_path.stem}_reordered{original_path.suffix}"
        new_file_path = original_path.parent / new_filename

        new_doc.save(new_file_path)
        new_doc.close()
        doc.close()

        # Clean up temporary files
        for file in temp_dir.iterdir():
            file.unlink()
        temp_dir.rmdir()

        return jsonify({"status": "success", "message": f"PDF reordered successfully and saved as {new_filename}"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def start_editor(input_pdf_path):
    global pdf_path, original_pdf_path
    pdf_path = input_pdf_path
    original_pdf_path = input_pdf_path # Save original path for saving

    # Copy the input PDF to a temporary location to avoid modifying the original during thumbnail generation
    temp_pdf_path = temp_dir / "current_pdf.pdf"
    import shutil
    shutil.copy2(pdf_path, temp_pdf_path)
    pdf_path = temp_pdf_path

    print(f"Opening reorder editor for {original_pdf_path}...")
    import webbrowser
    webbrowser.open(DOMAIN) # Open the URL in the default browser
    app.run(debug=False) # Set debug=False for production

if __name__ == '__main__':
    # This part is for testing the Flask app directly
    # In the actual tool, start_editor will be called from main.py
    # Example usage: python -m features.reorder C:/path/to/your/pdf.pdf
    if len(sys.argv) > 1:
        start_editor(sys.argv[1])
    else:
        print("Please provide a PDF path as an argument.")
