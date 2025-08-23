"""
Development-specific configuration
THIS IS FOR LOCAL DEVELOPMENT ONLY - NEVER USE IN PRODUCTION
"""
import os
from pathlib import Path

class DevelopmentSettings:
    """Development environment settings - isolated from production"""
    
    # Development database - separate from production
    DATABASE_URL = "sqlite:///./dev_msl_research.db"
    
    # Development server settings
    API_PORT = 8000
    DEBUG = True
    ENVIRONMENT = "development"
    
    # Development secret (not secure - only for local dev)
    SECRET_KEY = "development_secret_key_not_for_production"
    
    # OpenAI API Key (optional for development)
    OPENAI_API_KEY = os.getenv("DEV_OPENAI_API_KEY", "")
    
    # CORS settings for development
    CORS_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001"
    ]
    
    def __init__(self):
        print("🔧 DEVELOPMENT MODE ACTIVE")
        print(f"📁 Database: {self.DATABASE_URL}")
        print(f"🌐 API Port: {self.API_PORT}")
        print("⚠️  This is DEVELOPMENT mode - isolated from production")
        
        # Ensure development database directory exists
        db_path = Path(self.DATABASE_URL.replace("sqlite:///", ""))
        db_path.parent.mkdir(exist_ok=True)

# Create development settings instance
dev_settings = DevelopmentSettings()
