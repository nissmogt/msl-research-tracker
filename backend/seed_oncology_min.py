#!/usr/bin/env python3
"""
Minimal oncology seed for testing "JCO > Nature" requirement
Creates just enough data to validate the reliability meter scoring
"""

from sqlalchemy.orm import Session
from models import Journal, Article
from datetime import date, timedelta
from database import SessionLocal

def seed_oncology_data():
    """Create minimal oncology seed data for JCO vs Nature testing"""
    
    with SessionLocal() as db:
        try:
            print("🌱 Seeding minimal oncology data for JCO vs Nature test...")
            
            # Check if journals already exist
            existing_jco = db.query(Journal).filter(Journal.name == "Journal of Clinical Oncology").first()
            existing_nature = db.query(Journal).filter(Journal.name == "Nature").first()
            
            if not existing_jco:
                jco = Journal(
                    name="Journal of Clinical Oncology",
                    issn="0732-183X",
                    impact_factor=32.976,
                    impact_factor_year=2023,
                    category="Oncology",
                    publisher="American Society of Clinical Oncology"
                )
                db.add(jco)
                print("  ➕ Created Journal of Clinical Oncology")
            else:
                jco = existing_jco
                print("  ✅ Journal of Clinical Oncology already exists")
            
            if not existing_nature:
                nature = Journal(
                    name="Nature",
                    issn="0028-0836", 
                    impact_factor=64.8,
                    impact_factor_year=2023,
                    category="General Science",
                    publisher="Nature Publishing Group"
                )
                db.add(nature)
                print("  ➕ Created Nature")
            else:
                nature = existing_nature
                print("  ✅ Nature already exists")
            
            db.flush()  # Get IDs
            
            # Remove existing test articles to avoid duplicates
            db.query(Article).filter(
                Article.title.like("JCO oncology%")
            ).delete()
            db.query(Article).filter(
                Article.title.like("Nature oncology%")
            ).delete()
            
            # Create JCO articles (more oncology-focused, recent)
            today = date.today()
            
            jco_articles = [
                {
                    "title": "JCO oncology 1: Pembrolizumab in Advanced NSCLC",
                    "abstract": "This study evaluates pembrolizumab efficacy in advanced non-small cell lung cancer patients with PD-L1 expression. Results show significant improvement in overall survival with pembrolizumab compared to chemotherapy in oncology treatment protocols.",
                    "publication_date": str(today - timedelta(days=30)),
                },
                {
                    "title": "JCO oncology 2: CAR-T Cell Therapy for B-cell Lymphoma", 
                    "abstract": "CAR-T cell therapy demonstrates remarkable efficacy in relapsed B-cell lymphoma. This oncology breakthrough provides new treatment options for patients with resistant tumors and represents a major advance in cancer immunotherapy.",
                    "publication_date": str(today - timedelta(days=60)),
                },
                {
                    "title": "JCO oncology 3: Checkpoint Inhibitors in Melanoma",
                    "abstract": "Long-term survival data for checkpoint inhibitors in metastatic melanoma shows sustained responses. This comprehensive oncology analysis demonstrates the clinical utility of immunotherapy in cancer treatment protocols.",
                    "publication_date": str(today - timedelta(days=90)),
                },
                {
                    "title": "JCO oncology 4: Precision Medicine in Breast Cancer",
                    "abstract": "Genomic profiling guides precision oncology treatment selection in breast cancer patients. This study validates the clinical utility of tumor sequencing for personalized cancer therapy decisions.",
                    "publication_date": str(today - timedelta(days=120)),
                },
                {
                    "title": "JCO oncology 5: Liquid Biopsy in Lung Cancer",
                    "abstract": "Circulating tumor DNA analysis enables early detection of oncology treatment resistance. This liquid biopsy approach revolutionizes cancer monitoring and therapy optimization in clinical practice.",
                    "publication_date": str(today - timedelta(days=150)),
                },
                {
                    "title": "JCO oncology 6: Immunotherapy Combination Strategies",
                    "abstract": "Combination immunotherapy approaches show synergistic effects in solid tumors. This oncology research provides evidence for rational combination strategies in cancer treatment protocols.",
                    "publication_date": str(today - timedelta(days=180)),
                },
                {
                    "title": "JCO oncology 7: Pediatric Oncology Clinical Trials",
                    "abstract": "Phase II trial results in pediatric sarcoma demonstrate safety and efficacy of targeted therapy. This pediatric oncology study establishes new treatment standards for childhood cancer.",
                    "publication_date": str(today - timedelta(days=210)),
                },
                {
                    "title": "JCO oncology 8: Radiation Therapy Optimization",
                    "abstract": "Advanced radiation therapy techniques improve outcomes in prostate cancer. This oncology study demonstrates superior tumor control with reduced toxicity in cancer treatment.",
                    "publication_date": str(today - timedelta(days=240)),
                }
            ]
            
            for i, article_data in enumerate(jco_articles):
                article = Article(
                    pubmed_id=f"jco_test_{i+1}",
                    journal="Journal of Clinical Oncology",
                    therapeutic_area="oncology",
                    authors="Test Author et al.",
                    **article_data
                )
                db.add(article)
            
            print(f"  ➕ Created {len(jco_articles)} JCO oncology articles")
            
            # Create Nature articles (fewer explicitly oncology-tagged, more basic science)
            nature_articles = [
                {
                    "title": "Nature oncology 1: Cancer Cell Metabolism Pathways",
                    "abstract": "Basic science investigation of metabolic reprogramming in cancer cells reveals novel therapeutic targets. This fundamental oncology research elucidates mechanisms of tumor cell survival and growth.",
                    "publication_date": str(today - timedelta(days=365)),
                },
                {
                    "title": "Nature oncology 2: Tumor Microenvironment Dynamics", 
                    "abstract": "Single-cell analysis reveals complex interactions within the tumor microenvironment. This basic oncology research provides insights into cancer progression and immune evasion mechanisms.",
                    "publication_date": str(today - timedelta(days=400)),
                },
                {
                    "title": "Nature oncology 3: Epigenetic Regulation in Cancer",
                    "abstract": "Genome-wide epigenetic profiling identifies novel oncology targets for therapeutic intervention. This fundamental cancer research advances our understanding of tumor biology and development.",
                    "publication_date": str(today - timedelta(days=450)),
                }
            ]
            
            for i, article_data in enumerate(nature_articles):
                article = Article(
                    pubmed_id=f"nature_test_{i+1}",
                    journal="Nature",
                    therapeutic_area="oncology",
                    authors="Nature Author et al.",
                    **article_data
                )
                db.add(article)
            
            print(f"  ➕ Created {len(nature_articles)} Nature oncology articles")
            
            db.commit()
            
            print("✅ Oncology seed data created successfully!")
            print("\n📊 Data Summary:")
            print(f"   • JCO: {len(jco_articles)} recent oncology articles (clinical focus)")
            print(f"   • Nature: {len(nature_articles)} older oncology articles (basic science focus)")
            print("\n🎯 Expected Result:")
            print("   • JCO should score higher than Nature for oncology + clinical use case")
            print("   • JCO has more recent articles, higher specialization, stronger clinical focus")
            print("\n📝 Next Steps:")
            print("   1. Run: python worker_reliability.py --ta oncology --force")
            print("   2. Test: POST /reliability/top with oncology + clinical")
            print("   3. Verify: JCO score > Nature score")
            
        except Exception as e:
            db.rollback()
            print(f"❌ Error seeding data: {e}")
            raise

if __name__ == "__main__":
    seed_oncology_data()
