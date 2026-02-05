from app.db import SessionLocal
from app.models import (
    Project, AuditLog, Defect, OnboardingData, ProjectTask, 
    BuilderWorkHistory, TestExecution, TestResult, DefectAssignment,
    CapacitySuggestion, CapacityAllocation, ProjectWorkload,
    StageOutput, Artifact, Task, ChatLog
)

# Try imports for others
try:
    from app.models import ClientReminder
except ImportError:
    ClientReminder = None

try:
    from app.models import TestScenario
except ImportError:
    TestScenario = None

db = SessionLocal()

def safe_delete(model, name):
    if not model:
        return
    try:
        # Check if table exists/has data first? No, delete is fine.
        # But if error occurs, transaction is aborted in Postgres.
        # We should use savepoints or just rollback and start fresh if we want individual deletes?
        # But we want ALL to be deleted in one go or cascade.
        # So catching exception and continuing is dangerous if transaction is aborted.
        # However, for this script, we want to find all dependencies.
        # Since we use one session, one error aborts all.
        deleted = db.query(model).delete()
        print(f"Deleted {deleted} {name} records")
    except Exception as e:
        print(f"Error deleting {name}: {e}")
        # If error invalidates transaction, we can't continue using db session.
        # So we should probably let it fail and fix the script.
        raise e 

try:
    print("Cleaning up database projects and dependencies...")
    
    # Order matters for Foreign Keys
    safe_delete(BuilderWorkHistory, "BuilderWorkHistory")
    safe_delete(DefectAssignment, "DefectAssignment")
    safe_delete(TestResult, "TestResult")
    safe_delete(TestExecution, "TestExecution")
    safe_delete(ClientReminder, "ClientReminder")
    safe_delete(TestScenario, "TestScenario")
    
    safe_delete(CapacitySuggestion, "CapacitySuggestion")
    safe_delete(CapacityAllocation, "CapacityAllocation")
    safe_delete(ProjectWorkload, "ProjectWorkload")
    
    safe_delete(Defect, "Defect")
    safe_delete(ProjectTask, "ProjectTask")
    safe_delete(Task, "Task")
    safe_delete(StageOutput, "StageOutput")
    safe_delete(Artifact, "Artifact")
    safe_delete(ChatLog, "ChatLog") # Added
    safe_delete(OnboardingData, "OnboardingData")
    
    safe_delete(AuditLog, "AuditLog")
    
    # Finally Projects
    safe_delete(Project, "Project")
    
    db.commit()
    print("Database cleanup complete.")
    
except Exception as e:
    db.rollback()
    print(f"Cleanup failed (rolled back): {e}")
finally:
    db.close()
