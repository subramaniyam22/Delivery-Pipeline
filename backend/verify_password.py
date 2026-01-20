
from app.db import SessionLocal
from app.models import User
from app.auth import verify_password, get_password_hash
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_mgr_password():
    db = SessionLocal()
    try:
        email = "subramaniyam@manager.com"
        user = db.query(User).filter(User.email == email).first()
        if user:
            logger.info(f"User found: {user.email}")
            logger.info(f"Stored Hash: {user.password_hash}")
            
            is_valid = verify_password("Admin@123", user.password_hash)
            logger.info(f"Verification result for 'Admin@123': {is_valid}")
            
            new_hash = get_password_hash("Admin@123")
            logger.info(f"New Hash for 'Admin@123': {new_hash}")
            
            is_valid_new = verify_password("Admin@123", new_hash)
            logger.info(f"Verification result for new hash: {is_valid_new}")
        else:
            logger.error(f"User {email} not found")
                
    except Exception as e:
        logger.error(f"Error during verification: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_mgr_password()
