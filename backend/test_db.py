"""
Quick diagnostic script to test database and API performance.
"""
import time
from app.db import SessionLocal
from app.models import Project, User
from sqlalchemy.orm import joinedload

def test_database():
    print("Testing database connection...")
    db = SessionLocal()
    
    try:
        # Test simple query
        start = time.time()
        count = db.query(Project).count()
        elapsed = time.time() - start
        print(f"✓ Simple count query: {count} projects in {elapsed:.2f}s")
        
        # Test query with joinedloads (like the API)
        start = time.time()
        projects = db.query(Project).options(
            joinedload(Project.creator),
            joinedload(Project.sales_rep),
            joinedload(Project.manager_chk),
            joinedload(Project.consultant),
            joinedload(Project.pc),
            joinedload(Project.builder),
            joinedload(Project.tester),
            joinedload(Project.onboarding_data)
        ).limit(50).all()
        elapsed = time.time() - start
        print(f"✓ Complex query with joins: {len(projects)} projects in {elapsed:.2f}s")
        
        if elapsed > 5:
            print("⚠️  WARNING: Query is slow! Consider:")
            print("   - Adding database indexes")
            print("   - Reducing number of joinedloads")
            print("   - Using lazy loading for some relationships")
        
        print("\n✓ Database is working!")
        
    except Exception as e:
        print(f"✗ Database error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_database()
