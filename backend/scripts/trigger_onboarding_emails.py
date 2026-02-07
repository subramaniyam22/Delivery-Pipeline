from app.db import SessionLocal
from app.models import Project, Stage
from app.services.onboarding_agent_service import OnboarderAgentService


def main() -> None:
    db = SessionLocal()
    sent = 0
    skipped = 0
    try:
        projects = (
            db.query(Project)
            .filter(Project.current_stage == Stage.ONBOARDING)
            .all()
        )
        agent = OnboarderAgentService(db)
        for project in projects:
            if not project.client_email_ids:
                skipped += 1
                print(f"SKIP: {project.title} (no client_email_ids)")
                continue
            agent.validate_initial_project_data(project.id)
            sent += 1
            print(f"TRIGGERED: {project.title}")
    finally:
        db.close()

    print(f"\nDone. Triggered: {sent}, Skipped: {skipped}")


if __name__ == "__main__":
    main()
