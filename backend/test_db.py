
from app.db import SessionLocal
from app.models import User

try:
    db = SessionLocal()
    print("Database session created")
    user = db.query(User).filter(User.email == "subramaniyam@consultant.com").first()
    if user:
        print(f"User found: {user.email}")
        print(f"Role: {user.role}")
        print(f"Password hash: {user.password_hash}")
    else:
        print("User not found")
    db.close()
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Error: {e}")
