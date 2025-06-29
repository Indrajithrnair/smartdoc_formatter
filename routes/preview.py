from flask import Blueprint, jsonify, current_app, session
import mammoth
import bleach
from bleach.css_sanitizer import CSSSanitizer
import os

from utils.helpers import get_file_path

preview_bp = Blueprint('preview', __name__)

# Configure bleach for safe HTML
ALLOWED_TAGS = [
    'p', 'br', 'b', 'i', 'u', 'em', 'strong', 'a', 'h1', 'h2', 'h3',
    'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote', 'pre', 'code',
    'hr', 'div', 'span', 'table', 'thead', 'tbody', 'tr', 'th', 'td'
]

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title'],
    'img': ['src', 'alt', 'title'],
    '*': ['class', 'style']
}

ALLOWED_STYLES = [
    'text-align', 'margin-left', 'margin-right', 'font-size', 'font-family'
]

STYLE_MAP = {
    'b': 'strong',
    'i': 'em'
}

@preview_bp.route('/preview/<file_id>', methods=['GET'])
def preview_document(file_id):
    """Generate HTML preview of the document."""
    try:
        # Check if session is initialized
        if 'files' not in session:
            current_app.logger.error("Session files list not initialized")
            return jsonify({'error': 'Session error'}), 500

        # Find file info in session
        file_info = next((f for f in session['files'] if f['id'] == file_id), None)
        if not file_info:
            current_app.logger.error(f"File info not found in session for file_id: {file_id}")
            return jsonify({'error': 'File not found in session'}), 404

        # Use processed file if available, otherwise use original
        filename = file_info.get('processed_filename') or file_info['filename']
        filepath = get_file_path(filename, current_app)
        
        current_app.logger.info(f"Attempting to preview file: {filepath}")
        
        if not os.path.exists(filepath):
            current_app.logger.error(f"File not found at path: {filepath}")
            return jsonify({'error': 'File not found on server'}), 404

        # Configure mammoth with style map
        style_map = """
        p[style-name='Heading 1'] => h1:fresh
        p[style-name='Heading 2'] => h2:fresh
        p[style-name='Heading 3'] => h3:fresh
        p[style-name='Heading 4'] => h4:fresh
        p[style-name='Heading 5'] => h5:fresh
        p[style-name='Heading 6'] => h6:fresh
        b => strong
        i => em
        u => u
        strike => s
        """

        # Convert DOCX to HTML with style mapping
        try:
            current_app.logger.info(f"Opening document for conversion: {filepath}")
            with open(filepath, 'rb') as docx_file:
                current_app.logger.info("Starting mammoth conversion")
                result = mammoth.convert_to_html(
                    docx_file,
                    style_map=style_map,
                    ignore_empty_paragraphs=True
                )
                html = result.value
                messages = result.messages

            # Log conversion messages
            if messages:
                for msg in messages:
                    current_app.logger.warning(f"Mammoth conversion message: {msg}")

            if not html:
                current_app.logger.error("Mammoth conversion produced empty HTML")
                return jsonify({'error': 'Document conversion failed - empty result'}), 500

            current_app.logger.info("Document conversion successful")

        except Exception as conversion_error:
            current_app.logger.error(f"Document conversion error: {str(conversion_error)}", exc_info=True)
            return jsonify({
                'error': 'Document conversion failed',
                'details': str(conversion_error)
            }), 500

        # Sanitize HTML while preserving formatting
        try:
            css_sanitizer = CSSSanitizer(allowed_css_properties=ALLOWED_STYLES)
            cleaner = bleach.sanitizer.Cleaner(
                tags=ALLOWED_TAGS,
                attributes=ALLOWED_ATTRIBUTES,
                css_sanitizer=css_sanitizer,
                strip=True
            )
            clean_html = cleaner.clean(html)
            
            if not clean_html:
                current_app.logger.error("HTML sanitization produced empty result")
                return jsonify({'error': 'HTML sanitization failed - empty result'}), 500

            current_app.logger.info("HTML sanitization successful")

        except Exception as sanitize_error:
            current_app.logger.error(f"HTML sanitization error: {str(sanitize_error)}", exc_info=True)
            return jsonify({
                'error': 'HTML sanitization failed',
                'details': str(sanitize_error)
            }), 500

        # Add wrapper div for styling
        wrapped_html = f'<div class="document-preview">{clean_html}</div>'

        return jsonify({
            'html': wrapped_html,
            'messages': [str(msg) for msg in messages],
            'is_processed': bool(file_info.get('processed_filename'))
        }), 200

    except Exception as e:
        current_app.logger.error(f"Unexpected error in preview: {str(e)}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred'}), 500 