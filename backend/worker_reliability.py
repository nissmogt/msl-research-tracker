#!/usr/bin/env python3
"""
Nightly Reliability Score Computation Worker
Updates all journal reliability snapshots for consistent API performance

Usage:
  python worker_reliability.py                    # Compute today's snapshots
  python worker_reliability.py --date 2024-01-15  # Compute for specific date
  python worker_reliability.py --ta oncology      # Compute only for specific TA

Railway Cron Setup:
  Add to railway.json or use Railway dashboard:
  - Schedule: "0 2 * * *" (2 AM daily)
  - Command: "python -m backend.worker_reliability"
"""

import argparse
import sys
from datetime import date, datetime
from typing import List, Optional
from sqlalchemy import select, distinct
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from database import SessionLocal
from models import Journal, Article, ReliabilitySnapshot, TherapeuticArea
from reliability_meter import ReliabilityMeter, UseCase
from providers import EmbeddingProvider

# Default therapeutic areas to process (expand as needed)
DEFAULT_TA_LIST = [
    "oncology", 
    "cardiovascular", 
    "neurology",
    "immunology",
    "endocrinology",
    "respiratory",
    "gastroenterology"
]

def _upsert_snapshot(db: Session, journal: Journal, ta: str, use_case: UseCase, reliability_result):
    """Helper function to insert or update a snapshot record (race-safe for Postgres)"""
    
    snapshot_data = {
        "journal_id": journal.id,
        "ta": ta.lower(),
        "use_case": use_case.value,
        "score": reliability_result.score,
        "band": reliability_result.band.value,
        "components": {
            "authority_ta": reliability_result.components.authority_ta,
            "relevance_ta": reliability_result.components.relevance_ta,
            "freshness_ta": reliability_result.components.freshness_ta,
            "guideline": reliability_result.components.guideline,
            "rigor": reliability_result.components.rigor
        },
        "uncertainty": reliability_result.uncertainty,
        "reasons": reliability_result.reasons,
        "impact_factor": reliability_result.impact_factor,
        "version": "v2",
        "snapshot_date": date.today(),
    }
    
    # Use PostgreSQL-specific upsert for race safety
    try:
        stmt = insert(ReliabilitySnapshot).values(**snapshot_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=[
                ReliabilitySnapshot.journal_id,
                ReliabilitySnapshot.ta,
                ReliabilitySnapshot.use_case,
                ReliabilitySnapshot.snapshot_date
            ],
            set_={
                "score": stmt.excluded.score,
                "band": stmt.excluded.band,
                "components": stmt.excluded.components,
                "uncertainty": stmt.excluded.uncertainty,
                "reasons": stmt.excluded.reasons,
                "impact_factor": stmt.excluded.impact_factor,
                "version": stmt.excluded.version,
            }
        )
        db.execute(stmt)
        print(f"  ✅ Upserted: {journal.name} | {ta} | {use_case.value}")
    except Exception as e:
        # Fallback to SQLite-compatible approach for development
        print(f"PostgreSQL upsert failed, using fallback: {str(e)[:50]}...")
        existing_stmt = select(ReliabilitySnapshot).where(
            ReliabilitySnapshot.journal_id == journal.id,
            ReliabilitySnapshot.ta == ta.lower(),
            ReliabilitySnapshot.use_case == use_case.value,
            ReliabilitySnapshot.snapshot_date == date.today(),
        )
        existing_row = db.execute(existing_stmt).scalar_one_or_none()
        
        if existing_row:
            # Update existing record
            for key, value in snapshot_data.items():
                setattr(existing_row, key, value)
            print(f"  ✅ Updated: {journal.name} | {ta} | {use_case.value}")
        else:
            # Create new record
            new_snapshot = ReliabilitySnapshot(**snapshot_data)
            db.add(new_snapshot)
            print(f"  ➕ Created: {journal.name} | {ta} | {use_case.value}")

def get_journals_with_ta_articles(db: Session, ta: str) -> List[Journal]:
    """Get journals that have published articles in the specified TA"""
    stmt = (
        select(Journal)
        .join(Article, Article.journal == Journal.name)
        .where(Article.therapeutic_area.ilike(f"%{ta}%"))
        .distinct()
    )
    return db.execute(stmt).scalars().all()

