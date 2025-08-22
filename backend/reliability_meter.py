"""
Journal Reliability Meter - TA-Aware Implementation
Extends the existing JournalImpactFactorService with multi-dimensional scoring.

Based on the CS-inspired multi-dimensional reliability scoring spec:
- Authority (TA-specific impact/citations)
- Relevance (semantic alignment to TA)  
- Freshness (recent activity in TA)
- Guideline (clinical presence)
- Rigor (integrity proxies)

KEY INNOVATION: JCO beats Nature in oncology contexts!
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from models import Journal, Article
import time
import re

class UseCase(Enum):
    CLINICAL = "clinical"      # For pivotal/label-proximal decisions
    EXPLORATORY = "exploratory"  # For mechanistic/scouting research

class ReliabilityBand(Enum):
    HIGH = "high"              # 0.80-1.00: Highest confidence
    MODERATE = "moderate"      # 0.60-0.79: Good confidence  
    EXPLORATORY = "exploratory" # 0.40-0.59: Moderate confidence
    LOW = "low"               # 0.00-0.39: Lower confidence

@dataclass
class ReliabilityComponents:
    """The 5 dimensions of journal reliability"""
    authority_ta: float      # TA-specific citation authority 
    relevance_ta: float      # Semantic alignment to TA
    freshness_ta: float      # Recent publication activity in TA
    guideline: float         # Presence in clinical guidelines
    rigor: float            # Editorial integrity proxies

@dataclass
class ReliabilityScore:
    """Complete reliability assessment for a journal in a TA context"""
    journal_name: str
    therapeutic_area: str
    use_case: UseCase
    score: float             # 0.0-1.0 composite score
    band: ReliabilityBand    # Human-readable reliability level
    components: ReliabilityComponents
    uncertainty: str         # "low", "medium", "high"
    reasons: List[str]       # Explainable AI reasons
    impact_factor: float     # Traditional IF for reference
    updated_at: str

class ReliabilityMeter:
    """
    TA-aware journal reliability assessment system
    
    Solves the "Journal of Clinical Oncology vs Nature" problem by considering:
    1. Therapeutic area context
    2. Use case (clinical vs exploratory)  
    3. Multiple reliability dimensions
    4. Uncertainty quantification
    """
    
    def __init__(self):
        # Weight profiles optimized for different use cases
        self.weights = {
            UseCase.CLINICAL: {
                'alpha': 0.45,   # Authority: High weight for clinical decisions
                'beta': 0.20,    # Relevance: Moderate weight
                'gamma': 0.05,   # Freshness: Low weight (established knowledge matters)
                'delta': 0.25,   # Guideline: High weight for clinical use
                'epsilon': 0.05  # Rigor: Baseline requirement
            },
            UseCase.EXPLORATORY: {
                'alpha': 0.20,   # Authority: Lower weight (new ideas welcome)
                'beta': 0.40,    # Relevance: High weight (specialization matters)
                'gamma': 0.25,   # Freshness: High weight (latest research)
                'delta': 0.05,   # Guideline: Low weight (not yet in guidelines)
                'epsilon': 0.10  # Rigor: Moderate weight
            }
        }
        
        # Trusted publishers for cold-start boost
        self.trusted_entities = {
            'nature', 'science', 'cell', 'lancet', 'bmj', 'jama',
            'american society of clinical oncology', 'asco',
            'american association for cancer research', 'aacr',
            'european society for medical oncology', 'esmo',
            'american college of cardiology', 'american heart association'
        }
    
    def assess_reliability(self, journal_name: str, therapeutic_area: str, 
                         use_case: UseCase, db: Session, 
                         impact_factor: float = None) -> ReliabilityScore:
        """
        Main entry point: Assess journal reliability for TA and use case
        
        Example results:
        - JCO + Oncology + Clinical → High reliability (0.85+)
        - Nature + Oncology + Clinical → Moderate reliability (0.70)
        - JCO + Cardiology + Clinical → Exploratory reliability (0.50)
        """
        
        # Get TA-specific articles for evidence
        ta_articles = self._get_ta_articles(journal_name, therapeutic_area, db)
        
        # Compute 5-dimensional components
        components = self._compute_reliability_components(
            journal_name, therapeutic_area, ta_articles, db
        )
        
        # Apply use-case specific weights
        weights = self.weights[use_case]
        composite_score = (
            weights['alpha'] * components.authority_ta +
            weights['beta'] * components.relevance_ta +
            weights['gamma'] * components.freshness_ta +
            weights['delta'] * components.guideline +
            weights['epsilon'] * components.rigor
        )
        
        # Determine reliability band
        band = self._score_to_band(composite_score)
        
        # Quantify uncertainty
        uncertainty = self._assess_uncertainty(ta_articles, components)
        
        # Generate explainable reasons
        reasons = self._generate_explanations(components, band, uncertainty, use_case)
        
        return ReliabilityScore(
            journal_name=journal_name,
            therapeutic_area=therapeutic_area,
            use_case=use_case,
            score=round(composite_score, 3),
            band=band,
            components=components,
            uncertainty=uncertainty,
            reasons=reasons,
            impact_factor=impact_factor or 1.0,
            updated_at=time.strftime("%Y-%m-%d %H:%M:%S")
        )
    
    def _compute_reliability_components(self, journal_name: str, ta: str, 
                                      ta_articles: List[Article], 
                                      db: Session) -> ReliabilityComponents:
        """Compute the 5 reliability dimensions"""
        
        return ReliabilityComponents(
            authority_ta=self._compute_authority(journal_name, ta, ta_articles),
            relevance_ta=self._compute_relevance(journal_name, ta, ta_articles),
            freshness_ta=self._compute_freshness(ta_articles),
            guideline=self._compute_guideline_presence(journal_name, ta),
            rigor=self._compute_rigor(journal_name)
        )
    
    def _compute_authority(self, journal_name: str, ta: str, ta_articles: List[Article]) -> float:
        """
        TA-specific authority using intelligent pattern matching
        
        Key insight: JCO has HIGH authority in oncology, lower in cardiology
        """
        # Base authority from journal reputation
        base_authority = self._get_journal_base_authority(journal_name)
        
        # TA specialization multiplier (this is the key innovation!)
        ta_multiplier = self._get_ta_specialization_score(journal_name, ta)
        
        # Evidence boost from actual TA articles
        evidence_boost = min(0.3, len(ta_articles) / 50.0)
        
        # Cold-start boost for trusted entities
        trust_boost = 0.08 if self._is_trusted_publisher(journal_name) else 0.0
        
        # Combine factors (ensuring we don't exceed 1.0)
        authority = min(1.0, base_authority * ta_multiplier + evidence_boost + trust_boost)
        
        return authority
    
    def _get_journal_base_authority(self, journal_name: str) -> float:
        """Base authority independent of TA specialization"""
        name = journal_name.lower()
        
        # Tier 1: Global premier journals
        if any(term in name for term in ['nature medicine', 'science translational']):
            return 0.95
        if any(term in name for term in ['nature', 'science', 'cell']):
            return 0.85
        
        # Tier 2: Top medical journals
        if any(term in name for term in ['new england', 'nejm', 'lancet', 'jama']):
            return 0.90
        
        # Tier 3: Specialty leaders
        if any(term in name for term in ['circulation', 'blood', 'cancer cell', 'immunity']):
            return 0.80
        
        # Tier 4: Clinical journals
        if 'clinical' in name or 'american journal' in name:
            return 0.70
        
        return 0.50  # Default
    
    def _get_ta_specialization_score(self, journal_name: str, ta: str) -> float:
        """
        CRITICAL FUNCTION: How specialized is this journal for the TA?
        
        This is what makes JCO rank higher than Nature for oncology!
        """
        name = journal_name.lower()
        ta_lower = ta.lower()
        
        # TA-specific keyword mapping
        ta_specialization = {
            'oncology': ['cancer', 'oncology', 'tumor', 'carcinoma', 'malignancy'],
            'cardiovascular': ['cardiology', 'cardiovascular', 'heart', 'cardiac', 'circulation'],
            'neurology': ['neurology', 'neurological', 'brain', 'neuro', 'cognitive'],
            'immunology': ['immunology', 'immune', 'allergy', 'autoimmune'],
            'endocrinology': ['diabetes', 'endocrinology', 'hormone', 'metabolism', 'endocrine'],
            'respiratory': ['respiratory', 'pulmonary', 'lung', 'asthma'],
            'gastroenterology': ['gastroenterology', 'digestive', 'liver', 'hepatology'],
            'dermatology': ['dermatology', 'skin', 'dermatological'],
            'rheumatology': ['rheumatology', 'arthritis', 'rheumatic'],
            'infectious diseases': ['infectious', 'microbiology', 'virology', 'antimicrobial']
        }
        
        # Strong boost for direct TA specialization
        if ta_lower in ta_specialization:
            keywords = ta_specialization[ta_lower]
            if any(keyword in name for keyword in keywords):
                return 1.4  # 40% boost for specialization!
        
        # Penalty for broad journals when looking at specific TAs
        broad_indicators = ['general', 'international', 'world', 'global', 'medicine']
        if any(indicator in name for indicator in broad_indicators):
            if ta_lower != 'general medicine':
                return 0.7  # 30% penalty for being too broad
        
        return 1.0  # Neutral multiplier
    
    def _compute_relevance(self, journal_name: str, ta: str, ta_articles: List[Article]) -> float:
        """Semantic relevance to therapeutic area"""
        
        if not ta_articles:
            # Fallback to name-based estimation
            return self._estimate_relevance_from_name(journal_name, ta)
        
        # Calculate proportion of journal's output that's TA-relevant
        estimated_total_articles = max(len(ta_articles) * 3, 30)  # Conservative estimate
        ta_proportion = len(ta_articles) / estimated_total_articles
        
        # Content relevance from abstracts
        content_score = self._analyze_abstract_relevance(ta_articles, ta)
        
        # Combine proportion and content quality
        relevance = min(1.0, ta_proportion * 1.5 + content_score * 0.5)
        
        return relevance
    
    def _compute_freshness(self, ta_articles: List[Article]) -> float:
        """Recent publication activity in the TA"""
        if not ta_articles:
            return 0.1
        
        current_year = 2024
        recent_count = 0
        
        for article in ta_articles:
            try:
                if article.publication_date:
                    pub_year = int(article.publication_date[:4])
                    if current_year - pub_year <= 2:  # Last 2 years
                        recent_count += 1
            except (ValueError, TypeError):
                continue
        
        # Normalize: 15+ recent articles = maximum freshness
        freshness = min(1.0, recent_count / 15.0)
        return freshness
    
    def _compute_guideline_presence(self, journal_name: str, ta: str) -> float:
        """Estimate presence in clinical guidelines"""
        name = journal_name.lower()
        
        # High guideline presence journals
        clinical_authorities = [
            'new england', 'nejm', 'lancet', 'jama', 'bmj',
            'journal of clinical oncology', 'circulation',
            'diabetes care', 'chest'
        ]
        
        if any(auth in name for auth in clinical_authorities):
            return 0.9
        
        # Specialty clinical journals
        if 'clinical' in name:
            return 0.7
        
        # Medical society journals
        if any(society in name for society in ['american', 'european', 'society']):
            return 0.6
        
        # Basic science journals (lower guideline presence)
        if any(basic in name for basic in ['nature', 'science', 'cell']) and 'clinical' not in name:
            return 0.3
        
        return 0.4  # Default
    
    def _compute_rigor(self, journal_name: str) -> float:
        """Editorial rigor and integrity proxies"""
        name = journal_name.lower()
        
        # Premier journals with highest standards
        if any(premier in name for premier in ['nature', 'science', 'cell', 'new england', 'lancet']):
            return 0.95
        
        # Established medical journals
        if any(med in name for med in ['jama', 'bmj', 'circulation', 'blood']):
            return 0.85
        
        # Clinical and specialty journals
        if 'clinical' in name or 'american journal' in name:
            return 0.75
        
        return 0.65  # Default
    
    def _get_ta_articles(self, journal_name: str, ta: str, db: Session) -> List[Article]:
        """Retrieve articles from this journal in the therapeutic area"""
        try:
            # Query for articles matching journal and TA
            articles = db.query(Article).filter(
                Article.journal.ilike(f"%{journal_name}%"),
                Article.therapeutic_area.ilike(f"%{ta}%")
            ).limit(100).all()  # Increased limit for better evidence
            
            return articles
        except Exception as e:
            print(f"Error retrieving TA articles: {e}")
            return []
    
    def _assess_uncertainty(self, ta_articles: List[Article], 
                          components: ReliabilityComponents) -> str:
        """Quantify uncertainty in the reliability assessment"""
        evidence_count = len(ta_articles)
        
        # Evidence-based uncertainty
        if evidence_count < 3:
            return "high"
        elif evidence_count < 10:
            return "medium"
        else:
            return "low"
    
    def _score_to_band(self, score: float) -> ReliabilityBand:
        """Convert numerical score to reliability band"""
        if score >= 0.80:
            return ReliabilityBand.HIGH
        elif score >= 0.60:
            return ReliabilityBand.MODERATE
        elif score >= 0.40:
            return ReliabilityBand.EXPLORATORY
        else:
            return ReliabilityBand.LOW
    
    def _generate_explanations(self, components: ReliabilityComponents, 
                             band: ReliabilityBand, uncertainty: str,
                             use_case: UseCase) -> List[str]:
        """Generate human-readable explanations for the score"""
        reasons = []
        
        # Band-level summary
        if band == ReliabilityBand.HIGH:
            reasons.append(f"Highly reliable source for {use_case.value} use")
        elif band == ReliabilityBand.MODERATE:
            reasons.append(f"Good reliability for {use_case.value} use")
        elif band == ReliabilityBand.EXPLORATORY:
            reasons.append(f"Moderate reliability - suitable for {use_case.value} research")
        else:
            reasons.append(f"Lower reliability - consider supplementary sources")
        
        # Component-specific reasons (top 2-3)
        if components.authority_ta >= 0.8:
            reasons.append("High authority in this therapeutic area")
        elif components.authority_ta >= 0.6:
            reasons.append("Moderate authority in this therapeutic area")
        
        if components.relevance_ta >= 0.8:
            reasons.append("Highly specialized for this therapeutic area")
        elif components.relevance_ta >= 0.6:
            reasons.append("Good specialization for this therapeutic area")
        
        if components.freshness_ta >= 0.7:
            reasons.append("Active recent publication in this area")
        
        if components.guideline >= 0.8:
            reasons.append("Frequently cited in clinical guidelines")
        
        # Uncertainty warning
        if uncertainty == "high":
            reasons.append("Limited evidence available - interpret cautiously")
        
        return reasons[:4]  # Limit to top 4 most important reasons
    
    # Helper methods
    def _is_trusted_publisher(self, journal_name: str) -> bool:
        """Check if journal is from a trusted publisher/society"""
        name = journal_name.lower()
        return any(trusted in name for trusted in self.trusted_entities)
    
    def _estimate_relevance_from_name(self, journal_name: str, ta: str) -> float:
        """Estimate relevance when no articles are available"""
        specialization = self._get_ta_specialization_score(journal_name, ta)
        
        if specialization > 1.2:
            return 0.8  # High relevance for highly specialized journals
        elif specialization > 1.0:
            return 0.6  # Good relevance for somewhat specialized
        elif specialization < 1.0:
            return 0.3  # Lower relevance for broad journals
        
        return 0.5  # Neutral
    
    def _analyze_abstract_relevance(self, articles: List[Article], ta: str) -> float:
        """Analyze how relevant article abstracts are to the TA"""
        if not articles:
            return 0.5
        
        # TA-specific keyword sets for content analysis
        ta_keywords = {
            'oncology': ['cancer', 'tumor', 'malignant', 'chemotherapy', 'radiation', 'metastasis', 'oncology'],
            'cardiovascular': ['heart', 'cardiac', 'coronary', 'hypertension', 'stroke', 'vascular', 'cardiovascular'],
            'neurology': ['brain', 'neurological', 'cognitive', 'seizure', 'dementia', 'parkinson', 'alzheimer'],
            'immunology': ['immune', 'immunology', 'antibody', 'cytokine', 'inflammation', 'autoimmune'],
            'endocrinology': ['diabetes', 'insulin', 'hormone', 'endocrine', 'metabolism', 'glucose']
        }
        
        if ta.lower() not in ta_keywords:
            return 0.5  # Default for unmapped TAs
        
        keywords = ta_keywords[ta.lower()]
        relevance_scores = []
        
        # Analyze sample of abstracts
        for article in articles[:20]:  # Sample up to 20 articles
            if article.abstract:
                text = f"{article.title} {article.abstract}".lower()
                keyword_matches = sum(1 for keyword in keywords if keyword in text)
                relevance_scores.append(keyword_matches / len(keywords))
        
        return sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.5
