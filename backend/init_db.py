from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import Base, TherapeuticArea
from pubmed_service import PubMedService

def init_database():
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create a database session
    db = SessionLocal()
    
    try:
        # Check if therapeutic areas already exist
        existing_areas = db.query(TherapeuticArea).count()
        if existing_areas == 0:
            # Add hierarchical therapeutic areas
            oncology = TherapeuticArea(name="Oncology", description="Cancer research and treatment")
            db.add(oncology)
            db.flush()  # get oncology.id

            breast_cancer = TherapeuticArea(name="Breast Cancer", description="Breast cancer research", parent_id=oncology.id)
            db.add(breast_cancer)
            db.flush()

            tn_breast_cancer = TherapeuticArea(name="Triple-Negative Breast Cancer", description="Triple-negative breast cancer research", parent_id=breast_cancer.id)
            db.add(tn_breast_cancer)

            # Add other top-level TAs (no children for now)
            db.add_all([
                TherapeuticArea(name="Cardiovascular", description="Heart and vascular diseases"),
                TherapeuticArea(name="Neurology", description="Nervous system disorders"),
                TherapeuticArea(name="Immunology", description="Immune system and autoimmune diseases"),
                TherapeuticArea(name="Rare Diseases", description="Orphan diseases and conditions"),
                TherapeuticArea(name="Infectious Diseases", description="Viral, bacterial, and parasitic infections"),
                TherapeuticArea(name="Endocrinology", description="Hormone and metabolic disorders"),
                TherapeuticArea(name="Dermatology", description="Skin conditions and diseases"),
                TherapeuticArea(name="Psychiatry", description="Mental health and behavioral disorders"),
                TherapeuticArea(name="Respiratory", description="Lung and respiratory conditions")
            ])
            db.commit()
            print("✅ Database initialized with hierarchical therapeutic areas")
        else:
            print("✅ Database already contains therapeutic areas")
            
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_database() 