#!/usr/bin/env python3
"""
Environment setup script for MSL Research Tracker
Generates required environment variables for deployment
"""

import secrets
import os
from pathlib import Path

def generate_secret_key():
    """Generate a secure secret key"""
    return secrets.token_urlsafe(32)

def create_env_file():
    """Create or update .env file with required variables"""
    env_file = Path(".env")
    
    # Read existing .env if it exists
    existing_vars = {}
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    existing_vars[key] = value
    
    # Generate new variables if not present
    if 'SECRET_KEY' not in existing_vars:
        existing_vars['SECRET_KEY'] = generate_secret_key()
        print(f"✅ Generated SECRET_KEY: {existing_vars['SECRET_KEY'][:10]}...")
    
    if 'OPENAI_API_KEY' not in existing_vars:
        existing_vars['OPENAI_API_KEY'] = 'your_openai_api_key_here'
        print("⚠️  Please set your OPENAI_API_KEY in the .env file")
    
    # Write back to .env file
    with open(env_file, 'w') as f:
        f.write("# MSL Research Tracker Environment Variables\n")
        f.write("# Generated automatically - update with your actual values\n\n")
        
        for key, value in existing_vars.items():
            f.write(f"{key}={value}\n")
    
    print(f"✅ Environment file created/updated: {env_file.absolute()}")

def print_railway_vars():
    """Print environment variables for Railway deployment"""
    secret_key = generate_secret_key()
    
    print("\n🚀 Railway Environment Variables:")
    print("=" * 50)
    print(f"OPENAI_API_KEY=your_actual_openai_api_key")
    print(f"SECRET_KEY={secret_key}")
    print("=" * 50)
    print("\n💡 Copy these to your Railway project environment variables")

if __name__ == "__main__":
    print("🔧 MSL Research Tracker Environment Setup")
    print("=" * 40)
    
    # Create local .env file
    create_env_file()
    
    # Show Railway variables
    print_railway_vars() 