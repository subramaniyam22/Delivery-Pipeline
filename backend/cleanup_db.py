from app.db import SessionLocal
from app.models import Project, AuditLog, Task, Defect

db = SessionLocal()

try:
    print("Cleaning up database projects and dependencies...")
    
    # Delete Defects
    deleted = db.query(Defect).delete()
    print(f"Deleted {deleted} defects")
    
    # Delete Tasks
    deleted = db.query(Task).delete()
    print(f"Deleted {deleted} tasks")

    # Delete AuditLogs linked to projects or all
    deleted = db.query(AuditLog).delete()
    print(f"Deleted {deleted} audit logs")
    
    # Delete Projects
    deleted = db.query(Project).delete()
    print(f"Deleted {deleted} projects")
    
    db.commit()
    print("Database cleanup complete.")
    
except Exception as e:
    db.rollback()
    print(f"Error occurred: {e}")
finally:
    db.close()
