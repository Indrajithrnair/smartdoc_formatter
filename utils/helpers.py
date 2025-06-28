import os
from werkzeug.utils import secure_filename
from flask import current_app

def allowed_file(filename):
    """
    Check if the uploaded file has an allowed extension
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def get_safe_filename(filename):
    """
    Generate a safe filename while preserving the original extension
    """
    return secure_filename(filename)

def ensure_upload_folder():
    """
    Ensure the upload folder exists
    """
    os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)

def get_file_path(filename):
    """
    Get the full path for a file in the upload folder
    """
    return os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

def cleanup_old_files():
    """
    Clean up old temporary files from the upload folder
    """
    try:
        folder = current_app.config['UPLOAD_FOLDER']
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')
    except Exception as e:
        print(f'Failed to clean up upload folder. Reason: {e}') 