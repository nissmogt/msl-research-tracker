import os
import secrets
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Required environment variables
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    
    # Generate SECRET_KEY if not provided (for development/testing)
    _secret_key = os.getenv("SECRET_KEY")
    if not _secret_key:
        # Generate a secure key for this session
        _secret_key = secrets.token_urlsafe(32)
        print(f"⚠️  No SECRET_KEY provided. Generated temporary key: {_secret_key[:10]}...")
        print("💡 For production, set SECRET_KEY environment variable")
    
    SECRET_KEY: str = _secret_key
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./msl_research.db")
    
    # JWT settings
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Validate required settings - but don't crash on startup
    def __init__(self):
        if not self.OPENAI_API_KEY:
            print("⚠️  WARNING: OPENAI_API_KEY environment variable is not set")
            print("💡 AI features will not work until OPENAI_API_KEY is set in Railway")
            print("💡 Set OPENAI_API_KEY in Railway environment variables to enable AI insights")

settings = Settings() 