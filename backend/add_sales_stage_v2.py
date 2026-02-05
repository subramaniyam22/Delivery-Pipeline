"""
Add SALES to the Stage enum in the database - Alternative approach
"""
from sqlalchemy import create_engine, text
from app.config import settings

def add_sales_stage_v2():
    engine = create_engine(settings.database_url_fixed)
    
    # Use raw connection with autocommit for ALTER TYPE
    with engine.connect() as conn:
        # Set autocommit mode
        conn.execution_options(isolation_level="AUTOCOMMIT")
        
        try:
            # First check if SALES exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_enum 
                    WHERE enumlabel = 'SALES' 
                    AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'stage')
                );
            """))
            exists = result.scalar()
            
            if exists:
                print("✅ SALES already exists in stage enum")
            else:
                # Try to add SALES - note: BEFORE clause might not work in all PostgreSQL versions
                # So we'll try without it first
                try:
                    conn.execute(text("ALTER TYPE stage ADD VALUE 'SALES'"))
                    print("✅ Successfully added SALES to stage enum (at end)")
                except Exception as e1:
                    print(f"Could not add at end: {e1}")
                    # If that fails, the enum might be in use, need to recreate
                    print("⚠️ The stage enum might be in use. You may need to manually add SALES.")
                    
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    add_sales_stage_v2()
