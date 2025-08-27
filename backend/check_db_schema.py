#!/usr/bin/env python3
"""
Check the current database schema and add insights column if needed.
This will run automatically on Railway startup.
"""

import os
import sqlite3
from sqlalchemy import inspect
from database import engine

def ensure_insights_column():
    """Ensure insights column exists in articles table."""
    try:
        # Use SQLAlchemy inspector to check schema
        inspector = inspect(engine)
        columns = inspector.get_columns('articles')
        column_names = [col['name'] for col in columns]
        
        print(f"Current articles table columns: {column_names}")
        
        if 'insights' not in column_names:
            print("Adding insights column to articles table...")
            
            # Add the column using proper SQLAlchemy syntax
            from sqlalchemy import text
            with engine.connect() as connection:
                connection.execute(text("ALTER TABLE articles ADD COLUMN insights TEXT"))
                connection.commit()
            
            print("✅ Successfully added insights column")
        else:
            print("✅ Insights column already exists")
            
    except Exception as e:
        print(f"Error checking/updating database schema: {e}")
        # If column creation fails, we'll handle it gracefully in the application

if __name__ == "__main__":
    ensure_insights_column()
