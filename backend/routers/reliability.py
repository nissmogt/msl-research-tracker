"""
FastAPI router for Reliability Meter v2 snapshot-based endpoints
Serves precomputed scores for optimal performance using SQLAlchemy 2.0 patterns
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, func
from sqlalchemy.dialects.postgresql import insert
from datetime import date, datetime
from typing import List, Optional
from models import Journal, Article, ReliabilitySnapshot
from schemas_reliability_v2 import TopQuery, SnapshotRow, TAComparison, BulkRefreshRequest, UseCase
from database import get_db
from reliability_meter import ReliabilityMeter, UseCase as ReliabilityUseCase

# Add rate limiting if available
try:
    from middleware.rate_limit import search_rate_limit
    RATE_LIMITING_AVAILABLE = True
except ImportError:
    RATE_LIMITING_AVAILABLE = False
    search_rate_limit = lambda x: x  # No-op decorator

# Safer decorator toggle
rate_limit_decorator = search_rate_limit if RATE_LIMITING_AVAILABLE else (lambda f: f)

router = APIRouter(prefix="/reliability", tags=["reliability"])

@router.post("/top", response_model=List[SnapshotRow])
async def get_top_journals(payload: TopQuery, db: Session = Depends(get_db)):
    """
    Get top-performing journals for a therapeutic area from daily snapshots
    
    This endpoint serves precomputed reliability scores for optimal performance.
    Scores are updated nightly to ensure consistency and speed.
    
    Args:
        payload: Query parameters (TA, use case, date, limit)
        db: Database session
        
    Returns:
        List of top journals with reliability scores
        
    Raises:
        HTTPException: 404 if no data found, 400 for invalid input, 500 for server errors
    """
    try:
        # Parse target date
        target_date = date.fromisoformat(payload.date) if payload.date else date.today()
        
        def _query_for_date(query_date: date):
            """Helper to build query for specific date"""
            return (
                select(ReliabilitySnapshot, Journal.name)
                .join(Journal, Journal.id == ReliabilitySnapshot.journal_id)
                .where(
                    ReliabilitySnapshot.ta == payload.ta.lower(),
                    ReliabilitySnapshot.use_case == payload.use_case,
                    ReliabilitySnapshot.snapshot_date == query_date,
                )
                .order_by(desc(ReliabilitySnapshot.score))
                .limit(payload.limit)
            )
        
        # Try target date first
        result = db.execute(_query_for_date(target_date)).all()
        
        if not result:
            # Graceful fallback to latest available snapshot
            latest_date_stmt = (
                select(func.max(ReliabilitySnapshot.snapshot_date))
                .where(
                    ReliabilitySnapshot.ta == payload.ta.lower(),
                    ReliabilitySnapshot.use_case == payload.use_case
                )
            )
            latest_date = db.execute(latest_date_stmt).scalar()
            
            if not latest_date:
                raise HTTPException(
                    status_code=404,
                    detail=f"No reliability data for TA '{payload.ta}'. Run the initial score computation worker."
                )
            
            # Use latest available data
            result = db.execute(_query_for_date(latest_date)).all()
            print(f"📅 Fallback: Requested {target_date}, serving {latest_date} for {payload.ta}/{payload.use_case}")
        
        # Convert to response format
        return [
            SnapshotRow(
                journal_id=row.ReliabilitySnapshot.journal_id,
                journal_name=row.name,
                ta=row.ReliabilitySnapshot.ta,
                use_case=row.ReliabilitySnapshot.use_case,
                score=row.ReliabilitySnapshot.score,
                band=row.ReliabilitySnapshot.band,
                components=row.ReliabilitySnapshot.components,
                uncertainty=row.ReliabilitySnapshot.uncertainty,
                reasons=row.ReliabilitySnapshot.reasons,
                impact_factor=row.ReliabilitySnapshot.impact_factor,
                version=row.ReliabilitySnapshot.version,
                snapshot_date=str(row.ReliabilitySnapshot.snapshot_date),
            ) for row in result
        ]
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except Exception as e:
        print(f"Error in top_journals: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/ta-comparison", response_model=List[TAComparison])
async def compare_therapeutic_areas(
    use_case: str = "clinical", 
    date_str: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Compare journal quality across different therapeutic areas
    Shows average scores and top performers by TA
    """
    try:
        target_date = date.fromisoformat(date_str) if date_str else date.today()
        
        # Aggregate query for TA comparison using SQLAlchemy 2.0
        stmt = (
            select(
                ReliabilitySnapshot.ta,
                func.count(ReliabilitySnapshot.id).label('journal_count'),
                func.avg(ReliabilitySnapshot.score).label('avg_score'),
                func.max(ReliabilitySnapshot.score).label('max_score')
            )
            .where(
                ReliabilitySnapshot.use_case == use_case,
                ReliabilitySnapshot.snapshot_date == target_date
            )
            .group_by(ReliabilitySnapshot.ta)
            .order_by(desc(func.avg(ReliabilitySnapshot.score)))
        )
        
        aggregates = db.execute(stmt).all()
        
        # Get top journal for each TA
        comparisons = []
        for agg in aggregates:
            # Find top journal for this TA
            top_journal_stmt = (
                select(Journal.name, ReliabilitySnapshot.score)
                .join(Journal, Journal.id == ReliabilitySnapshot.journal_id)
                .where(
                    ReliabilitySnapshot.ta == agg.ta,
                    ReliabilitySnapshot.use_case == use_case,
                    ReliabilitySnapshot.snapshot_date == target_date,
                    ReliabilitySnapshot.score == agg.max_score
                )
                .limit(1)
            )
            
            top_result = db.execute(top_journal_stmt).first()
            
            comparisons.append(TAComparison(
                ta_name=agg.ta.title(),
                journal_count=agg.journal_count,
                avg_score=round(agg.avg_score, 3),
                top_journal=top_result.name if top_result else "Unknown",
                top_score=round(agg.max_score, 3)
            ))
        
        return comparisons
        
    except Exception as e:
        print(f"Error in ta_comparison: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/refresh")
