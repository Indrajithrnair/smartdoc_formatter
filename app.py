import os
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, jsonify, session, render_template
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
import logging
from logging.handlers import RotatingFileHandler
from datetime import timedelta

from config import Config
from routes.document import document_bp
from routes.preview import preview_bp
from utils.helpers import cleanup_old_files, ensure_upload_folder

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize configuration
    config_class.init_app(app)
    
    # Initialize CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": app.config['CORS_ORIGINS'],
            "methods": app.config['CORS_METHODS'],
            "allow_headers": app.config['CORS_ALLOWED_HEADERS']
        }
    })
    
    # Configure session
    app.permanent_session_lifetime = app.config['PERMANENT_SESSION_LIFETIME']
    
    # Configure logging
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/smartdoc.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('SmartDoc Formatter startup')

    # Register blueprints
    app.register_blueprint(document_bp, url_prefix='/api')
    app.register_blueprint(preview_bp, url_prefix='/api')

    # Ensure upload directory exists and clean old files
    with app.app_context():
        ensure_upload_folder(app)
        cleanup_old_files(app)

    @app.route('/')
    def index():
        """Serve the main application interface."""
        return render_template('index.html')

    @app.route('/<path:path>')
    def catch_all(path):
        """Handle undefined routes."""
        return jsonify({
            "error": {
                "code": 404,
                "name": "Not Found",
                "description": f"The requested URL /{path} was not found on the server.",
                "available_endpoints": {
                    "root": "/",
                    "document": "/api/",
                    "upload": "/api/upload",
                    "process": "/api/process",
                    "download": "/api/download/<file_id>",
                    "preview": "/api/preview/<file_id>"
                }
            }
        }), 404

    @app.before_request
    def before_request():
        """Initialize session data."""
        session.permanent = True
        if not session.get('files'):
            session['files'] = []

    @app.after_request
    def after_request(response):
        """Add CORS headers to response."""
        response.headers.add('Access-Control-Allow-Origin', app.config['CORS_ORIGINS'][0])
        response.headers.add('Access-Control-Allow-Headers', ', '.join(app.config['CORS_ALLOWED_HEADERS']))
        response.headers.add('Access-Control-Allow-Methods', ', '.join(app.config['CORS_METHODS']))
        return response

    @app.errorhandler(HTTPException)
    def handle_exception(e):
        """Handle all HTTP exceptions."""
        app.logger.error(f"HTTP error occurred: {str(e)}")
        response = {
            "error": {
                "code": e.code,
                "name": e.name,
                "description": e.description,
            }
        }
        return jsonify(response), e.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(e):
        """Handle any unexpected errors."""
        app.logger.error(f"Unexpected error occurred: {str(e)}")
        response = {
            "error": {
                "code": 500,
                "name": "Internal Server Error",
                "description": "An unexpected error occurred"
            }
        }
        return jsonify(response), 500

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000) 