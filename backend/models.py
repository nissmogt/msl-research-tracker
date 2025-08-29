from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float, Index, JSON, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Journal(Base):
    __tablename__ = "journals"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    issn = Column(String, index=True)  # International Standard Serial Number
    impact_factor = Column(Float)
    impact_factor_year = Column(Integer)  # Year of the impact factor
    category = Column(String)  # Medical specialty category
    publisher = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class TherapeuticArea(Base):
    __tablename__ = "therapeutic_areas"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text)
    
    conversations = relationship("Conversation", back_populates="therapeutic_area")

class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    pubmed_id = Column(String, unique=True, index=True, nullable=False)
    title = Column(Text, nullable=False)
    authors = Column(Text)  # JSON string
    abstract = Column(Text)
    publication_date = Column(String)
    journal = Column(String)
    therapeutic_area = Column(String)
    link = Column(String)
    rss_fetch_date = Column(String)
    # insights = Column(Text)  # Store the generated insights - temporarily disabled until DB migration
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    ta_id = Column(Integer, ForeignKey("therapeutic_areas.id"), nullable=False)
    title = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    therapeutic_area = relationship("TherapeuticArea", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    content = Column(Text, nullable=False)
    is_ai = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    conversation = relationship("Conversation", back_populates="messages")

# Reliability Meter v2 Models - Citation Analysis & Authority Scoring
class Citation(Base):
    """Citation relationships between articles for authority scoring via PageRank"""
    __tablename__ = "citations"
    
    id = Column(Integer, primary_key=True, index=True)
    citing_article_id = Column(Integer, ForeignKey("articles.id"), nullable=False, index=True)
    cited_article_id = Column(Integer, ForeignKey("articles.id"), nullable=False, index=True)
    citation_context = Column(Text)  # Context around the citation for relevance scoring
    citation_weight = Column(Float, default=1.0)  # Weighted importance of citation
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    citing_article = relationship("Article", foreign_keys=[citing_article_id], backref="citations_made")
    cited_article = relationship("Article", foreign_keys=[cited_article_id], backref="citations_received")
    
    # Composite index for efficient PageRank queries
    __table_args__ = (
        Index('idx_citation_citing_cited', 'citing_article_id', 'cited_article_id'),
        Index('idx_citation_cited_citing', 'cited_article_id', 'citing_article_id'),
    )

class GuidelineCite(Base):
    """Presence in clinical guidelines for clinical authority scoring"""
    __tablename__ = "guideline_cites"
    
    id = Column(Integer, primary_key=True, index=True)
    journal_id = Column(Integer, ForeignKey("journals.id"), nullable=False, index=True)
    therapeutic_area = Column(String, nullable=False, index=True)
    guideline_source = Column(String, nullable=False)  # NCCN, ASCO, ESMO, FDA, etc.
    guideline_title = Column(String, nullable=False)
    citation_count = Column(Integer, default=1)  # Number of citations in this guideline
    guideline_year = Column(Integer, nullable=False)
    citation_weight = Column(Float, default=1.0)  # Weighted by guideline importance
    evidence_level = Column(String)  # Level I, II, III, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    journal = relationship("Journal", backref="guideline_citations")
    
    # Composite index for TA-specific guideline queries
    __table_args__ = (
        Index('idx_guideline_journal_ta', 'journal_id', 'therapeutic_area'),
        Index('idx_guideline_ta_year', 'therapeutic_area', 'guideline_year'),
    )

class RigorSignal(Base):
    """Editorial rigor and integrity signals for rigor scoring"""
    __tablename__ = "rigor_signals"
    
    id = Column(Integer, primary_key=True, index=True)
    journal_id = Column(Integer, ForeignKey("journals.id"), nullable=False, index=True)
    signal_type = Column(String, nullable=False)  # retraction, correction, editorial_policy, peer_review_type
    signal_date = Column(DateTime(timezone=True), nullable=False)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=True)  # Specific article if applicable
    signal_severity = Column(String, default='medium')  # low, medium, high
    signal_description = Column(Text)
    signal_source = Column(String)  # PubMed, Retraction Watch, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    journal = relationship("Journal", backref="rigor_signals")
    article = relationship("Article", backref="rigor_signals")
    
    # Index for temporal rigor analysis
    __table_args__ = (
        Index('idx_rigor_journal_date', 'journal_id', 'signal_date'),
        Index('idx_rigor_type_severity', 'signal_type', 'signal_severity'),
    )

