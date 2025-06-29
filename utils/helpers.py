import os
import time
from datetime import datetime
from typing import Optional
from werkzeug.utils import secure_filename
from flask import Flask, current_app
import logging

logger = logging.getLogger(__name__)

def allowed_file(filename: str, app: Flask) -> bool:
    """
    Check if the uploaded file has an allowed extension.
    
    Args:
        filename (str): The name of the file to check
        app (Flask): The Flask application instance
        
    Returns:
        bool: True if the file extension is allowed, False otherwise
    """
    if not filename or '.' not in filename:
        return False
    extension = filename.rsplit('.', 1)[1].lower()
    return extension in app.config['ALLOWED_EXTENSIONS']

def get_safe_filename(filename: str) -> str:
    """
    Generate a safe filename while preserving the original extension.
    
    Args:
        filename (str): The original filename
        
    Returns:
        str: A sanitized version of the filename
    """
    if not filename:
        raise ValueError("Filename cannot be empty")
    return secure_filename(filename)

def ensure_upload_folder(app: Flask) -> None:
    """
    Ensure the upload folder exists and has proper permissions.
    
    Args:
        app (Flask): The Flask application instance
    """
    try:
        upload_folder = app.config['UPLOAD_FOLDER']
        logger.info(f"Ensuring upload folder exists at: {upload_folder}")
        
        # Create directory if it doesn't exist
        if not os.path.exists(upload_folder):
            logger.info(f"Creating upload folder: {upload_folder}")
            os.makedirs(upload_folder, mode=0o755, exist_ok=True)
        
        # Ensure directory has correct permissions
        current_mode = os.stat(upload_folder).st_mode & 0o777
        if current_mode != 0o755:
            logger.warning(f"Fixing upload folder permissions from {oct(current_mode)} to 755")
            os.chmod(upload_folder, 0o755)
        
        # Check if directory is writable
        test_file = os.path.join(upload_folder, '.test')
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            logger.info("Upload folder is writable")
        except OSError as e:
            error_msg = f"Upload directory {upload_folder} is not writable: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
            
    except Exception as e:
        error_msg = f"Failed to initialize upload folder: {e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

def get_file_path(filename: str, app: Flask) -> str:
    """
    Get the full path for a file in the upload folder.
    
    Args:
        filename (str): The name of the file
        app (Flask): The Flask application instance
        
    Returns:
        str: The full path to the file
        
    Raises:
        ValueError: If the filename is empty or would escape the upload folder
    """
    if not filename:
        raise ValueError("Filename cannot be empty")
        
    safe_filename = get_safe_filename(filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
    
    # Ensure the path doesn't escape the upload folder
    if not os.path.normpath(file_path).startswith(os.path.normpath(app.config['UPLOAD_FOLDER'])):
        raise ValueError("Invalid file path")
        
    return file_path

def get_file_age(file_path: str) -> Optional[float]:
    """
    Get the age of a file in seconds.
    
    Args:
        file_path (str): Path to the file
        
    Returns:
        Optional[float]: The age of the file in seconds, or None if the file doesn't exist
    """
    try:
        if os.path.exists(file_path):
            return time.time() - os.path.getmtime(file_path)
        return None
    except OSError as e:
        logger.error(f"Error getting file age for {file_path}: {e}")
        return None

def cleanup_old_files(app: Flask) -> None:
    """
    Clean up old temporary files from the upload folder.
    
    Args:
        app (Flask): The Flask application instance
    """
    try:
        folder = app.config['UPLOAD_FOLDER']
        max_age = app.config['FILE_CLEANUP_AFTER'].total_seconds()
        
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                # Skip if not a file
                if not os.path.isfile(file_path):
                    continue
                    
                # Check file age
                file_age = get_file_age(file_path)
                if file_age and file_age > max_age:
                    os.unlink(file_path)
                    logger.info(f"Deleted old file: {filename}")
                    
            except Exception as e:
                logger.error(f"Failed to process {file_path} during cleanup: {e}")
                
    except Exception as e:
        logger.error(f"Failed to clean up upload folder: {e}")

def format_file_size(size_in_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_in_bytes (int): File size in bytes
        
    Returns:
        str: Formatted file size (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_in_bytes < 1024:
            return f"{size_in_bytes:.1f} {unit}"
        size_in_bytes /= 1024
    return f"{size_in_bytes:.1f} TB" 