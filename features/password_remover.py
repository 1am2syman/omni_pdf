"""Module for removing passwords from PDF files."""

import os
import time
from flask import Blueprint, request, jsonify, current_app
import fitz  # PyMuPDF
import pathlib
import sys
import logging

# Create a Blueprint for this feature
password_remover_bp = Blueprint(
    'password_remover_bp', 
    __name__,
    template_folder='../templates' # Assuming templates are in a common directory
)

if hasattr(sys, "_MEIPASS"):
    # Running from the EXE.
    FOLDER = pathlib.Path(sys.executable).parent
else:
    # Running as the script.
    FOLDER = pathlib.Path(__file__).parent.parent # Go up one level to project root from features/

# Setup basic logging for the module if not in Flask context
logger = logging.getLogger(__name__)
if not logger.handlers: # Avoid adding multiple handlers during reloads
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def remove_pdf_password_core(input_pdf_path: str, password: str, output_folder_abs: str) -> dict:
    """
    Removes password from an encrypted PDF file using PyMuPDF (fitz) if the provided password is correct.
    Saves the decrypted PDF with '_decrypted_{timestamp}' appended to its original name in the specified output_folder.

    Args:
        input_pdf_path: Path to the encrypted PDF file.
        password: The password to decrypt the PDF.
        output_folder_abs: Absolute path to the folder to save the decrypted PDF.

    Returns:
        A dictionary with status, message, and optionally output_path.
    """
    try:
        if not os.path.exists(input_pdf_path):
            return {"status": "error", "message": f"Input PDF not found: {input_pdf_path}"}
        
        if not os.path.isdir(output_folder_abs):
             os.makedirs(output_folder_abs, exist_ok=True) # Ensure output folder exists

        doc = fitz.open(input_pdf_path)
        
        if doc.is_encrypted:
            # Attempt to authenticate
            if doc.authenticate(password):
                # Define output path
                original_filename = os.path.basename(input_pdf_path)
                base, ext = os.path.splitext(original_filename)
                # Ensure unique filename in the target directory
                timestamp = int(time.time())
                decrypted_filename = f"{base}_decrypted_{timestamp}{ext}"
                output_pdf_path = os.path.join(output_folder_abs, decrypted_filename)
                
                # Save the decrypted PDF
                # Using garbage=3 or 4 can help clean up, deflate compresses.
                doc.save(output_pdf_path, garbage=4, deflate=True)
                doc.close()
                
                return {
                    "status": "success",
                    "message": "PDF password removed successfully.",
                    "output_path": output_pdf_path
                }
            else:
                doc.close()
                return {
                    "status": "error",
                    "message": "Incorrect password or decryption failed."
                }
        else:
            doc.close()
            # If not encrypted, we can optionally copy it or just inform the user.
            # For consistency, let's copy it to the output folder with a similar naming convention.
            original_filename = os.path.basename(input_pdf_path)
            base, ext = os.path.splitext(original_filename)
            timestamp = int(time.time()) # Add timestamp to avoid overwriting if called multiple times
            output_filename = f"{base}_unencrypted_{timestamp}{ext}"
            output_pdf_path = os.path.join(output_folder_abs, output_filename)
            
            # Copy the file
            import shutil
            shutil.copy2(input_pdf_path, output_pdf_path)

            return {
                "status": "info",
                "message": "PDF is not encrypted. Copied to output folder.",
                "output_path": output_pdf_path 
            }
    except Exception as e:
        # Use module logger or current_app.logger if available
        log_func = current_app.logger.error if current_app else logger.error
        log_func(f"Error removing PDF password for {input_pdf_path}: {e}", exc_info=True)
        if 'doc' in locals() and doc: # Ensure doc is closed if an error occurs after opening
            try:
                doc.close()
            except: # nosec
                pass 
        return {"status": "error", "message": f"An error occurred: {str(e)}"}

