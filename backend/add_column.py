from sqlalchemy import text
from app.db import SessionLocal

def add_column():
    db = SessionLocal()
    try:
        # Check if column exists
        check_query = text("SELECT column_name FROM information_schema.columns WHERE table_name='projects' AND column_name='project_type'")
        result = db.execute(check_query).fetchone()
        
        if not result:
            print("Adding project_type column...")
            db.execute(text("ALTER TABLE projects ADD COLUMN project_type VARCHAR(50)"))
            db.commit()
            print("Column added successfully.")
        else:
            print("Column already exists.")
            
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_column()
