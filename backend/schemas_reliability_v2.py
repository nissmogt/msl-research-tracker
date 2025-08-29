"""
Pydantic v2 schemas for Reliability Meter v2 API contracts
Implements the CS spec for TA-aware journal reliability assessment
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime, date
from enum import Enum

class UseCase(str, Enum):
    """Use case enum for reliability assessment context"""
    CLINICAL = "clinical"
    EXPLORATORY = "exploratory"

class ReliabilityBand(str, Enum):
    """Reliability band classification"""
    HIGH = "high"              # 0.80-1.00: Highest confidence
    MODERATE = "moderate"      # 0.60-0.79: Good confidence  
    EXPLORATORY = "exploratory" # 0.40-0.59: Moderate confidence
    LOW = "low"               # 0.00-0.39: Lower confidence

class UncertaintyLevel(str, Enum):
    """Uncertainty quantification levels"""
    LOW = "low"       # High evidence, stable metrics
    MEDIUM = "medium" # Moderate evidence
    HIGH = "high"     # Limited evidence, interpret cautiously

# Request Schemas
class ReliabilityRequest(BaseModel):
    """Request for journal reliability assessment"""
    journal_name: str = Field(..., min_length=1, max_length=200, description="Journal name to assess")
    therapeutic_area: str = Field(..., min_length=1, max_length=100, description="Therapeutic area context")
    use_case: UseCase = Field(..., description="Clinical vs exploratory research context")
    
    @field_validator('journal_name', 'therapeutic_area')
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Field cannot be empty or whitespace only')
        return v.strip()

class BulkReliabilityRequest(BaseModel):
    """Batch request for multiple journal assessments"""
    assessments: List[ReliabilityRequest] = Field(..., min_length=1, max_length=50)
    cache_results: bool = Field(default=True, description="Whether to cache computed scores")

# Component Schemas
class ReliabilityComponents(BaseModel):
    """The 5 dimensions of journal reliability with detailed breakdown"""
    authority_ta: float = Field(..., ge=0.0, le=1.0, description="TA-specific citation authority (PageRank)")
    relevance_ta: float = Field(..., ge=0.0, le=1.0, description="Semantic alignment to TA (embedding similarity)")
    freshness_ta: float = Field(..., ge=0.0, le=1.0, description="Recent publication activity in TA")
    guideline: float = Field(..., ge=0.0, le=1.0, description="Presence in clinical guidelines")
    rigor: float = Field(..., ge=0.0, le=1.0, description="Editorial integrity proxies")
    
    # Raw component details for explainability
    authority_details: Optional[Dict[str, Any]] = Field(default=None, description="PageRank computation details")
    relevance_details: Optional[Dict[str, Any]] = Field(default=None, description="Embedding similarity breakdown")
    freshness_details: Optional[Dict[str, Any]] = Field(default=None, description="Recent article analysis")
    guideline_details: Optional[Dict[str, Any]] = Field(default=None, description="Guideline citation breakdown")
    rigor_details: Optional[Dict[str, Any]] = Field(default=None, description="Integrity signal analysis")

class WeightProfile(BaseModel):
    """Use case specific weight configuration"""
    use_case: UseCase
    alpha: float = Field(..., ge=0.0, le=1.0, description="Authority weight")
    beta: float = Field(..., ge=0.0, le=1.0, description="Relevance weight") 
    gamma: float = Field(..., ge=0.0, le=1.0, description="Freshness weight")
    delta: float = Field(..., ge=0.0, le=1.0, description="Guideline weight")
    epsilon: float = Field(..., ge=0.0, le=1.0, description="Rigor weight")
    
    @field_validator('alpha', 'beta', 'gamma', 'delta', 'epsilon')
    @classmethod
    def validate_weight_sum(cls, v, info):
        # Note: Full validation of weight sum = 1.0 should be done at the model level
        return v

# Response Schemas  
class ReliabilityResponse(BaseModel):
    """Complete reliability assessment response"""
    journal_name: str
    therapeutic_area: str
    use_case: UseCase
    
    # Core scoring results
    composite_score: float = Field(..., ge=0.0, le=1.0, description="Final weighted reliability score")
    reliability_band: ReliabilityBand = Field(..., description="Human-readable reliability classification")
    components: ReliabilityComponents = Field(..., description="Detailed component breakdown")
    
    # Uncertainty and explainability
    uncertainty_level: UncertaintyLevel = Field(..., description="Confidence in the assessment")
    explanation_reasons: List[str] = Field(..., min_length=1, description="Human-readable explanations")
    
    # Metadata and audit trail
    evidence_article_count: int = Field(..., ge=0, description="Number of articles used as evidence")
    computation_timestamp: datetime = Field(..., description="When this score was computed")
    score_version: str = Field(default="v2.0", description="Reliability algorithm version")
    
    # Context for comparison
    traditional_impact_factor: Optional[float] = Field(default=None, description="Traditional IF for reference")
    percentile_rank_in_ta: Optional[float] = Field(default=None, ge=0.0, le=100.0, description="Percentile rank within TA")

class BulkReliabilityResponse(BaseModel):
    """Batch response for multiple assessments"""
    assessments: List[ReliabilityResponse]
    computation_summary: Dict[str, Any] = Field(..., description="Batch processing metadata")

# Citation and Authority Schemas
class CitationCreate(BaseModel):
    """Schema for creating citation relationships"""
    citing_article_pubmed_id: str = Field(..., min_length=1)
    cited_article_pubmed_id: str = Field(..., min_length=1)
    citation_context: Optional[str] = Field(default=None, max_length=1000)
    citation_weight: float = Field(default=1.0, ge=0.0, le=10.0)

class CitationResponse(BaseModel):
    """Citation relationship data"""
    id: int
    citing_article_id: int
    cited_article_id: int
    citation_context: Optional[str]
    citation_weight: float
    created_at: datetime

# Guideline Citation Schemas
class GuidelineCiteCreate(BaseModel):
    """Schema for recording guideline citations"""
    journal_name: str = Field(..., min_length=1, max_length=200)
    therapeutic_area: str = Field(..., min_length=1, max_length=100)
    guideline_source: str = Field(..., min_length=1, max_length=50)  # NCCN, ASCO, etc.
    guideline_title: str = Field(..., min_length=1, max_length=300)
    citation_count: int = Field(default=1, ge=1)
    guideline_year: int = Field(..., ge=1950, le=2030)
    evidence_level: Optional[str] = Field(default=None, max_length=20)

class GuidelineCiteResponse(BaseModel):
    """Guideline citation data"""
    id: int
    journal_id: int
    therapeutic_area: str
    guideline_source: str
    guideline_title: str
    citation_count: int
    guideline_year: int
    citation_weight: float
    evidence_level: Optional[str]
    created_at: datetime

# Rigor Signal Schemas
class RigorSignalCreate(BaseModel):
    """Schema for recording editorial rigor signals"""
    journal_name: str = Field(..., min_length=1, max_length=200)
    signal_type: str = Field(..., description="retraction, correction, editorial_policy, etc.")
    signal_date: datetime
    article_pubmed_id: Optional[str] = Field(default=None, description="Specific article if applicable")
    signal_severity: str = Field(default="medium", description="low, medium, high")
    signal_description: Optional[str] = Field(default=None, max_length=1000)
    signal_source: str = Field(..., min_length=1, max_length=100)  # PubMed, Retraction Watch

class RigorSignalResponse(BaseModel):
    """Rigor signal data"""
    id: int
    journal_id: int
    signal_type: str
    signal_date: datetime
    article_id: Optional[int]
    signal_severity: str
    signal_description: Optional[str]
    signal_source: str
    created_at: datetime

# Analytics and Comparison Schemas
class TAAnalytics(BaseModel):
    """Therapeutic area reliability analytics"""
    therapeutic_area: str
    journal_count: int
    avg_reliability_score: float
    score_distribution: Dict[ReliabilityBand, int]
    top_journals: List[Dict[str, Any]]
    bottom_journals: List[Dict[str, Any]]
    uncertainty_analysis: Dict[UncertaintyLevel, int]

class JournalComparison(BaseModel):
    """Side-by-side journal comparison"""
    journal_a: ReliabilityResponse
    journal_b: ReliabilityResponse
    comparison_insights: List[str]
    winner_by_component: Dict[str, str]  # Which journal wins each component
    overall_recommendation: str

# Configuration and Admin Schemas
class ReliabilityConfig(BaseModel):
    """Configuration for reliability assessment system"""
    weight_profiles: Dict[UseCase, WeightProfile]
    normalization_parameters: Dict[str, Any]
    embedding_model: str = Field(default="text-embedding-ada-002")
    pagerank_damping: float = Field(default=0.85, ge=0.0, le=1.0)
    freshness_decay_rate: float = Field(default=0.1, ge=0.0, le=1.0)
    
class SystemHealth(BaseModel):
    """System health and performance metrics"""
    database_status: str
    embedding_cache_hit_rate: float
    avg_computation_time_ms: float
    cached_scores_count: int
    last_batch_update: Optional[datetime]
    
# Validation test schemas for CS spec compliance
class ValidationTest(BaseModel):
    """Test case for reliability meter validation"""
    test_name: str
    journal_a: str
    journal_b: str  
    therapeutic_area: str
    use_case: UseCase
    expected_winner: str  # journal_a or journal_b
    expected_reason: str
    tolerance: float = Field(default=0.05, ge=0.0, le=0.5)

class ValidationResult(BaseModel):
    """Result of reliability meter validation test"""
    test: ValidationTest
    score_a: float
    score_b: float
    actual_winner: str
    test_passed: bool
    score_difference: float
    execution_time_ms: float
    detailed_breakdown: Dict[str, Any]

# Snapshot-based API Schemas for Performance-Optimized Serving
class SnapshotRow(BaseModel):
    """Individual reliability snapshot record for API responses"""
    journal_id: int
    journal_name: str
    ta: str
    use_case: UseCase
    score: float
    band: ReliabilityBand
    components: ReliabilityComponents
    uncertainty: UncertaintyLevel
    reasons: List[str]
    impact_factor: float
    version: str
    snapshot_date: str  # YYYY-MM-DD format

class TopQuery(BaseModel):
    """Query for top-performing journals in a therapeutic area"""
    ta: str = Field(..., min_length=1, description="Therapeutic area (e.g., 'oncology')")
    use_case: UseCase = Field(default="clinical", description="Clinical vs exploratory context")
    date: Optional[str] = Field(default=None, description="Date in YYYY-MM-DD format (default: today)")
    limit: int = Field(default=25, ge=1, le=100, description="Number of results to return")

class TAComparison(BaseModel):
    """Comparative analysis across therapeutic areas"""
    ta_name: str
    journal_count: int
    avg_score: float
    top_journal: str
    top_score: float

class BulkRefreshRequest(BaseModel):
    """Request for bulk score refresh (admin-only)"""
    ta_list: List[str] = Field(..., min_length=1, max_length=10)
    use_cases: List[UseCase] = Field(default=["clinical", "exploratory"])
    force_recompute: bool = Field(default=False, description="Force recomputation even if recent snapshot exists")