class EmbeddingCache(Base):
    """Cache for expensive embedding computations in relevance scoring"""
    __tablename__ = "embedding_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    content_hash = Column(String, unique=True, index=True, nullable=False)  # Hash of input text
    content_type = Column(String, nullable=False)  # journal_abstract, ta_ontology, etc.
    embedding_vector = Column(Text, nullable=False)  # JSON serialized vector
    embedding_model = Column(String, nullable=False)  # text-embedding-ada-002, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    accessed_at = Column(DateTime(timezone=True), server_default=func.now())
    access_count = Column(Integer, default=1)
    
    # Index for cache lookups and cleanup
    __table_args__ = (
        Index('idx_embedding_type_model', 'content_type', 'embedding_model'),
        Index('idx_embedding_accessed', 'accessed_at'),
    )

class ReliabilityScore(Base):
    """Precomputed reliability scores for performance and audit trail"""
    __tablename__ = "reliability_scores"
    
    id = Column(Integer, primary_key=True, index=True)
    journal_id = Column(Integer, ForeignKey("journals.id"), nullable=False, index=True)
    therapeutic_area = Column(String, nullable=False, index=True)
    use_case = Column(String, nullable=False)  # clinical, exploratory
    
    # Component scores (0.0-1.0)
    authority_ta = Column(Float, nullable=False)
    relevance_ta = Column(Float, nullable=False)
    freshness_ta = Column(Float, nullable=False)
    guideline = Column(Float, nullable=False)
    rigor = Column(Float, nullable=False)
    
    # Final composite score and metadata
    composite_score = Column(Float, nullable=False, index=True)
    reliability_band = Column(String, nullable=False)  # high, moderate, exploratory, low
    uncertainty_level = Column(String, nullable=False)  # low, medium, high
    explanation_reasons = Column(Text, nullable=False)  # JSON array of explanation strings
    
    # Versioning and audit trail
    score_version = Column(String, nullable=False, default='v2.0')
    computation_date = Column(DateTime(timezone=True), server_default=func.now())
    evidence_article_count = Column(Integer, default=0)
    
    # Relationships
    journal = relationship("Journal", backref="reliability_scores")
    
    # Composite index for efficient scoring queries
    __table_args__ = (
        Index('idx_reliability_journal_ta_case', 'journal_id', 'therapeutic_area', 'use_case'),
        Index('idx_reliability_ta_score', 'therapeutic_area', 'composite_score'),
        Index('idx_reliability_computation_date', 'computation_date'),
    )

# --- ReliabilitySnapshot for Performance-Optimized Scoring ---
class ReliabilitySnapshot(Base):
    """
    Precomputed reliability scores stored as daily snapshots for performance.
    Enables sub-second API responses and consistent scoring across sessions.
    """
    __tablename__ = "reliability_snapshots"

    id = Column(Integer, primary_key=True)
    journal_id = Column(Integer, ForeignKey("journals.id", ondelete="CASCADE"), nullable=False, index=True)
    ta = Column(String(64), nullable=False, index=True)  # therapeutic_area
    use_case = Column(String(16), nullable=False, index=True)  # "clinical" | "exploratory"
    score = Column(Float, nullable=False)
    band = Column(String(16), nullable=False)  # "high" | "moderate" | "exploratory" | "low"
    components = Column(JSON, nullable=False)  # {authority_ta, relevance_ta, freshness_ta, guideline, rigor}
    uncertainty = Column(String(16), nullable=False)  # "low" | "medium" | "high"
    reasons = Column(JSON, nullable=False)  # List[str] explanations
    impact_factor = Column(Float, default=1.0)
    version = Column(String(32), default="v2")
    snapshot_date = Column(Date, nullable=False, index=True)  # YYYY-MM-DD
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    journal = relationship("Journal", backref="reliability_snapshots")

    # Performance-optimized indexes
    __table_args__ = (
        # Top-K query index for fastest retrieval
        Index("ix_snapshots_ta_uc_date_score_desc", "ta", "use_case", "snapshot_date", "score"),
        # Enforce one snapshot per (journal, ta, use_case, date)
        Index("uq_snapshots_journal_ta_uc_date", "journal_id", "ta", "use_case", "snapshot_date", unique=True),
        # Cleanup queries by date
        Index("ix_snapshots_date_only", "snapshot_date"),
    ) 