import sys
import os
sys.path.append(os.getcwd())

from app.db import SessionLocal
from app.models import User, Role, Region
from app.auth import get_password_hash

db = SessionLocal()
try:
    user = User(
        name="Test Sales",
        email="testsales@example.com",
        password_hash=get_password_hash("password"),
        role=Role.SALES,
        region=Region.INDIA,
        is_active=True
    )
    db.add(user)
    db.commit()
    print("User created successfully")
except Exception as e:
    print(f"Error creating user: {e}")
finally:
    db.close()
