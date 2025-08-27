#!/usr/bin/env python3
"""
Database migration script to add insights column to articles table.
Run this once to update your existing database schema.
"""

import sqlite3
import os

def add_insights_column():
    """Add insights column to articles table if it doesn't exist."""
    db_path = "msl_research.db"
    
    # Check if database exists
    if not os.path.exists(db_path):
        print("Database not found, it will be created with the new schema when the app starts.")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if insights column already exists
        cursor.execute("PRAGMA table_info(articles)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'insights' not in columns:
            print("Adding insights column to articles table...")
            cursor.execute("ALTER TABLE articles ADD COLUMN insights TEXT")
            conn.commit()
            print("✅ Successfully added insights column to articles table")
        else:
            print("✅ Insights column already exists in articles table")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error updating database: {e}")

if __name__ == "__main__":
    add_insights_column()
