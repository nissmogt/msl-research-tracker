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
            # Add therapeutic areas
            therapeutic_areas = [
                {"name": "Oncology", "description": "Cancer research and treatment"},
                {"name": "Cardiovascular", "description": "Heart and vascular diseases"},
                {"name": "Neurology", "description": "Nervous system disorders"},
                {"name": "Immunology", "description": "Immune system and autoimmune diseases"},
                {"name": "Rare Diseases", "description": "Orphan diseases and conditions"},
                {"name": "Infectious Diseases", "description": "Viral, bacterial, and parasitic infections"},
                {"name": "Endocrinology", "description": "Hormone and metabolic disorders"},
                {"name": "Dermatology", "description": "Skin conditions and diseases"},
                {"name": "Psychiatry", "description": "Mental health and behavioral disorders"},
                {"name": "Respiratory", "description": "Lung and respiratory conditions"}
            ]
            
            for area_data in therapeutic_areas:
                area = TherapeuticArea(**area_data)
                db.add(area)
            
            db.commit()
            print("✅ Database initialized with therapeutic areas")
        else:
            print("✅ Database already contains therapeutic areas")
            
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_database() 