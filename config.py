import os
from datetime import timedelta

class Config:
    # Basic Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-please-change-in-production'
    
    # File Upload Configuration
    UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static', 'uploads'))
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'docx'}  # Only allow .docx files for now
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Security Headers
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'SAMEORIGIN',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
            "font-src 'self' https://cdnjs.cloudflare.com; "
            "img-src 'self' data:; "
            "connect-src 'self'"
        )
    }
    
    # File Cleanup
    FILE_CLEANUP_AFTER = timedelta(hours=24)  # Delete files after 24 hours
    
    # API Rate Limiting
    RATELIMIT_DEFAULT = "100 per minute"
    RATELIMIT_STORAGE_URL = "memory://"
    
    # CORS Configuration
    CORS_ORIGINS = ['http://localhost:5000']
    CORS_METHODS = ['GET', 'POST', 'OPTIONS']
    CORS_ALLOWED_HEADERS = ['Content-Type', 'Authorization']
    
    @staticmethod
    def init_app(app):
        """Initialize application with additional configuration."""
        # Ensure upload directory exists
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        
        # Add security headers
        @app.after_request
        def add_security_headers(response):
            for header, value in Config.SECURITY_HEADERS.items():
                response.headers[header] = value
            return response 