@password_remover_bp.route('/remove_pdf_password', methods=['POST'])
def handle_remove_pdf_password_route():
    """
    Flask route to handle PDF password removal requests.
    Expects 'pdf_path' and 'password' in form data.
    Optionally 'output_folder_relative' (relative to project root).
    """
    if 'pdf_file' not in request.files:
        return jsonify({"status": "error", "message": "No PDF file part in the request."}), 400
    
    file = request.files['pdf_file']
    password = request.form.get('password', "")
    # Default output folder is 'removed_passwords' in the project root
    output_folder_form = request.form.get('output_folder_relative', 'removed_passwords_web') 

    if file.filename == '':
        return jsonify({"status": "error", "message": "No PDF file selected."}), 400

    if file and file.filename.lower().endswith('.pdf'):
        # Ensure the FOLDER for saving temporary uploaded files exists (e.g., project_root/temp_uploads)
        upload_temp_dir = FOLDER / "temp_uploads_web" # Differentiate from CLI temp if any
        os.makedirs(upload_temp_dir, exist_ok=True)
        
        # Save the uploaded file temporarily
        # Sanitize filename to prevent directory traversal or invalid characters
        from werkzeug.utils import secure_filename
        safe_filename = secure_filename(file.filename)
        if not safe_filename: # Handle empty or all-invalid char filenames
            safe_filename = f"uploaded_file_{int(time.time())}.pdf"
            
        temp_pdf_path = upload_temp_dir / safe_filename
        file.save(temp_pdf_path)

        # Determine absolute output folder (e.g., project_root/removed_passwords_web)
        absolute_output_folder = FOLDER / output_folder_form 
        os.makedirs(absolute_output_folder, exist_ok=True)

        result = remove_pdf_password_core(str(temp_pdf_path), password, str(absolute_output_folder))
        
        # Clean up the temporarily uploaded file
        try:
            os.remove(temp_pdf_path)
        except OSError as e:
            current_app.logger.error(f"Error removing temporary file {temp_pdf_path}: {e}")

        if result["status"] == "success" or result["status"] == "info":
            return jsonify(result), 200
        elif "Incorrect password" in result.get("message", ""):
            return jsonify(result), 401 # Unauthorized for incorrect password
        else: 
            return jsonify(result), 500
    else:
        return jsonify({"status": "error", "message": "Invalid file type. Please upload a PDF file."}), 400

# Example of how to run this blueprint if it were standalone (for testing)
# In a real app, this blueprint would be registered with the main Flask app.
if __name__ == '__main__':
    # This is for testing the blueprint directly.
    # You would need a simple Flask app to run this.
    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(password_remover_bp, url_prefix='/feature') # Example prefix
    
    # Configure logging for testing
    import logging
    logging.basicConfig(level=logging.DEBUG)
    app.logger.info("Starting password remover blueprint test server...")
    
    print("Password Remover Blueprint Test Server")
    print("Routes:")
    print("  POST /feature/remove_pdf_password")
    print("    Params: pdf_file (file), password (form), output_folder_relative (form, optional)")
    print("  POST /feature/remove_passwords_from_folder")
    print("    Params: input_folder_path (form), password (form, optional), output_folder_relative (form, optional)")
    app.run(debug=True, port=5001)


