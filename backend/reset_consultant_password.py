import sys
sys.path.append('/app')
from app.db import SessionLocal
from app.models import User
from app.auth import get_password_hash

db = SessionLocal()
email = "subramaniyam@consultant.com"
new_password = "abc123"

user = db.query(User).filter(User.email == email).first()
if user:
    user.password_hash = get_password_hash(new_password)
    db.commit()
    print(f"Password for {email} reset to {new_password}")
else:
    print(f"User {email} not found")
db.close()
