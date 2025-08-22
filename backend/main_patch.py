# Patch for main.py to integrate reliability meter

# Add these imports at the top after existing imports
from reliability_meter import ReliabilityMeter, UseCase as ReliabilityUseCase
from schemas import ReliabilityRequest, ReliabilityResponse

# Add this to the search-pubmed endpoint (around line 155)
reliability_meter_patch = '''
@app.post("/articles/search-pubmed")
async def search_pubmed_only(request: SearchRequest, 
                           reliability_req: ReliabilityRequest = None,
                           db: Session = Depends(get_db)):
    """Search PubMed with caching and TA-aware reliability scoring"""
    try:
        # Get articles from PubMed (cached)
        articles = cached_pubmed_search(request.therapeutic_area, request.days_back)
        
        # Initialize reliability meter
        reliability_meter = ReliabilityMeter()
        
        # Determine use case
        use_case = ReliabilityUseCase.CLINICAL
        if reliability_req and reliability_req.use_case == "exploratory":
            use_case = ReliabilityUseCase.EXPLORATORY
        
        # Sort by impact factor using database service AND add reliability scores
        sorted_articles = sort_by_impact_factor(articles, db)
        
        # Convert to response format with reliability data
        response_articles = []
        for article_data in sorted_articles:
            # Get reliability assessment for this journal in this TA
            try:
                reliability_score = reliability_meter.assess_reliability(
                    journal_name=article_data['journal'],
                    therapeutic_area=request.therapeutic_area,
                    use_case=use_case,
                    db=db,
                    impact_factor=article_data.get('impact_factor', 1.0)
                )
                
                response_articles.append({
                    "id": None,
                    "pubmed_id": article_data['pubmed_id'],
                    "title": article_data['title'],
                    "authors": article_data['authors'],
                    "abstract": article_data['abstract'],
                    "publication_date": article_data['publication_date'],
                    "journal": article_data['journal'],
                    "therapeutic_area": article_data['therapeutic_area'],
                    "link": article_data['link'],
                    "created_at": None,
                    "impact_factor": article_data.get('impact_factor', 1.0),
                    "reliability_tier": article_data.get('reliability_tier', 'Unknown'),
                    # NEW: Reliability meter data
                    "reliability_score": reliability_score.score,
                    "reliability_band": reliability_score.band.value,
                    "reliability_reasons": reliability_score.reasons,
                    "uncertainty": reliability_score.uncertainty,
                    "use_case": use_case.value
                })
                
            except Exception as e:
                print(f"Error assessing reliability for {article_data['journal']}: {e}")
                # Fallback to basic article data
                response_articles.append({
                    "id": None,
                    "pubmed_id": article_data['pubmed_id'],
                    "title": article_data['title'],
                    "authors": article_data['authors'],
                    "abstract": article_data['abstract'],
                    "publication_date": article_data['publication_date'],
                    "journal": article_data['journal'],
                    "therapeutic_area": article_data['therapeutic_area'],
                    "link": article_data['link'],
                    "created_at": None,
                    "impact_factor": article_data.get('impact_factor', 1.0),
                    "reliability_tier": article_data.get('reliability_tier', 'Unknown'),
                    # Default reliability data
                    "reliability_score": None,
                    "reliability_band": None,
                    "reliability_reasons": [],
                    "uncertainty": "high",
                    "use_case": use_case.value
                })
        
        # Sort by reliability score (highest first), then by impact factor
        response_articles.sort(
            key=lambda x: (x.get('reliability_score', 0), x.get('impact_factor', 0)), 
            reverse=True
        )
        
        return response_articles
        
    except Exception as e:
        print(f"Error in cached search: {e}")
        return []
'''

# Add new endpoint for reliability assessment
reliability_endpoint = '''
@app.post("/articles/reliability", response_model=ReliabilityResponse)
async def assess_journal_reliability(
    journal_name: str,
    therapeutic_area: str,
    request: ReliabilityRequest,
    db: Session = Depends(get_db)
):
    """Assess reliability of a specific journal for a therapeutic area"""
    try:
        from journal_service import JournalImpactFactorService
        
        # Get traditional impact factor
        journal_service = JournalImpactFactorService()
        impact_factor, _ = journal_service.get_impact_factor(journal_name, db)
        
        # Get reliability assessment
        reliability_meter = ReliabilityMeter()
        use_case = ReliabilityUseCase.CLINICAL if request.use_case == "clinical" else ReliabilityUseCase.EXPLORATORY
        
        reliability_score = reliability_meter.assess_reliability(
            journal_name=journal_name,
            therapeutic_area=therapeutic_area,
            use_case=use_case,
            db=db,
            impact_factor=impact_factor
        )
        
        return ReliabilityResponse(
            journal_name=reliability_score.journal_name,
            therapeutic_area=reliability_score.therapeutic_area,
            use_case=reliability_score.use_case.value,
            score=reliability_score.score,
            band=reliability_score.band.value,
            components=reliability_score.components,
            uncertainty=reliability_score.uncertainty,
            reasons=reliability_score.reasons,
            impact_factor=reliability_score.impact_factor,
            updated_at=reliability_score.updated_at
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error assessing reliability: {str(e)}")
'''

print("Patches ready to apply to main.py")