@rate_limit_decorator
async def refresh_scores(
    payload: BulkRefreshRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Force refresh reliability scores for specific therapeutic areas
    WARNING: This is computationally expensive. Use sparingly.
    
    Args:
        payload: Refresh request with TA list and options
        request: HTTP request for client tracking
        db: Database session
        
    Returns:
        Success message with refresh statistics
    """
    # Log the refresh request for monitoring
    client_ip = request.client.host
    print(f"Manual refresh requested by {client_ip} for TAs: {payload.ta_list}")
    
    try:
        meter = ReliabilityMeter()
        refresh_count = 0
        
        for ta in payload.ta_list:
            # Get journals that have articles in this TA (SQLAlchemy 2.0)
            journals_stmt = (
                select(Journal)
                .join(Article, Article.journal == Journal.name)
                .where(Article.therapeutic_area.ilike(f"%{ta}%"))
                .distinct()
            )
            journals = db.execute(journals_stmt).scalars().all()
            
            for journal in journals:
                for use_case_str in payload.use_cases:
                    use_case = ReliabilityUseCase.CLINICAL if use_case_str == "clinical" else ReliabilityUseCase.EXPLORATORY
                    
                    # Check if recent snapshot exists (unless force_recompute)
                    if not payload.force_recompute:
                        existing_stmt = select(ReliabilitySnapshot).where(
                            ReliabilitySnapshot.journal_id == journal.id,
                            ReliabilitySnapshot.ta == ta.lower(),
                            ReliabilitySnapshot.use_case == use_case_str,
                            ReliabilitySnapshot.snapshot_date == date.today()
                        )
                        existing = db.execute(existing_stmt).scalar_one_or_none()
                        
                        if existing:
                            continue  # Skip if recent snapshot exists
                    
                    # Compute new score
                    try:
                        reliability_result = meter.assess_reliability(journal.name, ta, use_case, db)
                        
                        # Upsert snapshot
                        _upsert_snapshot(db, journal, ta, use_case_str, reliability_result)
                        refresh_count += 1
                        
                    except Exception as e:
                        print(f"Failed to compute {journal.name} {ta} {use_case_str}: {e}")
                        continue
        
        db.commit()
        
        return {
            "message": f"Successfully refreshed {refresh_count} reliability scores",
            "ta_list": payload.ta_list,
            "use_cases": payload.use_cases,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        db.rollback()
        print(f"Error in refresh_scores: {e}")
        raise HTTPException(status_code=500, detail=f"Refresh failed: {str(e)}")

def _upsert_snapshot(db: Session, journal: Journal, ta: str, use_case: str, reliability_result):
    """Helper function to insert or update a snapshot record (race-safe for Postgres)"""
    
    # Prepare data
    snapshot_data = {
        "journal_id": journal.id,
        "ta": ta.lower(),
        "use_case": use_case,
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
    except Exception as e:
        # Fallback to SQLite-compatible approach for development
        print(f"PostgreSQL upsert failed, using fallback: {e}")
        existing_stmt = select(ReliabilitySnapshot).where(
            ReliabilitySnapshot.journal_id == journal.id,
            ReliabilitySnapshot.ta == ta.lower(),
            ReliabilitySnapshot.use_case == use_case,
            ReliabilitySnapshot.snapshot_date == date.today(),
        )
        existing = db.execute(existing_stmt).scalar_one_or_none()
        
        if existing:
            # Update existing record
            for key, value in snapshot_data.items():
                setattr(existing, key, value)
        else:
            # Create new record
            new_snapshot = ReliabilitySnapshot(**snapshot_data)
            db.add(new_snapshot)
