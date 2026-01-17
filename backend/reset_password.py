from app.db import SessionLocal
from app.models import User
from app.auth import get_password_hash
import sys

db = SessionLocal()
email = "subramaniyam.webdesigner@gmail.com"
new_password = "admin123"

user = db.query(User).filter(User.email == email).first()
if user:
    print(f"User found: {user.email}")
    user.password_hash = get_password_hash(new_password)
    db.commit()
    print(f"Password reset successfully for {email}")
else:
    print(f"User not found: {email}")
    sys.exit(1)
db.close()
