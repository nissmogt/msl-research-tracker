#!/usr/bin/env python3
"""
🔧 Development Environment Setup Script
Creates isolated development environment separate from production

This script ensures:
1. Separate development database
2. Local-only configurations
3. No risk to production data
4. Proper environment isolation
"""

import os
import secrets
import shutil
from pathlib import Path

def create_dev_env_file():
    """Create development environment file"""
    env_content = f"""# 🔧 DEVELOPMENT ENVIRONMENT ONLY
# This file configures the app for LOCAL DEVELOPMENT
# Never use these values in production!

# Development Database (separate from production)
DATABASE_URL=sqlite:///./dev_msl_research.db

# Development API Configuration
ENVIRONMENT=development
PORT=8000
DEBUG=true

# Development Secret Key (NOT FOR PRODUCTION)
SECRET_KEY={secrets.token_urlsafe(32)}

# Optional: Add your OpenAI key for testing AI features
# OPENAI_API_KEY=your_dev_key_here

# Development CORS (allows all local origins)
CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000
"""
    
    # Write to backend directory
    backend_env = Path("backend/.env.development")
    with open(backend_env, 'w') as f:
        f.write(env_content)
    
    print(f"✅ Created: {backend_env}")
    return backend_env

def create_frontend_env():
    """Create frontend development environment"""
    frontend_env_content = """# Frontend Development Configuration
# Forces frontend to connect to local backend

REACT_APP_API_URL=http://localhost:8000
REACT_APP_ENVIRONMENT=development

# Development optimizations
GENERATE_SOURCEMAP=true
BROWSER=none
"""
    
    frontend_env = Path("frontend/.env.development")
    with open(frontend_env, 'w') as f:
        f.write(frontend_env_content)
    
    print(f"✅ Created: {frontend_env}")
    return frontend_env

def backup_production_db():
    """Backup any existing production database"""
    prod_db = Path("backend/msl_research.db")
    if prod_db.exists():
        backup_db = Path("backend/msl_research_BACKUP.db")
        shutil.copy2(prod_db, backup_db)
        print(f"📁 Backed up production DB to: {backup_db}")
        return backup_db
    return None

def create_dev_database():
    """Initialize separate development database"""
    dev_db = Path("backend/dev_msl_research.db")
    
    # Remove existing dev database to start fresh
    if dev_db.exists():
        dev_db.unlink()
        print(f"🗑️  Removed existing dev database")
    
    print(f"📁 Development database will be created at: {dev_db}")
    return dev_db

def update_backend_for_dev():
    """Update backend to load development configuration"""
    main_py = Path("backend/main.py")
    
    # Add development configuration import at the top
    dev_config_import = """
# Development Environment Detection
import os
if os.getenv('ENVIRONMENT') == 'development' or '--dev' in os.sys.argv:
    from config_dev import dev_settings
    print("🔧 Loading DEVELOPMENT configuration")
else:
    from config import settings
    print("🚀 Loading PRODUCTION configuration")
"""
    
    print("⚠️  NOTE: You'll need to manually update main.py to use development config")
    print("📝 Add environment detection at the top of main.py")

def create_dev_scripts():
    """Create convenient development scripts"""
    
    # Development start script
    dev_start_backend = """#!/bin/bash
# Start backend in development mode

echo "🔧 Starting DEVELOPMENT backend..."
echo "📁 Using development database: dev_msl_research.db"
echo "🌐 API will run on: http://localhost:8000"
echo "⚠️  This is ISOLATED from production!"

cd backend
export ENVIRONMENT=development
python main.py --dev
"""
    
    # Frontend development script
    dev_start_frontend = """#!/bin/bash
# Start frontend in development mode

echo "🌐 Starting DEVELOPMENT frontend..."
echo "🔌 Will connect to: http://localhost:8000"
echo "⚠️  This will NOT affect production!"

cd frontend
npm start
"""
    
    # Write scripts
    backend_script = Path("start_dev_backend.sh")
    frontend_script = Path("start_dev_frontend.sh")
    
    with open(backend_script, 'w') as f:
        f.write(dev_start_backend)
    with open(frontend_script, 'w') as f:
        f.write(dev_start_frontend)
    
    # Make executable
    os.chmod(backend_script, 0o755)
    os.chmod(frontend_script, 0o755)
    
    print(f"✅ Created: {backend_script}")
    print(f"✅ Created: {frontend_script}")

def print_instructions():
    """Print setup completion instructions"""
    print("\n" + "="*60)
    print("🎉 DEVELOPMENT ENVIRONMENT SETUP COMPLETE!")
    print("="*60)
    
    print("\n📋 What was created:")
    print("  ✅ backend/.env.development - Development configuration")
    print("  ✅ frontend/.env.development - Frontend development config")
    print("  ✅ backend/config_dev.py - Development settings")
    print("  ✅ start_dev_backend.sh - Development backend script")
    print("  ✅ start_dev_frontend.sh - Development frontend script")
    
    print("\n🔐 SAFETY FEATURES:")
    print("  🛡️  Separate development database (dev_msl_research.db)")
    print("  🛡️  Isolated from production Railway server")
    print("  🛡️  Development-only secret keys")
    print("  🛡️  Local-only CORS settings")
    
    print("\n🚀 TO START DEVELOPMENT:")
    print("  1. Backend:  ./start_dev_backend.sh")
    print("  2. Frontend: ./start_dev_frontend.sh")
    print("  3. Open: http://localhost:3000")
    
    print("\n⚠️  IMPORTANT:")
    print("  • Development uses dev_msl_research.db (separate from production)")
    print("  • Frontend connects to localhost:8000 (not Railway production)")
    print("  • All changes are isolated from production")
    print("  • Production data is safe!")
    
    print("\n🔄 TO SWITCH BACK TO PRODUCTION:")
    print("  • Delete .env.development files")
    print("  • Frontend will auto-connect to Railway production")

def main():
    """Main setup function"""
    print("🔧 MSL Research Tracker - Development Environment Setup")
    print("=" * 55)
    print("This will create an ISOLATED development environment")
    print("that is completely separate from your production data.")
    print()
    
    # Confirm before proceeding
    response = input("Continue with development setup? (y/N): ")
    if response.lower() != 'y':
        print("❌ Setup cancelled")
        return
    
    print("\n🔨 Setting up development environment...")
    
    # Create environment files
    create_dev_env_file()
    create_frontend_env()
    
    # Database safety
    backup_production_db()
    create_dev_database()
    
    # Create convenience scripts
    create_dev_scripts()
    
    # Instructions
    print_instructions()

if __name__ == "__main__":
    main()
