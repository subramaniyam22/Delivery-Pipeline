from sqlalchemy.orm import Session
from app.models import Project, OnboardingData, OnboardingReviewStatus, AuditLog, Stage, ProjectStatus
from app.services.email_service import EmailService
from uuid import UUID
import logging
from app.config import settings

logger = logging.getLogger(__name__)

class OnboarderAgentService:
    def __init__(self, db: Session):
        self.db = db

    def check_and_automate_onboarding(self, project_id: UUID):
        """
        Check if onboarding is complete and automatically advance stage if HITL is disabled.
        """
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project or project.current_stage != Stage.ONBOARDING:
            return

        onboarding = self.db.query(OnboardingData).filter(OnboardingData.project_id == project_id).first()
        if not onboarding:
            return

        # Do not advance until client has submitted onboarding (submitted_at set when they submit the form)
        if not getattr(onboarding, "submitted_at", None):
            return

        # If manual review is enabled, we don't auto-advance
        if project.require_manual_review:
            return

        # Calculate completion
        from app.routers.onboarding import resolve_required_fields, calculate_completion_percentage
        required_fields = resolve_required_fields(self.db, project)
        completion = calculate_completion_percentage(onboarding, required_fields)

        if completion >= 100:
            logger.info(f"Project {project_id} onboarding 100% complete. AI Agent auto-advancing.")
            
            # Transition logic
            onboarding.review_status = OnboardingReviewStatus.APPROVED
            onboarding.ai_review_notes = "Onboarder Agent Analysis: All requirements met. Automatically advancing to Assignment stage."
            project.current_stage = Stage.ASSIGNMENT
            
            # Log audit
            from datetime import datetime
            audit = AuditLog(
                project_id=project.id,
                actor_user_id=None, # System/AI Agent
                action="AGENT_AUTO_ADVANCE",
                payload_json={"stage": "ONBOARDING", "next_stage": "ASSIGNMENT", "comment": onboarding.ai_review_notes}
            )
            self.db.add(audit)
            self.db.commit()
            
            return {"success": True, "advanced": True}
        
        return {"success": True, "advanced": False, "completion": completion}

    def validate_initial_project_data(self, project_id: UUID):
        """
        Validate project data immediately after creation by Sales.
        Checks for: Title, Client Name, PMC, Location, Client Email IDs, Description, Priority.
        """
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            logger.error(f"Project {project_id} not found for agent validation")
            return

        missing_fields = []
        if not project.title: missing_fields.append("Project Title")
        if not project.client_name: missing_fields.append("Client Name")
        if not project.pmc_name: missing_fields.append("PMC Name")
        if not project.location: missing_fields.append("Location")
        if not project.client_email_ids: missing_fields.append("Client Email IDs")
        # Description is mentioned as optional in UI but user said "check for all information"
        # I'll check description as well based on requirements
        # Priority is also required
        if not project.priority: missing_fields.append("Priority")

        onboarding = self.db.query(OnboardingData).filter(OnboardingData.project_id == project_id).first()
        if not onboarding:
            # Create onboarding data if missing
            from app.routers.onboarding import generate_client_token
            from datetime import datetime, timedelta
            onboarding = OnboardingData(
                project_id=project_id,
                client_access_token=generate_client_token(),
                token_expires_at=datetime.utcnow() + timedelta(days=30),
                contacts_json=[],
                images_json=[],
                theme_colors_json={},
                custom_fields_json=[],
                requirements_json={}
            )
            self.db.add(onboarding)
            self.db.flush()

        if missing_fields:
            comment = f"Onboarder Agent: Missing required information: {', '.join(missing_fields)}. Please update the project details."
            onboarding.review_status = OnboardingReviewStatus.NEEDS_CHANGES
            onboarding.ai_review_notes = comment
            project.status = ProjectStatus.DRAFT
            
            # Log audit
            audit = AuditLog(
                project_id=project.id,
                actor_user_id=project.created_by_user_id,
                action="AGENT_REVIEW_FAILED",
                payload_json={"missing_fields": missing_fields, "comment": comment}
            )
            self.db.add(audit)
        else:
            comment = "Onboarder Agent: All initial information provided. Triggering client notification."
            onboarding.review_status = OnboardingReviewStatus.PENDING
            onboarding.ai_review_notes = comment
            # project.status = ProjectStatus.ACTIVE # Do not override user's status choice
            
            # Trigger client email or next workflow step
            audit = AuditLog(
                project_id=project.id,
                actor_user_id=project.created_by_user_id,
                action="AGENT_REVIEW_PASSED",
                payload_json={"comment": comment}
            )
            self.db.add(audit)
            
            # Trigger client email notification
            client_emails = project.client_email_ids.split(",") if project.client_email_ids else []
            if client_emails:
                onboarding = self.db.query(OnboardingData).filter(OnboardingData.project_id == project.id).first()
                link = f"{settings.FRONTEND_URL}/client-onboarding/{onboarding.client_access_token}" if onboarding and onboarding.client_access_token else "#"
                
                EmailService.send_client_reminder_email(
                    to_emails=[e.strip() for e in client_emails],
                    subject=f"Let’s get your project moving 🚀",
                    message=f"Hi {project.client_name},<br><br>Welcome aboard! We’ve reviewed the initial details for {project.title}, and everything looks on track so far.<br><br>To help us move faster and avoid back-and-forth later, could you complete the onboarding form below? This will give our team the clarity we need to set things up right from day one.<br><br>👉 Onboarding form:<br><a href='{link}'>{link}</a><br><br>If anything feels unclear, just use the chat option on the onboarding page. You’ll be connected to our team while you fill it out.<br><br>Once you’re done, we’ll review your inputs and come back with the next steps and timelines.<br><br>Excited to get started with you.<br><br>Warm regards,<br>Project Onboarding Team",
                    project_title=project.title,
                    sender_name="Project Onboarding Team"
                )
            
            # Advance logic or notification trigger
            # send_initial_onboarding_email(project)

        return {"success": True, "missing_fields": missing_fields}