def remove_passwords_from_folder_core(input_folder_path: str, password: str, output_folder_abs: str) -> dict:
    """
    Removes passwords from all PDF files in a given folder.

    Args:
        input_folder_path: Absolute or relative path to the folder containing encrypted PDF files.
        password: The password to try for decrypting the PDFs. An empty string can be used
                  if PDFs might not have passwords or have blank passwords.
        output_folder_abs: Absolute path to the folder to save the decrypted PDFs.

    Returns:
        A dictionary containing a list of results for each file processed.
    """
    results = []
    total_files = 0
    successful_removals = 0
    failed_removals = 0
    not_encrypted_skipped = 0

    # Ensure input_folder_path is absolute
    input_folder_abs = os.path.abspath(input_folder_path)

    if not os.path.isdir(input_folder_abs):
        return {
            "status": "error",
            "message": f"Input folder not found: {input_folder_abs}",
            "summary": {
                "total_files_scanned": 0,
                "successful_removals": 0,
                "failed_removals": 0,
                "not_encrypted_or_copied": 0
            },
            "details": []
        }

    os.makedirs(output_folder_abs, exist_ok=True)
    
    log_func = current_app.logger.info if current_app else logger.info

    for filename in os.listdir(input_folder_abs):
        if filename.lower().endswith(".pdf"):
            total_files += 1
            file_path = os.path.join(input_folder_abs, filename)
            log_func(f"Processing file: {file_path}")
            
            result = remove_pdf_password_core(file_path, password, output_folder_abs)
            
            file_summary = {
                "file_name": filename,
                "status": result["status"],
                "message": result["message"]
            }
            if "output_path" in result:
                file_summary["output_path"] = result["output_path"]
            
            results.append(file_summary)

            if result["status"] == "success":
                successful_removals += 1
            elif result["status"] == "info": # Not encrypted, copied
                not_encrypted_skipped +=1
            else: # error
                failed_removals += 1
        else:
            log_func(f"Skipping non-PDF file: {filename}")

    return {
        "status": "completed",
        "message": f"Processed {total_files} PDF files in the folder.",
        "summary": {
            "total_files_scanned": total_files,
            "successful_removals": successful_removals,
            "failed_removals": failed_removals,
            "not_encrypted_or_copied": not_encrypted_skipped
        },
        "details": results
    }

@password_remover_bp.route('/remove_passwords_from_folder', methods=['POST'])
def handle_remove_passwords_from_folder_route():
    """
    Flask route to handle password removal for all PDFs in a folder.
    Expects 'input_folder_path' (server-accessible path) and optionally 'password' 
    and 'output_folder_relative' in form data.
    """
    input_folder_path_form = request.form.get('input_folder_path')
    password = request.form.get('password', "") # Default to empty string if not provided
    output_folder_relative_from_request = request.form.get('output_folder_relative')

    if not input_folder_path_form:
        return jsonify({"status": "error", "message": "Missing 'input_folder_path' in form data."}), 400

    # The input_folder_path_form is expected to be a path accessible by the server.
    # For security, you might want to restrict this to subdirectories of FOLDER or a specific base path.
    # For now, we'll resolve it relative to FOLDER if it's not absolute.
    if not os.path.isabs(input_folder_path_form):
        input_folder_path_abs = FOLDER / input_folder_path_form
    else:
        input_folder_path_abs = pathlib.Path(input_folder_path_form)
    
    # Ensure the input path is a directory and within the project FOLDER to prevent directory traversal attacks
    # This is a basic check; more robust validation might be needed depending on security requirements.
    try:
        # Check if input_folder_path_abs is a subdirectory of FOLDER
        # This check might be too restrictive if users need to specify arbitrary server paths.
        # If arbitrary paths are allowed, ensure proper server-side validation and permissions.
        # For now, let's assume it should be within the project or an absolute path the server can access.
        if not os.path.isdir(str(input_folder_path_abs)):
             return jsonify({"status": "error", "message": f"Input folder path is not a valid directory: {input_folder_path_abs}"}), 400
        # Example security check (optional, adjust as needed):
        # if not str(input_folder_path_abs.resolve()).startswith(str(FOLDER.resolve())):
        #     return jsonify({"status": "error", "message": "Input folder path is outside the allowed project directory."}), 403

    except Exception as e: # Catches errors like invalid path characters
        return jsonify({"status": "error", "message": f"Invalid input folder path: {str(e)}"}), 400

    # Determine absolute_output_folder
    if output_folder_relative_from_request:
        # User specified an output folder relative to project root
        absolute_output_folder = FOLDER / output_folder_relative_from_request
    else:
        # Default to the input folder itself if no specific output folder is provided
        absolute_output_folder = input_folder_path_abs 
    
    os.makedirs(absolute_output_folder, exist_ok=True)

    results = remove_passwords_from_folder_core(str(input_folder_path_abs), password, str(absolute_output_folder))

    if results["status"] == "completed":
        return jsonify(results), 200
    else: # Typically "error" if input folder not found
        return jsonify(results), 404 if "not found" in results.get("message", "").lower() else 500
