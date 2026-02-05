"""
Add SALES to the Stage enum in the database
"""
from sqlalchemy import create_engine, text
from app.config import settings

def add_sales_stage():
    engine = create_engine(settings.database_url_fixed)
    
    # Use raw connection with autocommit for ALTER TYPE
    with engine.connect() as conn:
        # Set autocommit mode
        conn.execution_options(isolation_level="AUTOCOMMIT")
        
        try:
            # Add SALES to stage enum if it doesn't exist
            conn.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_enum 
                        WHERE enumlabel = 'SALES' 
                        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'stage')
                    ) THEN
                        ALTER TYPE stage ADD VALUE 'SALES' BEFORE 'ONBOARDING';
                    END IF;
                END$$;
            """))
            print("✅ Successfully added SALES to stage enum")
        except Exception as e:
            print(f"❌ Error: {e}")
            print("Note: If SALES already exists, this is expected.")

if __name__ == "__main__":
    add_sales_stage()