def run_worker(target_date: date = None, ta_filter: str = None, force_recompute: bool = False):
    """
    Main worker function to compute reliability snapshots
    
    Args:
        target_date: Date to compute snapshots for (default: today)
        ta_filter: Only process this specific TA (default: all TAs)
        force_recompute: Recompute even if snapshot exists (default: False)
    """
    if target_date is None:
        target_date = date.today()
    
    print(f"🔄 Starting reliability score computation for {target_date}")
    print(f"📊 TA Filter: {ta_filter or 'All TAs'}")
    print(f"🔥 Force Recompute: {force_recompute}")
    print("-" * 60)
    
    meter = ReliabilityMeter()
    total_computed = 0
    total_skipped = 0
    total_errors = 0
    
    with SessionLocal() as db:
        try:
            # Determine which TAs to process
            if ta_filter:
                ta_list = [ta_filter.lower()]
            else:
                # Get TAs from database or use default list
                try:
                    ta_stmt = select(distinct(TherapeuticArea.name))
                    db_tas = [row[0].lower() for row in db.execute(ta_stmt).all()]
                    ta_list = db_tas if db_tas else DEFAULT_TA_LIST
                except:
                    ta_list = DEFAULT_TA_LIST
            
            print(f"📋 Processing TAs: {ta_list}")
            
            for ta in ta_list:
                print(f"\n🔍 Processing TA: {ta.upper()}")
                
                # Get journals with articles in this TA
                journals = get_journals_with_ta_articles(db, ta)
                print(f"   Found {len(journals)} journals with {ta} articles")
                
                if not journals:
                    print(f"   ⚠️  No journals found for TA: {ta}")
                    continue
                
                # Process each journal for both use cases
                for journal in journals:
                    for use_case in [UseCase.CLINICAL, UseCase.EXPLORATORY]:
                        try:
                            # Check if snapshot already exists (unless force_recompute)
                            if not force_recompute:
                                existing_stmt = select(ReliabilitySnapshot).where(
                                    ReliabilitySnapshot.journal_id == journal.id,
                                    ReliabilitySnapshot.ta == ta,
                                    ReliabilitySnapshot.use_case == use_case.value,
                                    ReliabilitySnapshot.snapshot_date == target_date
                                )
                                existing = db.execute(existing_stmt).scalar_one_or_none()
                                
                                if existing:
                                    total_skipped += 1
                                    continue
                            
                            # Compute reliability score
                            reliability_result = meter.assess_reliability(
                                journal.name, ta, use_case, db
                            )
                            
                            # Upsert snapshot
                            _upsert_snapshot(db, journal, ta, use_case, reliability_result)
                            total_computed += 1
                            
                        except Exception as e:
                            total_errors += 1
                            print(f"  ❌ Error: {journal.name} | {ta} | {use_case.value}: {str(e)[:100]}")
                            continue
                
                # Commit after each TA to avoid large transactions
                db.commit()
                print(f"   ✅ Committed {ta} snapshots to database")
            
            print("\n" + "=" * 60)
            print(f"🎉 Worker completed successfully!")
            print(f"   📊 Total computed: {total_computed}")
            print(f"   ⏭️  Total skipped: {total_skipped}")
            print(f"   ❌ Total errors: {total_errors}")
            print(f"   📅 Date: {target_date}")
            print(f"   ⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
        except Exception as e:
            db.rollback()
            print(f"\n💥 Fatal error in worker: {e}")
            raise

def main():
    """Command-line interface for the worker"""
    parser = argparse.ArgumentParser(description="Reliability Score Computation Worker")
    parser.add_argument(
        "--date", 
        type=str, 
        help="Target date in YYYY-MM-DD format (default: today)"
    )
    parser.add_argument(
        "--ta", 
        type=str, 
        help="Process only this therapeutic area (default: all TAs)"
    )
    parser.add_argument(
        "--force", 
        action="store_true", 
        help="Force recomputation even if snapshot exists"
    )
    
    args = parser.parse_args()
    
    # Parse target date
    target_date = None
    if args.date:
        try:
            target_date = date.fromisoformat(args.date)
        except ValueError:
            print(f"❌ Invalid date format: {args.date}. Use YYYY-MM-DD format.")
            sys.exit(1)
    
    # Run the worker
    try:
        run_worker(
            target_date=target_date,
            ta_filter=args.ta,
            force_recompute=args.force
        )
    except KeyboardInterrupt:
        print("\n⏹️  Worker interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Worker failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
