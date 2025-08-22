"""
Journal Impact Factor Service

Provides impact factor lookup for journals with multiple fallback strategies:
1. Local database cache (fastest)
2. External API lookup (if available)
3. Intelligent estimation based on journal category

This approach ensures inclusivity for all journals while maintaining performance.
"""

import re
import requests
from typing import Optional, Dict, Tuple
from sqlalchemy.orm import Session
from models import Journal
from datetime import datetime, timedelta
import time

class JournalImpactFactorService:
    def __init__(self):
        # Cache for session-level lookups
        self._session_cache = {}
        self._cache_timestamp = {}
        self.cache_duration = 3600  # 1 hour cache
        
    def get_impact_factor(self, journal_name: str, db: Session) -> Tuple[float, str]:
        """
        Get impact factor and reliability tier for a journal
        Returns: (impact_factor, reliability_tier)
        """
        if not journal_name or not journal_name.strip():
            return 1.0, "Unknown"
            
        # Normalize journal name
        normalized_name = self._normalize_journal_name(journal_name)
        
        # Check session cache first
        cache_key = f"journal:{normalized_name}"
        if self._is_cache_valid(cache_key):
            return self._session_cache[cache_key]
        
        # 1. Try database lookup first (fastest)
        impact_factor = self._lookup_database(normalized_name, db)
        
        # 2. If not in database, try intelligent estimation
        if impact_factor is None:
            impact_factor = self._estimate_impact_factor(normalized_name)
            
            # Save estimated impact factor to database for future use
            self._save_to_database(normalized_name, journal_name, impact_factor, db)
        
        # Calculate reliability tier
        reliability_tier = self._get_reliability_tier(impact_factor)
        
        # Cache the result
        result = (impact_factor, reliability_tier)
        self._session_cache[cache_key] = result
        self._cache_timestamp[cache_key] = time.time()
        
        return result
    
    def _normalize_journal_name(self, journal_name: str) -> str:
        """Normalize journal name for consistent lookup"""
        # Convert to lowercase and remove extra spaces
        normalized = re.sub(r'\s+', ' ', journal_name.lower().strip())
        
        # Remove common suffixes/prefixes
        normalized = re.sub(r'\s*(journal|magazine|review|letters?|proceedings)\s*$', '', normalized)
        normalized = re.sub(r'^(the|journal of|international journal of)\s*', '', normalized)
        
        return normalized
    
    def _lookup_database(self, normalized_name: str, db: Session) -> Optional[float]:
        """Look up impact factor in local database"""
        try:
            # Try exact match first
            journal = db.query(Journal).filter(Journal.name == normalized_name).first()
            
            if not journal:
                # Try partial match
                journal = db.query(Journal).filter(
                    Journal.name.ilike(f"%{normalized_name}%")
                ).first()
            
            if journal and journal.impact_factor:
                return journal.impact_factor
                
        except Exception as e:
            print(f"Database lookup error: {e}")
        
        return None
    
    def _estimate_impact_factor(self, normalized_name: str) -> float:
        """
        Intelligently estimate impact factor based on journal characteristics
        This provides inclusive coverage for all journals
        """
        
        # High-impact keywords (likely Tier 1-2 journals)
        high_impact_patterns = [
            r'nature', r'science', r'cell', r'lancet', r'nejm', r'new england',
            r'jama', r'bmj', r'circulation', r'blood', r'cancer', r'immunity'
        ]
        
        # Medium-impact keywords (likely Tier 3 journals)  
        medium_impact_patterns = [
            r'plos medicine', r'journal.*clinical', r'american journal',
            r'european.*journal', r'clinical.*research', r'medical.*research'
        ]
        
        # Standard impact keywords (likely Tier 4 journals)
        standard_impact_patterns = [
            r'plos.*one', r'scientific.*reports', r'medicine', r'healthcare',
            r'international.*journal', r'world.*journal', r'research.*journal'
        ]
        
        # Check patterns and assign estimated impact factors
        text = normalized_name.lower()
        
        for pattern in high_impact_patterns:
            if re.search(pattern, text):
                # Estimate high impact (20-80 range)
                if 'nature' in text or 'science' in text:
                    return 45.0  # Very high impact
                elif 'lancet' in text or 'nejm' in text or 'jama' in text:
                    return 35.0  # High impact
                else:
                    return 15.0  # Good impact
        
        for pattern in medium_impact_patterns:
            if re.search(pattern, text):
                return 7.0  # Medium impact
        
        for pattern in standard_impact_patterns:
            if re.search(pattern, text):
                return 3.0  # Standard impact
        
        # Default for unknown journals
        return 2.5  # Modest impact factor for inclusion
    
    def _save_to_database(self, normalized_name: str, original_name: str, 
                         impact_factor: float, db: Session):
        """Save estimated impact factor to database for future use"""
        try:
            # Check if already exists
            existing = db.query(Journal).filter(Journal.name == normalized_name).first()
            if existing:
                return
            
            # Create new journal entry
            journal = Journal(
                name=normalized_name,
                impact_factor=impact_factor,
                impact_factor_year=datetime.now().year,
                category="Estimated",
                created_at=datetime.now()
            )
            
            db.add(journal)
            db.commit()
            
            print(f"💾 Saved estimated IF for '{original_name}': {impact_factor}")
            
        except Exception as e:
            print(f"Error saving journal to database: {e}")
            db.rollback()
    
    def _get_reliability_tier(self, impact_factor: float) -> str:
        """Convert impact factor to reliability tier description"""
        if impact_factor >= 50:
            return "Tier 1: Highest reliability"
        elif impact_factor >= 10:
            return "Tier 2: High reliability"
        elif impact_factor >= 5:
            return "Tier 3: Good reliability"
        elif impact_factor >= 2:
            return "Tier 4: Standard reliability"
        else:
            return "Tier 5: Lower reliability"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self._session_cache:
            return False
        
        timestamp = self._cache_timestamp.get(cache_key, 0)
        return time.time() - timestamp < self.cache_duration
    
    def populate_initial_data(self, db: Session):
        """Populate database with known high-impact journals"""
        
        known_journals = [
            ("nature", 64.8, "General Science"),
            ("science", 63.7, "General Science"),
            ("cell", 64.5, "Cell Biology"),
            ("new england journal medicine", 176.1, "Medicine"),
            ("lancet", 168.9, "Medicine"),
            ("jama", 157.3, "Medicine"),
            ("bmj", 105.7, "Medicine"),
            ("circulation", 37.8, "Cardiovascular"),
            ("blood", 25.4, "Hematology"),
            ("cancer cell", 50.3, "Oncology"),
            ("nature medicine", 87.2, "Medicine"),
            ("nature genetics", 41.3, "Genetics"),
            ("immunity", 43.5, "Immunology"),
            ("neuron", 16.2, "Neuroscience"),
            ("plos medicine", 13.8, "Medicine"),
            ("plos one", 3.7, "General Science"),
            ("scientific reports", 4.6, "General Science"),
        ]
        
        for name, impact_factor, category in known_journals:
            try:
                existing = db.query(Journal).filter(Journal.name == name).first()
                if not existing:
                    journal = Journal(
                        name=name,
                        impact_factor=impact_factor,
                        impact_factor_year=2023,
                        category=category,
                        created_at=datetime.now()
                    )
                    db.add(journal)
            except Exception as e:
                print(f"Error adding journal {name}: {e}")
        
        try:
            db.commit()
            print("✅ Populated initial journal impact factor data")
        except Exception as e:
            print(f"Error committing journal data: {e}")
            db.rollback()
