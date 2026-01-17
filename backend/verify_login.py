import sys
sys.path.append('/app')
from app.db import SessionLocal
from app.models import User
from app.auth import verify_password, get_password_hash

db = SessionLocal()
email = "subramaniyam@consultant.com"
password = "abc123"

user = db.query(User).filter(User.email == email).first()
if user:
    print(f"User found: {user.email}")
    print(f"Stored Hash: {user.hashed_password}")
    is_valid = verify_password(password, user.hashed_password)
    print(f"Password '{password}' valid: {is_valid}")
    
    # Test hashing again to see if it matches structure (bcrypt salts differ, but structure should be same)
    new_hash = get_password_hash(password)
    print(f"New Hash sample: {new_hash}")
    print(f"Verify New Hash: {verify_password(password, new_hash)}")
else:
    print(f"User {email} not found")
db.close()
